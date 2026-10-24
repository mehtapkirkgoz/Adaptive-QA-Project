"""Reusable saved bindings keep references scoped and execution explicitly confirmed."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.interactive_review import review_saved_local_form
from adaptive_qa.interactive_queue import OwnedInteractiveQueue,process_owned_interactive_once
from adaptive_qa.local_form_binding import LocalFormBinding
from adaptive_qa.local_free import LocalFreeProjects,LocalFreeSessions,LOCAL_ACTOR
from adaptive_qa.models import TestStatus
from adaptive_qa.project_settings import reference_name
from adaptive_qa.project_store import ProjectActor,ProjectNotFound
from adaptive_qa.secrets import SecretReference
from adaptive_qa.web_app import create_app,CSRF_COOKIE


class SavedLocalFormTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.database=Path(self.temp.name)/'projects.sqlite';self.projects=LocalFreeProjects(self.database)
        project=self.projects.create(LOCAL_ACTOR,'Reusable local form');self.pid=project.project_id
        self.binding=dict(operation='login',document_url='http://127.0.0.1:8000/portal/access',endpoint_url='http://127.0.0.1:8000/auth/check',
            field_names=['identity','accessCode'],accepted=dict(status_code=201,field_name='sessionReady',expected_value=True),
            rejected=dict(status_code=403,field_name='sessionReady',expected_value=False))
        self.settings=dict(base_url=self.binding['document_url'],allowed_hosts=['127.0.0.1'],allow_data_changes=True,
            secret_references={slot:reference_name(LOCAL_ACTOR.user_id,self.pid,slot) for slot in ('login_username','login_password')},local_form_binding=self.binding)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
        self.completion=ElementMapping('login.accepted',(LocatorSpec(LocatorStrategy.TEST_ID,'confirmed'),))
        self.queue=OwnedInteractiveQueue(self.projects)
        self.client=TestClient(create_app(LocalFreeSessions(self.database),projects=self.projects),base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close);self.client.get('/api/auth/me')
        self.headers={'origin':'http://127.0.0.1:8765','content-type':'application/json','x-csrf-token':self.client.cookies[CSRF_COOKIE]}
        self.base='/api/projects/'+self.pid+'/interactive'
        self.body=dict(completion=dict(logical_name='login.accepted',scope_test_id=None,locators=[dict(strategy='test_id',value='confirmed',role=None)]))

    def review(self):return review_saved_local_form(self.projects,LOCAL_ACTOR,self.pid,completion=self.completion)

    def test_syntax_persistence_and_review_never_resolve_values_or_start_child(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')),patch('adaptive_qa.interactive_process.run_isolated_local_form') as child:
            response=self.client.post(self.base+'/local/review',headers=self.headers,json=self.body)
            self.assertEqual(response.status_code,200,response.text);child.assert_not_called()
        self.assertFalse(response.json()['execution_authorized'])
        self.assertEqual(response.json()['scope'],'owned_loopback_only')
        reopened=LocalFreeProjects(self.database).configuration(LOCAL_ACTOR,self.pid)
        self.assertEqual(reopened['local_form_binding'],self.binding)
        self.assertEqual(self.queue.list(LOCAL_ACTOR,self.pid),())
        self.assertIsInstance(self.review().submission,LocalFormBinding)

    def test_current_confirmation_enqueues_and_common_history_cancels(self):
        digest=self.client.post(self.base+'/local/review',headers=self.headers,json=self.body).json()['contract_fingerprint']
        self.assertEqual(self.client.post(self.base+'/local/jobs',headers=self.headers,json=self.body).status_code,400)
        response=self.client.post(self.base+'/local/jobs',headers=self.headers,json=dict(self.body,confirmed_contract_fingerprint=digest))
        self.assertEqual(response.status_code,202,response.text);job=response.json()
        self.assertEqual(job['scope'],'owned_loopback_only')
        self.assertEqual(self.client.post(self.base+'/review',headers=self.headers,json=dict(self.body,fixture_id=None)).status_code,400)
        self.assertEqual(self.client.post(self.base+'/jobs',headers=self.headers,json=dict(self.body,fixture_id=None,confirmed_contract_fingerprint=digest)).status_code,400)
        self.assertEqual(self.client.get(self.base+'/jobs').json()['jobs'],[job])
        cancelled=self.client.post(self.base+'/jobs/'+job['job_id']+'/cancel',headers=self.headers,json={})
        self.assertEqual(cancelled.json()['status'],'cancelled')

    def test_endpoint_or_response_edits_invalidate_confirmation_and_claim(self):
        review=self.review();job=self.queue.submit(LOCAL_ACTOR,review)
        binding=dict(self.binding,endpoint_url='http://127.0.0.1:8000/auth/v2')
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_form_binding=binding))
        response=self.client.post(self.base+'/local/jobs',headers=self.headers,json=dict(self.body,confirmed_contract_fingerprint=review.submission.fingerprint()))
        self.assertEqual(response.status_code,400)
        self.assertIsNone(self.queue.claim_next())
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,job['job_id'])['status'],'error')
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_form_binding=dict(self.binding,accepted=dict(status_code=200,field_name='ready',expected_value=True))))
        self.assertNotEqual(self.review().submission.fingerprint(),review.submission.fingerprint())

    def test_revocation_preserves_metadata_but_blocks_review(self):
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,allow_data_changes=False))
        saved=self.projects.configuration(LOCAL_ACTOR,self.pid)
        self.assertFalse(saved['allow_data_changes']);self.assertEqual(saved['local_form_binding'],self.binding)
        with self.assertRaises(ValueError):self.review()
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_form_binding=None))
        with self.assertRaises(ValueError):self.review()

    def test_invalid_external_or_plaintext_bindings_are_not_stored(self):
        original=self.projects.configuration(LOCAL_ACTOR,self.pid)
        for changes in ({'endpoint_url':'https://example.com/login'},{'password':'private-value'},
                        {'accepted':dict(status_code=200,field_name='ready',expected_value='private-value')},
                        {'document_url':'http://127.0.0.1:8000/other'},{'field_names':['identity','identity']}):
            with self.assertRaises(ValueError):self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_form_binding=dict(self.binding,**changes)))
            self.assertEqual(self.projects.configuration(LOCAL_ACTOR,self.pid),original)
        self.assertNotIn(b'private-value',self.database.read_bytes())

    def test_worker_dispatches_only_current_typed_binding_and_scoped_references(self):
        self.queue.submit(LOCAL_ACTOR,self.review())
        with patch('adaptive_qa.interactive_process.run_isolated_local_form',return_value=InteractiveProbeResult(TestStatus.PASSED,'Private response',1)) as reusable,patch('adaptive_qa.interactive_process.run_isolated_interactive_probe') as fixed:
            result=process_owned_interactive_once(self.queue);fixed.assert_not_called()
        binding=reusable.call_args.args[0]
        self.assertIsInstance(binding,LocalFormBinding)
        self.assertEqual(tuple(ref.environment_variable for ref in binding.form.inputs),tuple(self.settings['secret_references'].values()))
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,result['job_id'])['result'],dict(status='passed',attempted_submissions=1))
        self.assertNotIn(b'Private response',self.database.read_bytes())

    def test_http_and_internal_ownership_guards_remain(self):
        headers={key:value for key,value in self.headers.items() if key!='x-csrf-token'}
        self.assertEqual(self.client.post(self.base+'/local/review',headers=headers,json=self.body).status_code,401)
        self.assertEqual(self.client.post(self.base+'/local/jobs',headers=headers,json=dict(self.body,confirmed_contract_fingerprint='a'*64)).status_code,401)
        with self.assertRaises(ProjectNotFound):review_saved_local_form(self.projects,ProjectActor('b'*32),self.pid,completion=self.completion)
        self.assertEqual(self.client.post(self.base.replace(self.pid,'0'*32)+'/local/review',headers=self.headers,json=self.body).status_code,404)
