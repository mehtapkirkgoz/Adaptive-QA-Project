"""Transactional ownership, frozen dispatch and cancellation precedence."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue, DiscoveryJobNotFound
from adaptive_qa.project_store import ProjectStore, ProjectActor, ProjectNotFound
from adaptive_qa.worker_lock import worker_lock


class DashboardJobsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(Path(self.temp.name) / 'projects.sqlite')
        self.actor, self.other = ProjectActor('a' * 32), ProjectActor('b' * 32)
        self.project = self.store.create(self.actor, 'Dispatch')
        self.settings = {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                         'allow_data_changes': False, 'secret_references': {}}
        self.store.save_configuration(self.actor, self.project.project_id, self.settings)
        self.queue = DashboardDiscoveryQueue(self.store)

    def submit(self):
        return self.queue.submit(self.actor, self.project.project_id)

    def test_submission_is_persistent_nonexecuting_and_configuration_is_frozen(self):
        job = self.submit()
        self.store.save_configuration(self.actor, self.project.project_id, dict(self.settings, allow_data_changes=True))
        reopened = DashboardDiscoveryQueue(ProjectStore(self.store.database))
        self.assertEqual(reopened.get(self.actor, self.project.project_id, job['job_id']), job)
        work = reopened.claim_next()
        self.assertFalse(work.configuration['allow_data_changes'])
        self.assertNotIn('secret_references', work.configuration)
        self.assertNotIn(work.claim_token, repr(work))
        self.assertNotIn('claim_token', reopened.get(self.actor, self.project.project_id, job['job_id']))

    def test_cross_owner_wrong_project_and_missing_jobs_are_not_enumerable(self):
        job = self.submit()
        another = self.store.create(self.actor, 'Other')
        for actor, project, jid in ((self.other, self.project.project_id, job['job_id']),
                                    (self.actor, another.project_id, job['job_id']),
                                    (self.actor, self.project.project_id, '0' * 32)):
            for method in ('get', 'cancel'):
                with self.assertRaisesRegex(DiscoveryJobNotFound, '^Discovery job not found.$'):
                    getattr(self.queue, method)(actor, project, jid)
        with self.assertRaises(ProjectNotFound):
            self.queue.submit(self.other, self.project.project_id)

    def test_queued_cancel_prevents_claim_and_running_cancel_wins_finalization(self):
        first = self.submit()
        self.assertEqual(self.queue.cancel(self.actor, self.project.project_id, first['job_id'])['status'], 'cancelled')
        self.assertIsNone(self.queue.claim_next())
        second = self.submit()
        work = self.queue.claim_next()
        self.assertFalse(self.queue.cancellation_requested(work))
        self.queue.cancel(self.actor, self.project.project_id, second['job_id'])
        self.assertTrue(self.queue.cancellation_requested(work))
        self.assertEqual(self.queue.finish(work), 'cancelled')
        with self.assertRaises(ValueError):
            self.queue.finish(work)

    def test_wrong_claim_cannot_finish_or_read_cancellation(self):
        self.submit()
        work = self.queue.claim_next()
        forged = replace(work, claim_token='wrong')
        for operation in ('finish', 'cancellation_requested'):
            with self.assertRaises(ValueError):
                getattr(self.queue, operation)(forged)
        self.assertEqual(self.queue.finish(work, failed=True), 'error')

    def test_concurrent_claims_never_duplicate_work(self):
        jobs = [self.submit() for _ in range(4)]
        with ThreadPoolExecutor(max_workers=4) as executor:
            work = list(executor.map(lambda _: self.queue.claim_next(), range(4)))
        self.assertEqual({w.job_id for w in work}, {j['job_id'] for j in jobs})

    def test_only_root_fixture_and_bounded_active_admission_are_accepted(self):
        for url in ('https://example.test/', 'http://127.0.0.1:8000/login'):
            hosts = ['example.test'] if 'example' in url else ['127.0.0.1']
            self.store.save_configuration(self.actor, self.project.project_id, dict(self.settings, base_url=url, allowed_hosts=hosts))
            with self.assertRaises(ValueError):
                self.submit()
        self.store.save_configuration(self.actor, self.project.project_id, self.settings)
        jobs = [self.submit() for _ in range(5)]
        with self.assertRaises(ValueError):
            self.submit()
        self.queue.cancel(self.actor, self.project.project_id, jobs[0]['job_id'])
        self.assertEqual(self.submit()['status'], 'queued')

    def test_recovery_marks_interrupted_work_without_replaying_or_resurrecting_claims(self):
        running = self.submit()
        work = self.queue.claim_next()
        cancelled = self.submit()
        other_work = self.queue.claim_next()
        self.queue.cancel(self.actor, self.project.project_id, cancelled['job_id'])
        queued = self.submit()
        self.assertEqual(self.queue.recover_interrupted(), {'cancelled': 1, 'error': 1})
        self.assertEqual(self.queue.get(self.actor, self.project.project_id, running['job_id'])['status'], 'error')
        self.assertEqual(self.queue.get(self.actor, self.project.project_id, cancelled['job_id'])['status'], 'cancelled')
        self.assertEqual(self.queue.claim_next().job_id, queued['job_id'])
        for stale in (work, other_work):
            with self.assertRaises(ValueError):
                self.queue.finish(stale)

    def test_recovery_refuses_active_worker_lock(self):
        self.submit()
        work = self.queue.claim_next()
        with worker_lock(self.store.database):
            with self.assertRaises(ValueError):
                self.queue.recover_interrupted()
        self.assertEqual(self.queue.get(self.actor, self.project.project_id, work.job_id)['status'], 'running')
