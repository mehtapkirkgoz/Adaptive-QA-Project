"""Trusted worker transitions and reduced report boundaries using typed fixture evidence."""

from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.discovery import PageSnapshot, FormSnapshot, FieldSnapshot
from adaptive_qa.project_store import ProjectStore, ProjectActor
from adaptive_qa.worker_lock import worker_lock


class DashboardWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = ProjectStore(Path(self.temp.name) / 'projects.sqlite')
        self.actor = ProjectActor('a' * 32)
        self.project = self.projects.create(self.actor, 'Worker')
        self.projects.save_configuration(self.actor, self.project.project_id,
            {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
             'allow_data_changes': False, 'secret_references': {}})
        self.queue = DashboardDiscoveryQueue(self.projects)
        self.job = self.queue.submit(self.actor, self.project.project_id)
        page = PageSnapshot('http://127.0.0.1:8000/', forms=(FormSnapshot(
            form_id='PRIVATE_LABEL_SENTINEL', fields=(FieldSnapshot('email'), FieldSnapshot('password')),
            buttons=('Sign in',)),), collection_complete=True)
        self.payload = {'pages': [asdict(page)], 'limitations': [],
                        'plan': {'execution_authorized': True, 'cases': []}}

    def get(self):
        return self.queue.get(self.actor, self.project.project_id, self.job['job_id'])

    def test_parent_rebuilds_nonexecuting_plan_and_omits_raw_snapshots(self):
        with patch('adaptive_qa.dashboard_worker.discover_local_sample', return_value=self.payload):
            outcome = process_discovery_once(self.queue)
        self.assertEqual(outcome['status'], 'completed')
        report = self.get()['report']
        self.assertFalse(report['execution_authorized'])
        self.assertEqual(report['counts']['catalog'], 75)
        self.assertGreater(report['counts']['selected'], 0)
        self.assertEqual(report['configuration_source'], 'job_snapshot')
        self.assertNotIn('PRIVATE_LABEL_SENTINEL', str(report))
        self.assertNotIn('http://', str(report))

    def test_cancel_wins_and_discards_even_successful_report(self):
        def discover(*args, **kwargs):
            self.queue.cancel(self.actor, self.project.project_id, self.job['job_id'])
            self.assertTrue(kwargs['should_cancel']())
            return self.payload
        with patch('adaptive_qa.dashboard_worker.discover_local_sample', side_effect=discover):
            self.assertEqual(process_discovery_once(self.queue)['status'], 'cancelled')
        self.assertNotIn('report', self.get())

    def test_child_failure_finalizes_generic_error_without_report(self):
        with patch('adaptive_qa.dashboard_worker.discover_local_sample', side_effect=RuntimeError('PRIVATE')):
            self.assertEqual(process_discovery_once(self.queue)['status'], 'error')
        self.assertNotIn('PRIVATE', str(self.get()))
        self.assertNotIn('report', self.get())

    def test_external_page_payload_is_rejected(self):
        self.payload['pages'][0]['url'] = 'https://example.test/'
        with patch('adaptive_qa.dashboard_worker.discover_local_sample', return_value=self.payload):
            self.assertEqual(process_discovery_once(self.queue)['status'], 'error')

    def test_execution_lock_covers_discovery_and_blocks_recovery(self):
        def discover(*args, **kwargs):
            with self.assertRaises(ValueError):
                self.queue.recover_interrupted()
            return self.payload
        with patch('adaptive_qa.dashboard_worker.discover_local_sample', side_effect=discover):
            self.assertEqual(process_discovery_once(self.queue)['status'], 'completed')

    def test_other_worker_lock_prevents_claiming_and_idle_returns_none(self):
        with worker_lock(self.projects.database):
            with self.assertRaises(ValueError):
                process_discovery_once(self.queue)
        self.assertEqual(self.get()['status'], 'queued')
        self.queue.cancel(self.actor, self.project.project_id, self.job['job_id'])
        self.assertIsNone(process_discovery_once(self.queue))
