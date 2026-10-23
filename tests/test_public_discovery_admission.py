"""HTTPS queue/report integration with no external traffic or executor activation."""

from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.project_store import ProjectStore, ProjectActor
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.discovery import PageSnapshot, FormSnapshot, FieldSnapshot
from adaptive_qa.dashboard_run_worker import process_run_once
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.organization_store import OrganizationStore
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
from adaptive_qa.organization_runs import OrganizationRunQueue


class PublicDiscoveryAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.projects = ProjectStore(Path(self.temporary.name)/'projects.sqlite')
        self.actor = ProjectActor('a'*32)
        self.settings = {'base_url': 'https://qa.example.test/start', 'allowed_hosts': ['qa.example.test'],
                         'allow_data_changes': False, 'secret_references': {}}

    def setup_scope(self, shared):
        if shared:
            organizations = OrganizationStore(self.projects)
            organization = organizations.create(self.actor, 'Public scope')
            scoped = OrganizationProjects(organizations)
            project = scoped.create(self.actor, organization, 'HTTPS discovery')['project_id']
            settings = scoped.save_configuration(self.actor, organization, project, self.settings)
            queue = OrganizationDiscoveryQueue(scoped)
            args = (self.actor, organization, project)
            runs = OrganizationRunQueue(queue)
        else:
            project = self.projects.create(self.actor, 'HTTPS discovery').project_id
            settings = self.projects.save_configuration(self.actor, project, self.settings)
            queue = DashboardDiscoveryQueue(self.projects)
            args = (self.actor, project)
            runs = DashboardRunQueue(self.projects)
        return settings, queue, args, runs

    def test_personal_and_shared_admission_do_not_resolve_or_execute(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('Admission must not resolve DNS')), \
                patch('socket.socket', side_effect=AssertionError('Admission must not connect')):
            for shared in (False, True):
                settings, queue, args, _ = self.setup_scope(shared)
                self.assertEqual(settings['discovery_support']['profile'], 'public_https')
                self.assertEqual(settings['discovery_support']['execution_scope'], 'document_and_form_ui')
                job = queue.submit(*args)
                self.assertEqual(job['status'], 'queued')
                self.assertNotIn('report', job)
                queue.cancel(*args, job['job_id'])

    def test_worker_rebuilds_scoped_public_report_and_admits_only_explicit_document_selection(self):
        for shared in (False, True):
            _, queue, args, runs = self.setup_scope(shared)
            job = queue.submit(*args)
            payload = {'pages': [asdict(PageSnapshot(self.settings['base_url'], (), (), True))], 'limitations': [],
                       'plan': {'execution_authorized': True}}
            with patch('adaptive_qa.dashboard_worker.discover_configured_target', return_value=payload) as child:
                self.assertEqual(process_discovery_once(queue)['status'], 'completed')
                self.assertEqual(child.call_args.kwargs['profile'], 'public_https')
            report = queue.get(*args, job['job_id'])['report']
            self.assertFalse(report['execution_authorized'])
            self.assertEqual(report['discovery_profile'], 'public_https')
            self.assertEqual(report['counts']['catalog'], 100)
            documents = [case for case in report['cases'] if case['target_binding'] == 'public_document']
            self.assertEqual(len(documents), 5)
            self.assertTrue(all(case['document_url'] == self.settings['base_url'] for case in documents))
            with patch('socket.getaddrinfo', side_effect=AssertionError('Admission must not resolve DNS')):
                run = runs.submit(*args, job['job_id'], ('DOC-001',))
            self.assertEqual(run['status'], 'queued')
            self.assertFalse(run['results'])
            runs.cancel(*args, run['run_id'])
            with self.assertRaises(ValueError):
                runs.submit(*args, job['job_id'], ('LOGIN-001',))

    def test_foreign_payload_cannot_escape_public_project_scope(self):
        _, queue, args, _ = self.setup_scope(False)
        job = queue.submit(*args)
        payload = {'pages': [asdict(PageSnapshot('https://foreign.example.test/', (), (), True))], 'limitations': []}
        with patch('adaptive_qa.dashboard_worker.discover_configured_target', return_value=payload):
            self.assertEqual(process_discovery_once(queue)['status'], 'error')
        self.assertNotIn('report', queue.get(*args, job['job_id']))

    def test_personal_and_shared_worker_route_only_document_cases_to_saved_https_target(self):
        for shared in (False, True):
            _, queue, args, runs = self.setup_scope(shared)
            job = queue.submit(*args)
            payload = {'pages': [asdict(PageSnapshot(self.settings['base_url'], (), (), True))], 'limitations': []}
            with patch('adaptive_qa.dashboard_worker.discover_configured_target', return_value=payload):
                process_discovery_once(queue)
            run = runs.submit(*args, job['job_id'], ('DOC-001',))
            outcome = TestResult('DOC-001', TestStatus.PASSED, 0.1, 'Controlled test result.')
            with patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test', return_value=outcome) as child, \
                    patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test') as sample:
                self.assertEqual(process_run_once(runs)['status'], 'completed')
                sample.assert_not_called()
                self.assertEqual(child.call_args.args[1].base_url, self.settings['base_url'])
                self.assertLessEqual(child.call_args.kwargs['timeout_seconds'], 30)
            saved = runs.get(*args, run['run_id'])
            self.assertEqual(len(saved['results']), 1)

    def test_changed_public_configuration_prevents_dispatch(self):
        _, queue, args, runs = self.setup_scope(False)
        job = queue.submit(*args)
        payload = {'pages': [asdict(PageSnapshot(self.settings['base_url'], (), (), True))], 'limitations': []}
        with patch('adaptive_qa.dashboard_worker.discover_configured_target', return_value=payload):
            process_discovery_once(queue)
        runs.submit(*args, job['job_id'], ('DOC-001',))
        self.projects.save_configuration(self.actor, args[-1], dict(self.settings, base_url='https://qa.example.test/changed'))
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test') as child:
            self.assertEqual(process_run_once(runs)['status'], 'error')
            child.assert_not_called()

    def test_personal_and_shared_public_form_selection_uses_only_read_only_form_worker(self):
        for shared in (False, True):
            _, queue, args, runs = self.setup_scope(shared)
            job = queue.submit(*args)
            forms = (FormSnapshot(fields=(FieldSnapshot('text', 'Username'), FieldSnapshot('password', 'Password')),
                                  buttons=('Sign in',)),
                     FormSnapshot(role='search', fields=(FieldSnapshot('search', 'Search products'),), buttons=('Search',)))
            payload = {'pages': [asdict(PageSnapshot(self.settings['base_url'], forms, (), True))], 'limitations': []}
            with patch('adaptive_qa.dashboard_worker.discover_configured_target', return_value=payload):
                process_discovery_once(queue)
            report = queue.get(*args, job['job_id'])['report']
            forms_bound = [case for case in report['cases'] if case['target_binding'] == 'public_form']
            self.assertEqual({case['case_id'] for case in forms_bound}, {'LOGIN-001', 'SEARCH-001'})
            with patch('socket.getaddrinfo', side_effect=AssertionError('Admission must not connect')):
                run = runs.submit(*args, job['job_id'], ('LOGIN-001', 'SEARCH-001'))
            def form_result(case_id, project, **kwargs):
                self.assertEqual(project.base_url, self.settings['base_url'])
                return TestResult(case_id, TestStatus.PASSED, 0.1, 'Controlled form result.')
            with patch('adaptive_qa.dashboard_run_worker.run_isolated_form_test', side_effect=form_result) as child, \
                    patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test') as document, \
                    patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test') as sample:
                self.assertEqual(process_run_once(runs)['status'], 'completed')
                self.assertEqual(child.call_count, 2)
                document.assert_not_called(); sample.assert_not_called()
            self.assertEqual(len(runs.get(*args, run['run_id'])['results']), 2)
            with self.assertRaises(ValueError):
                runs.submit(*args, job['job_id'], ('LOGIN-002',))
