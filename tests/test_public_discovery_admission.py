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
from adaptive_qa.discovery import PageSnapshot
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
                self.assertEqual(settings['discovery_support']['execution_scope'], 'discovery_only')
                job = queue.submit(*args)
                self.assertEqual(job['status'], 'queued')
                self.assertNotIn('report', job)
                queue.cancel(*args, job['job_id'])

    def test_worker_rebuilds_scoped_public_report_without_enabling_test_execution(self):
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
            self.assertTrue(all(case['target_binding'] is None for case in report['cases']))
            with self.assertRaises(ValueError):
                runs.submit(*args, job['job_id'], ('DOC-001',))

    def test_foreign_payload_cannot_escape_public_project_scope(self):
        _, queue, args, _ = self.setup_scope(False)
        job = queue.submit(*args)
        payload = {'pages': [asdict(PageSnapshot('https://foreign.example.test/', (), (), True))], 'limitations': []}
        with patch('adaptive_qa.dashboard_worker.discover_configured_target', return_value=payload):
            self.assertEqual(process_discovery_once(queue)['status'], 'error')
        self.assertNotIn('report', queue.get(*args, job['job_id']))
