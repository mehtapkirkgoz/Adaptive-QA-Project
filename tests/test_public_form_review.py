"""Saved HTTPS metadata remains owner-scoped and non-executing."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.project_settings import reference_name
from adaptive_qa.project_store import ProjectActor, ProjectStore, ProjectNotFound
from adaptive_qa.public_form_review import review_saved_public_form, revalidate_saved_public_form
from adaptive_qa.secrets import SecretReference


class SavedPublicFormReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=ProjectStore(Path(self.temp.name)/'projects.sqlite')
        self.owner=ProjectActor('a'*32);self.other=ProjectActor('b'*32)
        self.project=self.store.create(self.owner,'HTTPS review');self.pid=self.project.project_id
        self.data=dict(base_url='https://qa.example.test/search',allowed_hosts=['qa.example.test'],
            allow_data_changes=True,secret_references={'search_query':reference_name(self.owner.user_id,self.pid,'search_query')},
            local_form_binding=dict(profile='public_https',operation='search',
                document_url='https://qa.example.test/search',endpoint_url='https://qa.example.test/search/execute',
                field_names=['query'],accepted=dict(status_code=200,field_name='found',expected_value=True),
                rejected=dict(status_code=404,field_name='found',expected_value=False)))
        self.completion=ElementMapping('search.results',(LocatorSpec(LocatorStrategy.TEST_ID,'results-ready'),))
        self.save()

    def save(self,data=None):self.store.save_configuration(self.owner,self.pid,data or self.data)
    def review(self):return review_saved_public_form(self.store,self.owner,self.pid,completion=self.completion)

    def test_review_never_resolves_or_contacts_and_revalidates_unchanged(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')),patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')):
            review=self.review()
            self.assertFalse(review.execution_authorized)
            self.assertFalse(review.public()['execution_authorized'])
            self.assertEqual(revalidate_saved_public_form(self.store,self.owner,review),review)

    def test_owner_boundary_and_missing_project(self):
        for actor,pid in ((self.other,self.pid),(self.owner,'0'*32)):
            with self.assertRaises(ProjectNotFound):
                review_saved_public_form(self.store,actor,pid,completion=self.completion)
        with self.assertRaises(ProjectNotFound):revalidate_saved_public_form(self.store,self.other,self.review())

    def test_non_executing_save_does_not_bypass_policy_or_missing_references(self):
        for change in ({'allow_data_changes':False},{'secret_references':{}}):
            self.save(dict(self.data,**change))
            with self.assertRaises(ValueError):self.review()
        self.save()
        with self.assertRaises(ValueError):
            review_saved_public_form(self.store,self.owner,self.pid,completion=None)

    def test_changed_endpoint_or_settings_invalidates_previous_review(self):
        review=self.review()
        data=deepcopy(self.data);data['local_form_binding']['endpoint_url']='https://qa.example.test/v2/search'
        self.save(data)
        with self.assertRaises(ValueError):revalidate_saved_public_form(self.store,self.owner,review)
        self.save();self.assertEqual(revalidate_saved_public_form(self.store,self.owner,review),review)

    def test_explicit_profile_and_exact_origin_are_required(self):
        for change in ({'profile':'unknown'},{'endpoint_url':'https://127.0.0.1/execute'},
                       {'document_url':'https://qa.example.test/other'}):
            data=deepcopy(self.data);data['local_form_binding'].update(change)
            with self.assertRaises(ValueError):self.save(data)
        data=deepcopy(self.data);del data['local_form_binding']['profile']
        with self.assertRaises(ValueError):self.save(data)

    def test_review_cannot_enter_existing_local_execution_queue(self):
        from adaptive_qa.interactive_queue import OwnedInteractiveQueue
        queue=OwnedInteractiveQueue(self.store)
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')),self.assertRaises(ValueError):
            queue.submit(self.owner,self.review())


class PublicFormQueueTests(unittest.TestCase):
    setUp=SavedPublicFormReviewTests.setUp
    save=SavedPublicFormReviewTests.save
    review=SavedPublicFormReviewTests.review

    def queue(self):
        from adaptive_qa.interactive_queue import OwnedInteractiveQueue
        return OwnedInteractiveQueue(self.store)

    def submit(self,queue):
        review=self.review()
        return queue.submit_public(self.owner,review,confirmed_fingerprint=review.submission.fingerprint())

    def test_explicit_confirmation_and_ownership_before_admission(self):
        queue=self.queue();review=self.review()
        for fingerprint in ('',None,'0'*64,'ş'*64):
            with self.assertRaises(ValueError):queue.submit_public(self.owner,review,confirmed_fingerprint=fingerprint)
        with self.assertRaises(ProjectNotFound):
            queue.submit_public(self.other,review,confirmed_fingerprint=review.submission.fingerprint())
        self.assertEqual(queue.list(self.owner,self.pid),())

    def test_stale_claim_and_running_cancellation_never_replay(self):
        queue=self.queue();job=self.submit(queue)
        self.save(dict(self.data,allow_data_changes=False))
        self.assertIsNone(queue.claim_next())
        self.assertEqual(queue.get(self.owner,self.pid,job['job_id'])['status'],'error')
        self.save();self.submit(queue);work=queue.claim_next()
        self.save(dict(self.data,secret_references={}))
        self.assertTrue(queue.cancellation_requested(work))

    def test_worker_uses_supervised_public_path_and_sanitizes_result(self):
        from adaptive_qa.interactive_queue import process_owned_interactive_once
        from adaptive_qa.interactive_probe import InteractiveProbeResult
        from adaptive_qa.models import TestStatus
        queue=self.queue();job=self.submit(queue)
        with patch('adaptive_qa.public_browser_process.run_isolated_public_browser',
                return_value=InteractiveProbeResult(TestStatus.PASSED,'private-canary',1)) as child:
            self.assertEqual(process_owned_interactive_once(queue)['status'],'completed')
        self.assertEqual(child.call_args.kwargs['owner_id'],self.owner.user_id)
        result=queue.get(self.owner,self.pid,job['job_id'])
        self.assertEqual(result['scope'],'reviewed_public_https')
        self.assertEqual(result['result'],dict(status='passed',attempted_submissions=1))
        self.assertNotIn('private-canary',str(result))

    def test_capacity_recovery_and_claim_tokens_are_shared(self):
        from dataclasses import replace
        queue=self.queue()
        for _ in range(5):self.submit(queue)
        with self.assertRaises(ValueError):self.submit(queue)
        work=queue.claim_next()
        with self.assertRaises(ValueError):queue.cancellation_requested(replace(work,claim_token='wrong'))
        self.assertEqual(queue.recover_interrupted(),dict(cancelled=0,error=1))
        with self.assertRaises(ValueError):queue.cancellation_requested(work)

    def test_queued_cancel_never_starts_child(self):
        from adaptive_qa.interactive_queue import process_owned_interactive_once
        queue=self.queue();job=self.submit(queue)
        queue.cancel(self.owner,self.pid,job['job_id'])
        with patch('adaptive_qa.public_browser_process.run_isolated_public_browser') as child:
            self.assertIsNone(process_owned_interactive_once(queue));child.assert_not_called()

    def test_changed_settings_cannot_finalize_a_success(self):
        from adaptive_qa.interactive_probe import InteractiveProbeResult
        from adaptive_qa.models import TestStatus
        queue=self.queue();self.submit(queue);work=queue.claim_next()
        self.save(dict(self.data,allow_data_changes=False))
        self.assertEqual(queue.finish(work,InteractiveProbeResult(TestStatus.PASSED,'ignored',1)),'error')
        self.assertEqual(queue.get(self.owner,self.pid,work.job_id)['result']['status'],'error')

    def test_unknown_snapshot_fields_fail_closed_without_dispatch(self):
        import json
        queue=self.queue();job=self.submit(queue)
        with self.store._connection() as connection:
            raw=connection.execute('SELECT review_json FROM dashboard_interactive_jobs WHERE job_id=?',(job['job_id'],)).fetchone()[0]
            snapshot=json.loads(raw);snapshot['execution_authorized']=True
            connection.execute('UPDATE dashboard_interactive_jobs SET review_json=? WHERE job_id=?',(json.dumps(snapshot),job['job_id']))
        self.assertIsNone(queue.claim_next())
        self.assertEqual(queue.get(self.owner,self.pid,job['job_id'])['status'],'error')

