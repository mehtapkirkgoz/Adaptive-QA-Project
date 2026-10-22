"""Scoped discovery claims, revocation, policy changes and offline recovery."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
from adaptive_qa.organization_store import OrganizationStore, OrganizationNotFound
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_policy import OrganizationRole as Role
from adaptive_qa.project_store import ProjectStore, ProjectActor
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue, DiscoveryJobNotFound
from adaptive_qa.worker_lock import worker_lock


class OrganizationDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.personal = ProjectStore(Path(self.temp.name)/'projects.sqlite')
        self.organizations = OrganizationStore(self.personal)
        self.scoped = OrganizationProjects(self.organizations)
        self.queue = OrganizationDiscoveryQueue(self.scoped)
        self.owner, self.member, self.other = [ProjectActor(c*32) for c in 'abc']
        self.org = self.organizations.create(self.owner, 'One')
        self.second = self.organizations.create(self.other, 'Two')
        self.project = self.scoped.create(self.owner, self.org, 'Controlled')['project_id']
        self.settings = {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                         'allow_data_changes': False, 'secret_references': {}}
        self.scoped.save_configuration(self.owner, self.org, self.project, self.settings)

    def submit(self):
        return self.queue.submit(self.owner, self.org, self.project)

    def report(self):
        return {'project_id': self.project, 'execution_authorized': False}

    def test_completed_report_is_scoped_and_stale_claim_cannot_rewrite_it(self):
        job = self.submit()
        work = self.queue.claim_next()
        self.assertEqual(self.queue.finish(work, report=self.report()), 'completed')
        self.assertEqual(self.queue.get(self.owner, self.org, self.project, job['job_id'])['report'], self.report())
        self.assertNotIn('claim_token', self.queue.get(self.owner, self.org, self.project, job['job_id']))
        with self.assertRaises(ValueError):
            self.queue.finish(work, failed=True)
        with self.assertRaises(OrganizationNotFound):
            self.queue.get(self.other, self.org, self.project, job['job_id'])
        second_project = self.scoped.create(self.other, self.second, 'Other')['project_id']
        with self.assertRaises(DiscoveryJobNotFound):
            self.queue.get(self.other, self.second, second_project, job['job_id'])

    def test_viewer_cannot_submit_and_revoked_submitter_is_cancelled_before_claim(self):
        self.organizations.set_member(self.owner, self.org, self.member.user_id, Role.VIEWER)
        with self.assertRaises(OrganizationNotFound):
            self.queue.submit(self.member, self.org, self.project)
        self.organizations.set_member(self.owner, self.org, self.member.user_id, Role.MEMBER)
        job = self.queue.submit(self.member, self.org, self.project)
        self.organizations.remove_member(self.owner, self.org, self.member.user_id)
        self.assertIsNone(self.queue.claim_next())
        self.assertEqual(self.queue.get(self.owner, self.org, self.project, job['job_id'])['status'], 'cancelled')

    def test_policy_change_cancels_active_claim_and_discards_late_report(self):
        job = self.submit()
        work = self.queue.claim_next()
        self.scoped.save_configuration(self.owner, self.org, self.project, dict(self.settings, allow_data_changes=True))
        self.assertTrue(self.queue.cancellation_requested(work))
        self.assertEqual(self.queue.finish(work, report=self.report()), 'cancelled')
        self.assertNotIn('report', self.queue.get(self.owner, self.org, self.project, job['job_id']))

    def test_arbitrary_targets_and_execution_authorized_reports_are_rejected(self):
        self.scoped.save_configuration(self.owner, self.org, self.project,
                                      dict(self.settings, base_url='https://example.test/', allowed_hosts=['example.test']))
        with self.assertRaises(ValueError):
            self.submit()
        self.scoped.save_configuration(self.owner, self.org, self.project, self.settings)
        self.submit()
        work = self.queue.claim_next()
        with self.assertRaises(ValueError):
            self.queue.finish(work, report={'project_id': self.project, 'execution_authorized': True})

    def test_operator_recovery_refuses_live_worker_and_invalidates_interrupted_claim(self):
        job = self.submit()
        work = self.queue.claim_next()
        with worker_lock(self.personal.database), self.assertRaises(ValueError):
            self.queue.recover_interrupted()
        self.assertEqual(self.queue.recover_interrupted(), {'cancelled': 0, 'error': 1})
        self.assertEqual(self.queue.get(self.owner, self.org, self.project, job['job_id'])['status'], 'error')
        with self.assertRaises(ValueError):
            self.queue.finish(work, report=self.report())

    def test_global_discovery_capacity_counts_personal_and_shared_work(self):
        personal = DashboardDiscoveryQueue(self.personal)
        private = self.personal.create(self.owner, 'Personal')
        self.personal.save_configuration(self.owner, private.project_id, self.settings)
        with self.personal._connection() as c:
            for number in range(100):
                c.execute('INSERT INTO dashboard_discovery_jobs '
                          '(job_id, project_id, owner_id, status, configuration_json) VALUES (?, ?, ?, ?, ?)',
                          (f'{number:032x}', private.project_id, self.owner.user_id, 'queued', '{}'))
        with self.assertRaises(ValueError):
            self.submit()
        with self.personal._connection() as c:
            c.execute('DELETE FROM dashboard_discovery_jobs')
            for number in range(100):
                c.execute('INSERT INTO dashboard_organization_discovery '
                          '(job_id, organization_id, project_id, user_id, status, configuration_json) VALUES (?, ?, ?, ?, ?, ?)',
                          (f'{number:032x}', self.org, self.project, self.owner.user_id, 'queued', '{}'))
        with self.assertRaises(ValueError):
            personal.submit(self.owner, private.project_id)
