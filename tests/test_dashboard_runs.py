"""Explicit run admission cannot turn a plan, stale evidence or another owner into authority."""

from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_runs import DashboardRunQueue, TestRunNotFound
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.discovery import PageSnapshot, FormSnapshot, FieldSnapshot
from adaptive_qa.project_store import ProjectStore, ProjectActor, ProjectNotFound


class DashboardRunsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = ProjectStore(Path(self.temp.name) / 'projects.sqlite')
        self.actor, self.other = ProjectActor('a' * 32), ProjectActor('b' * 32)
        self.project = self.projects.create(self.actor, 'Run admission')
        self.pid = self.project.project_id
        self.settings = {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                         'allow_data_changes': False, 'secret_references': {}}
        self.projects.save_configuration(self.actor, self.pid, self.settings)
        self.discovery = DashboardDiscoveryQueue(self.projects)
        self.report_job = self.prepare_report()
        self.runs = DashboardRunQueue(self.projects)

    def prepare_report(self, url='http://127.0.0.1:8000/'):
        job = self.discovery.submit(self.actor, self.pid)
        page = PageSnapshot(url, forms=(FormSnapshot(fields=(FieldSnapshot('email'),
            FieldSnapshot('password')), buttons=('Sign in',)),), collection_complete=True)
        with patch('adaptive_qa.dashboard_worker.discover_local_sample',
                   return_value={'pages': [asdict(page)], 'limitations': []}):
            self.assertEqual(process_discovery_once(self.discovery)['status'], 'completed')
        return job['job_id']

    def submit(self, cases=('LOGIN-001',), job=None):
        return self.runs.submit(self.actor, self.pid, job or self.report_job, cases)

    def test_explicit_submission_persists_without_executing_or_rewriting_plan(self):
        before = self.discovery.get(self.actor, self.pid, self.report_job)['report']
        with patch('adaptive_qa.browser_process.run_isolated_sample_test', side_effect=AssertionError('Admission must not execute')):
            run = self.submit()
        self.assertEqual(run['status'], 'queued')
        self.assertEqual(run['case_ids'], ['LOGIN-001'])
        self.assertEqual(DashboardRunQueue(ProjectStore(self.projects.database)).get(self.actor, self.pid, run['run_id']), run)
        after = self.discovery.get(self.actor, self.pid, self.report_job)['report']
        self.assertEqual(before, after)
        self.assertFalse(after['execution_authorized'])

    def test_stale_configuration_and_uncompleted_evidence_are_rejected(self):
        queued = self.discovery.submit(self.actor, self.pid)
        with self.assertRaises(ValueError):
            self.submit(job=queued['job_id'])
        self.projects.save_configuration(self.actor, self.pid, dict(self.settings, allow_data_changes=True))
        with self.assertRaises(ValueError):
            self.submit()

    def test_other_owner_cannot_submit_read_or_cancel(self):
        run = self.submit()
        with self.assertRaises(ProjectNotFound):
            self.runs.submit(self.other, self.pid, self.report_job, ('LOGIN-001',))
        for method in ('get', 'cancel'):
            with self.assertRaisesRegex(TestRunNotFound, '^Test run not found.$'):
                getattr(self.runs, method)(self.other, self.pid, run['run_id'])
        second = self.projects.create(self.actor, 'Other project')
        with self.assertRaises(TestRunNotFound):
            self.runs.get(self.actor, second.project_id, run['run_id'])

    def test_nonselected_unsupported_mutating_and_duplicate_cases_are_rejected(self):
        for cases in ((), ['LOGIN-001'], ('LOGIN-001', 'LOGIN-001'), ('UNKNOWN',),
                      ('SEARCH-001',), ('API-001',), ('DB-001',), ('LOGIN-009',), ('LOGIN-001',) * 11):
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                self.submit(cases)

    def test_selected_case_on_another_route_is_not_silently_rebound_to_root(self):
        job = self.prepare_report('http://127.0.0.1:8000/login')
        report = self.discovery.get(self.actor, self.pid, job)['report']
        login = next(case for case in report['cases'] if case['case_id'] == 'LOGIN-001')
        self.assertEqual(login['decision'], 'selected')
        self.assertEqual(login['target_binding'], 'local_form')
        self.assertEqual(login['document_path'], '/login')
        with self.assertRaises(ValueError):
            self.submit(job=job)

    def test_plan_from_another_project_cannot_authorize_run(self):
        second = self.projects.create(self.actor, 'Second')
        self.projects.save_configuration(self.actor, second.project_id, self.settings)
        with self.assertRaises(ValueError):
            self.runs.submit(self.actor, second.project_id, self.report_job, ('LOGIN-001',))

    def test_active_admission_is_bounded_and_queued_cancel_is_idempotent(self):
        jobs = [self.submit() for _ in range(5)]
        with self.assertRaises(ValueError):
            self.submit()
        first = jobs[0]['run_id']
        result = self.runs.cancel(self.actor, self.pid, first)
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(self.runs.cancel(self.actor, self.pid, first), result)
        self.assertEqual(self.submit()['status'], 'queued')
