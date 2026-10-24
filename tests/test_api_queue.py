"""Confirmed saved API claims, drift, capacity and recovery with real SQLite."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from adaptive_qa.api_queue import LocalApiQueue, process_local_api_once
from adaptive_qa.local_free import LocalFreeProjects, LOCAL_ACTOR
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.project_store import ProjectActor, ProjectNotFound
from adaptive_qa.saved_api_review import review_saved_api


class ApiQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.projects=LocalFreeProjects(self.root/'projects.sqlite')
        self.pid=self.projects.create(LOCAL_ACTOR,'Owned API queue').project_id
        self.settings=dict(base_url='http://127.0.0.1:8000',allowed_hosts=['127.0.0.1'],allow_data_changes=False,
            secret_references={},local_api_binding=dict(path='/ready',expected_status=200,json_field='ready',expected_boolean=True))
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
        self.queue=LocalApiQueue(self.projects)

    def submit(self):
        digest=review_saved_api(self.projects,LOCAL_ACTOR,self.pid)['contract_fingerprint']
        return self.queue.submit(LOCAL_ACTOR,self.pid,digest)

    def test_confirmation_scope_stale_settings_and_sanitized_completion(self):
        with self.assertRaises(ValueError):self.queue.submit(LOCAL_ACTOR,self.pid,'0'*64)
        job=self.submit();work=self.queue.claim_next()
        with self.assertRaises(ProjectNotFound):self.queue.get(ProjectActor('b'*32),self.pid,job['job_id'])
        with self.assertRaises(ValueError):self.queue.finish(replace(work,token='wrong'),TestResult('LOCAL-API-READ',TestStatus.PASSED,0,'private'))
        self.assertEqual(self.queue.finish(work,TestResult('LOCAL-API-READ',TestStatus.PASSED,0,'private')),'completed')
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,job['job_id'])['result'],dict(status='passed'))
        with self.assertRaises(ValueError):self.queue.finish(work,TestResult('LOCAL-API-READ',TestStatus.PASSED,0,'private'))
        stale=self.submit()
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,allow_data_changes=True))
        with patch('adaptive_qa.api_queue.run_reviewed_local_api') as child:
            self.assertIsNone(process_local_api_once(self.queue));child.assert_not_called()
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,stale['job_id'])['status'],'error')

    def test_atomic_pending_limit_and_unique_concurrent_claims(self):
        def submit(_):
            try:return self.submit()
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(result is not None for result in pool.map(submit,range(8))),5)
        with ThreadPoolExecutor(max_workers=5) as pool:
            claims=list(pool.map(lambda _:self.queue.claim_next(),range(5)))
        self.assertEqual(len({claim.job_id for claim in claims}),5)

    def test_cancel_changed_policy_and_recovery_never_retry(self):
        job=self.submit();self.queue.cancel(LOCAL_ACTOR,self.pid,job['job_id']);self.assertIsNone(self.queue.claim_next())
        job=self.submit();work=self.queue.claim_next()
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,allow_data_changes=True))
        self.assertTrue(self.queue.cancellation_requested(work))
        self.assertEqual(self.queue.finish(work,TestResult('LOCAL-API-READ',TestStatus.ERROR,0,'private')),'error')
        self.submit();self.queue.claim_next()
        self.assertEqual(self.queue.recover_interrupted(),dict(cancelled=0,error=1))
        self.assertIsNone(self.queue.claim_next())

    def test_worker_exception_does_not_persist_private_text_or_retry(self):
        job=self.submit()
        with patch('adaptive_qa.api_queue.run_reviewed_local_api',side_effect=RuntimeError('private')) as child:
            self.assertEqual(process_local_api_once(self.queue)['status'],'completed')
        child.assert_called_once()
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,job['job_id'])['result'],dict(status='error'))
        self.assertIsNone(process_local_api_once(self.queue))

    def test_offline_recovery_cancels_api_jobs_and_revokes_claims(self):
        from adaptive_qa.dashboard_runs import DashboardRunQueue
        from adaptive_qa.local_backup import create_local_backup,restore_local_backup
        DashboardRunQueue(self.projects)
        job=self.submit();work=self.queue.claim_next()
        with TemporaryDirectory() as temporary:
            snapshot=Path(temporary)/'snapshot';destination=Path(temporary)/'restored'
            create_local_backup(self.root,snapshot,maintenance_confirmed=True)
            restore_local_backup(snapshot,destination,maintenance_confirmed=True)
            restored=LocalApiQueue(LocalFreeProjects(destination/'projects.sqlite'))
            self.assertEqual(restored.get(LOCAL_ACTOR,self.pid,job['job_id'])['status'],'cancelled')
            self.assertIsNone(restored.claim_next())
            with self.assertRaises(ValueError):restored.finish(work,TestResult('LOCAL-API-READ',TestStatus.PASSED,0,'private'))

    def test_signed_license_capacity_and_expiry_include_api_claims(self):
        import base64,json
        from dataclasses import asdict
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from adaptive_qa.license_store import LicenseStore
        from adaptive_qa.licensing import LicenseClaims,LicenseError,license_message
        from adaptive_qa.local_licensed import LicensedLocalProjects
        now=[150];private=Ed25519PrivateKey.generate()
        licenses=LicenseStore(self.root/'license.sqlite',{'issuer':private.public_key().public_bytes_raw()},clock=lambda:now[0])
        payload=asdict(LicenseClaims('a'*32,'b'*32,100,100,200,2,1))
        signature=base64.urlsafe_b64encode(private.sign(license_message('issuer',payload))).rstrip(b'=').decode()
        licenses.install(json.dumps(dict(key_id='issuer',payload=payload,signature=signature)).encode())
        paid=LicensedLocalProjects(self.projects.database,licenses);queue=LocalApiQueue(paid)
        digest=review_saved_api(paid,LOCAL_ACTOR,self.pid)['contract_fingerprint']
        queue.submit(LOCAL_ACTOR,self.pid,digest);queue.submit(LOCAL_ACTOR,self.pid,digest)
        work=queue.claim_next();self.assertIsNotNone(work)
        self.assertIsNone(queue.claim_next())
        with paid._connection() as c,self.assertRaises(LicenseError):paid.admit_execution(c,starting=True)
        now[0]=200
        self.assertTrue(queue.cancellation_requested(work))
        self.assertEqual(queue.finish(work,TestResult('LOCAL-API-READ',TestStatus.PASSED,0,'private')),'cancelled')
        self.assertIsNone(queue.claim_next())
        with self.assertRaises(LicenseError):queue.submit(LOCAL_ACTOR,self.pid,digest)
