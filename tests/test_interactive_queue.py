"""Interactive dispatch snapshots, leases, cancellation and license sharing."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict,replace
import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_review import review_saved_interactive
from adaptive_qa.interactive_queue import OwnedInteractiveQueue,process_owned_interactive_once
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.models import TestStatus
from adaptive_qa.local_free import LOCAL_ACTOR,LocalFreeProjects
from adaptive_qa.local_licensed import LicensedLocalProjects
from adaptive_qa.license_store import LicenseStore
from adaptive_qa.licensing import LicenseClaims,LicenseError,license_message
from adaptive_qa.project_store import ProjectActor,ProjectNotFound
from adaptive_qa.project_settings import reference_name


class InteractiveQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'projects.sqlite'
        self.projects=LocalFreeProjects(self.path)
        self.project=self.projects.create(LOCAL_ACTOR,'Local interactive')
        self.pid=self.project.project_id
        self.data=dict(base_url='http://127.0.0.1:8000/interactive/login-transition',allowed_hosts=['127.0.0.1'],allow_data_changes=True,
            secret_references={slot:reference_name(LOCAL_ACTOR.user_id,self.pid,slot) for slot in ('login_username','login_password')})
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.data)
        self.queue=OwnedInteractiveQueue(self.projects)
        self.completion=ElementMapping('login.accepted',(LocatorSpec(LocatorStrategy.TEST_ID,'result'),))

    def review(self,projects=None):
        return review_saved_interactive(projects or self.projects,LOCAL_ACTOR,self.pid,fixture_id='login-transition',completion=self.completion)

    def submit(self):return self.queue.submit(LOCAL_ACTOR,self.review())

    def test_owned_lifecycle_and_foreign_or_stale_claims(self):
        job=self.submit();work=self.queue.claim_next()
        self.assertEqual(work.job_id,job['job_id'])
        with self.assertRaises(ProjectNotFound):self.queue.get(ProjectActor('b'*32),self.pid,work.job_id)
        with self.assertRaises(ValueError):self.queue.cancellation_requested(replace(work,claim_token='wrong'))
        self.assertEqual(self.queue.finish(work,InteractiveProbeResult(TestStatus.PASSED,'private-canary',1)),'completed')
        public=self.queue.get(LOCAL_ACTOR,self.pid,work.job_id)
        self.assertEqual(public['result'],dict(status='passed',attempted_submissions=1))
        self.assertNotIn('private-canary',json.dumps(public))
        with self.assertRaises(ValueError):self.queue.finish(work,InteractiveProbeResult(TestStatus.PASSED,'private-canary',1))

    def test_stale_review_and_claim_time_drift_never_dispatch(self):
        review=self.review()
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.data,allow_data_changes=False))
        with self.assertRaises(ValueError):self.queue.submit(LOCAL_ACTOR,review)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.data)
        job=self.submit()
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.data,secret_references={}))
        with patch('adaptive_qa.interactive_process.run_isolated_interactive_probe') as child:
            self.assertIsNone(process_owned_interactive_once(self.queue));child.assert_not_called()
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,job['job_id'])['status'],'error')

    def test_atomic_pending_limit_and_concurrent_claims(self):
        review=self.review()
        def submit(_):
            try:return self.queue.submit(LOCAL_ACTOR,review)
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(job is not None for job in pool.map(submit,range(8))),5)
        with ThreadPoolExecutor(max_workers=5) as pool:work=list(pool.map(lambda _:self.queue.claim_next(),range(5)))
        self.assertEqual(len({item.job_id for item in work}),5)

    def test_cancel_recovery_and_unknown_outcome_are_never_retried(self):
        pending=self.submit();self.queue.cancel(LOCAL_ACTOR,self.pid,pending['job_id'])
        self.assertIsNone(self.queue.claim_next())
        running=self.submit();work=self.queue.claim_next()
        self.queue.cancel(LOCAL_ACTOR,self.pid,work.job_id)
        self.assertTrue(self.queue.cancellation_requested(work))
        self.assertEqual(self.queue.finish(work,InteractiveProbeResult(TestStatus.CANCELLED,'Cancelled',None)),'cancelled')
        self.assertIsNone(self.queue.get(LOCAL_ACTOR,self.pid,running['job_id'])['result']['attempted_submissions'])
        interrupted=self.submit();self.queue.claim_next()
        self.assertEqual(self.queue.recover_interrupted(),dict(cancelled=0,error=1))
        self.assertIsNone(self.queue.claim_next())
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,interrupted['job_id'])['status'],'error')

    def test_worker_uses_scoped_references_and_sanitizes_unexpected_child_failure(self):
        self.submit()
        with patch('adaptive_qa.interactive_process.run_isolated_interactive_probe',side_effect=RuntimeError('private-canary')) as child:
            result=process_owned_interactive_once(self.queue)
        args=child.call_args
        self.assertEqual(tuple(ref.environment_variable for ref in args.args[0].inputs),tuple(self.data['secret_references'].values()))
        self.assertEqual(args.kwargs['fixture_source'],'owned_submission')
        public=self.queue.get(LOCAL_ACTOR,self.pid,result['job_id'])
        self.assertEqual(public['result'],dict(status='error',attempted_submissions=None))
        self.assertNotIn('private-canary',self.path.read_bytes().decode('latin1'))

    def test_running_policy_revocation_requests_cancellation(self):
        self.submit();work=self.queue.claim_next()
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.data,allow_data_changes=False))
        self.assertTrue(self.queue.cancellation_requested(work))
        self.assertEqual(self.queue.finish(work,InteractiveProbeResult(TestStatus.ERROR,'Private',None)),'error')

    def test_signed_license_capacity_includes_interactive_and_existing_runs(self):
        now=[150];private=Ed25519PrivateKey.generate()
        licenses=LicenseStore(self.root/'license.sqlite',{'issuer':private.public_key().public_bytes_raw()},clock=lambda:now[0])
        payload=asdict(LicenseClaims('a'*32,'b'*32,100,100,200,2,1))
        signature=base64.urlsafe_b64encode(private.sign(license_message('issuer',payload))).rstrip(b'=').decode()
        licenses.install(json.dumps(dict(key_id='issuer',payload=payload,signature=signature)).encode())
        paid=LicensedLocalProjects(self.path,licenses);queue=OwnedInteractiveQueue(paid)
        queue.submit(LOCAL_ACTOR,self.review(paid));queue.submit(LOCAL_ACTOR,self.review(paid))
        with ThreadPoolExecutor(max_workers=4) as pool:claims=list(pool.map(lambda _:queue.claim_next(),range(4)))
        self.assertEqual(sum(claim is not None for claim in claims),1)
        work=next(claim for claim in claims if claim is not None)
        with paid._connection() as connection,self.assertRaises(LicenseError):paid.admit_execution(connection,starting=True)
        queue.submit(LOCAL_ACTOR,self.review(paid));self.assertIsNone(queue.claim_next())
        now[0]=200
        self.assertTrue(queue.cancellation_requested(work))
        with self.assertRaises(LicenseError):queue.submit(LOCAL_ACTOR,self.review(paid))
        self.assertIsNone(queue.claim_next())

    def test_offline_restore_cancels_interactive_work_and_drops_its_claim(self):
        from adaptive_qa.dashboard_runs import DashboardRunQueue
        from adaptive_qa.local_backup import create_local_backup,restore_local_backup
        DashboardRunQueue(self.projects)
        job=self.submit();work=self.queue.claim_next()
        with TemporaryDirectory() as recovery:
            bundle=Path(recovery)/'snapshot';destination=Path(recovery)/'restored'
            create_local_backup(self.root,bundle,maintenance_confirmed=True)
            restore_local_backup(bundle,destination,maintenance_confirmed=True)
            restored=OwnedInteractiveQueue(LocalFreeProjects(destination/'projects.sqlite'))
            self.assertEqual(restored.get(LOCAL_ACTOR,self.pid,job['job_id'])['status'],'cancelled')
            self.assertIsNone(restored.claim_next())
            with self.assertRaises(ValueError):restored.cancellation_requested(work)
