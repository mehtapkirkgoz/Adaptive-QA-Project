"""Transactional shared runs, quota release, tenant isolation and evidence expiry."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest
from unittest.mock import patch

from adaptive_qa.project_store import ProjectStore, ProjectActor
from adaptive_qa.organization_store import OrganizationStore, OrganizationNotFound
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
from adaptive_qa.organization_runs import OrganizationRunQueue
from adaptive_qa.organization_policy import OrganizationQuota, OrganizationRole as Role
from adaptive_qa.organization_admission import OrganizationCapacityExceeded
from adaptive_qa.dashboard_runs import TestRunNotFound
from adaptive_qa.dashboard_worker import configuration_fingerprint
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.worker_lock import worker_lock
from png_fixture import png_bytes


class OrganizationRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = ProjectStore(Path(self.temp.name)/'projects.sqlite')
        self.organizations = OrganizationStore(self.projects)
        self.scoped = OrganizationProjects(self.organizations)
        self.discovery = OrganizationDiscoveryQueue(self.scoped)
        self.now = 1000.0
        self.queue = OrganizationRunQueue(self.discovery,clock=lambda:self.now,retention_seconds=60)
        self.owner,self.other,self.member = [ProjectActor(c*32) for c in 'abc']
        self.org = self.organizations.create(self.owner,'One',quota=OrganizationQuota(3,2,1,3))
        self.second = self.organizations.create(self.other,'Two')
        self.project = self.scoped.create(self.owner,self.org,'Shared')['project_id']
        self.settings = {'base_url':'http://127.0.0.1:8000/','allowed_hosts':['127.0.0.1'],
                         'allow_data_changes':False,'secret_references':{}}
        self.scoped.save_configuration(self.owner,self.org,self.project,self.settings)
        self.job = self.discovery.submit(self.owner,self.org,self.project)['job_id']
        work = self.discovery.claim_next()
        report = {'project_id':self.project,'execution_authorized':False,'discovery_status':'completed',
                  'inspected_pages':1,'configuration_fingerprint':configuration_fingerprint(work.configuration),
                  'cases':[{'case_id':case,'decision':'selected','test_type':'ui','target_binding':'local_root'}
                           for case in ('LOGIN-001','SEARCH-001')]}
        self.discovery.finish(work,report=report)

    def submit(self, actor=None, cases=('LOGIN-001',)):
        return self.queue.submit(actor or self.owner,self.org,self.project,self.job,cases)

    def result(self, case='LOGIN-001', status=TestStatus.PASSED):
        return TestResult(case,status,.1,'private adapter text',('private/path.png',))

    def test_completed_lifecycle_preserves_failed_assertion_and_scoped_png(self):
        run = self.submit()
        work = self.queue.claim_next()
        self.queue.record_result(work,self.result(status=TestStatus.FAILED),evidence_png=png_bytes())
        self.assertEqual(self.queue.finish(work),'completed')
        public = self.queue.get(self.owner,self.org,self.project,run['run_id'])
        result = public['results'][0]
        self.assertEqual(result['status'],'failed')
        self.assertNotIn('private',str(public))
        self.assertNotIn('claim_token',public)
        self.assertEqual(self.queue.evidence(self.owner,self.org,self.project,run['run_id'],result['evidence_id']),png_bytes())
        self.now += 61
        with self.assertRaises(TestRunNotFound):
            self.queue.evidence(self.owner,self.org,self.project,run['run_id'],result['evidence_id'])
        self.assertTrue(self.queue.get(self.owner,self.org,self.project,run['run_id'])['results'][0]['evidence_expired'])
        self.assertEqual(self.queue.prune_expired_evidence(),{'removed':1})
        with self.assertRaises(ValueError):
            self.queue.record_result(work,self.result())

    def test_parallel_admission_and_claim_obey_shared_quota(self):
        def submit(_):
            try:
                return self.submit()
            except OrganizationCapacityExceeded:
                return None
        with ThreadPoolExecutor(max_workers=6) as pool:
            admitted = [value for value in pool.map(submit,range(6)) if value]
        self.assertEqual(len(admitted),2)
        first = self.queue.claim_next()
        self.assertIsNotNone(first)
        self.assertIsNone(self.queue.claim_next())
        self.queue.finish(first,failed=True)
        self.assertIsNotNone(self.queue.claim_next())

    def test_queue_insert_failure_rolls_back_reservation(self):
        run = self.submit()
        class Duplicate:
            hex = run['run_id']
        with patch('adaptive_qa.organization_runs.uuid4',return_value=Duplicate()), self.assertRaises(sqlite3.IntegrityError):
            self.submit()
        with self.projects._connection() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM dashboard_organization_admissions').fetchone()[0],1)

    def test_pending_cancel_frees_capacity_without_refunding_daily_admissions(self):
        for _ in range(3):
            run = self.submit()
            self.queue.cancel(self.owner,self.org,self.project,run['run_id'])
        with self.assertRaises(OrganizationCapacityExceeded):
            self.submit()

    def test_cancel_or_revocation_discards_late_result_and_releases_active_slot(self):
        self.organizations.set_member(self.owner,self.org,self.member.user_id,Role.MEMBER)
        run = self.submit(self.member)
        work = self.queue.claim_next()
        self.organizations.remove_member(self.owner,self.org,self.member.user_id)
        self.assertTrue(self.queue.cancellation_requested(work))
        self.assertFalse(self.queue.record_result(work,self.result(),evidence_png=png_bytes()))
        self.assertEqual(self.queue.finish(work),'cancelled')
        self.assertEqual(self.queue.get(self.owner,self.org,self.project,run['run_id'])['results'],[])
        self.submit()
        self.assertIsNotNone(self.queue.claim_next())

    def test_policy_change_before_claim_cancels_without_fabricated_results(self):
        run = self.submit()
        self.scoped.save_configuration(self.owner,self.org,self.project,dict(self.settings,allow_data_changes=True))
        self.assertIsNone(self.queue.claim_next())
        public = self.queue.get(self.owner,self.org,self.project,run['run_id'])
        self.assertEqual(public['status'],'cancelled')
        self.assertEqual(public['results'],[])

    def test_foreign_tenant_and_viewer_cannot_dispatch_or_read_foreign_results(self):
        run = self.submit()
        self.organizations.set_member(self.owner,self.org,self.member.user_id,Role.VIEWER)
        with self.assertRaises(OrganizationNotFound):
            self.submit(self.member)
        self.assertEqual(self.queue.get(self.member,self.org,self.project,run['run_id'])['status'],'queued')
        with self.assertRaises(OrganizationNotFound):
            self.queue.get(self.other,self.org,self.project,run['run_id'])
        other_project = self.scoped.create(self.other,self.second,'Other')['project_id']
        with self.assertRaises(TestRunNotFound):
            self.queue.get(self.other,self.second,other_project,run['run_id'])

    def test_recovery_preserves_partial_results_and_releases_only_exact_claim(self):
        run = self.submit(cases=('LOGIN-001','SEARCH-001'))
        work = self.queue.claim_next()
        self.queue.record_result(work,self.result())
        with worker_lock(self.projects.database),self.assertRaises(ValueError):
            self.queue.recover_interrupted()
        self.assertEqual(self.queue.recover_interrupted(),{'cancelled':0,'error':1})
        self.assertEqual(len(self.queue.get(self.owner,self.org,self.project,run['run_id'])['results']),1)
        with self.assertRaises(ValueError):
            self.queue.finish(work)
