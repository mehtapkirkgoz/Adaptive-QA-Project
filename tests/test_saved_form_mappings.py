"""Saved project mappings bind discovery and execution without resolving secrets."""
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.project_store import ProjectStore, ProjectActor
from adaptive_qa.organization_store import OrganizationStore
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
from adaptive_qa.organization_runs import OrganizationRunQueue
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.dashboard_run_worker import process_run_once
from adaptive_qa.discovery import PageSnapshot, FormSnapshot, FieldSnapshot
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.form_configuration import runtime_configuration
from adaptive_qa.local_runtime import _check_form_mapping_support
from adaptive_qa.agent_registry import AgentRegistry
from adaptive_qa.agent_broker import AgentBroker


class SavedFormMappingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.projects = ProjectStore(Path(self.temp.name)/'projects.sqlite')
        self.actor = ProjectActor('a'*32)
        self.mapping = {'logical_name': 'login.submit', 'scope_test_id': None,
            'locators': [{'strategy': 'role', 'value': 'Continue', 'role': 'button'}]}
        self.settings = {'base_url': 'https://qa.example.test/account', 'allowed_hosts': ['qa.example.test'],
            'allow_data_changes': False, 'secret_references': {}, 'form_mappings': [self.mapping]}

    def scope(self, shared):
        if shared:
            organizations = OrganizationStore(self.projects)
            org = organizations.create(self.actor, 'Mapped team')
            store = OrganizationProjects(organizations)
            project = store.create(self.actor, org, 'Mapped project')['project_id']
            args = (self.actor, org, project)
            discovery = OrganizationDiscoveryQueue(store)
            return store, args, discovery, OrganizationRunQueue(discovery)
        project = self.projects.create(self.actor, 'Mapped project').project_id
        return self.projects, (self.actor, project), DashboardDiscoveryQueue(self.projects), DashboardRunQueue(self.projects)

    def test_scoped_mapping_roundtrip_and_invalid_replacement_is_atomic(self):
        for shared in (False, True):
            store, args, _, _ = self.scope(shared)
            with patch('socket.getaddrinfo', side_effect=AssertionError('Saving must not resolve DNS')):
                saved = store.save_configuration(*args, self.settings)
            self.assertEqual(saved['form_mappings'], [self.mapping])
            for raw in ([self.mapping]*2, [{**self.mapping, 'logical_name': 'unknown.key'}],
                        [{**self.mapping, 'extra': True}], 'untyped'):
                with self.assertRaises(ValueError):
                    store.save_configuration(*args, dict(self.settings, form_mappings=raw))
                self.assertEqual(store.configuration(*args)['form_mappings'], [self.mapping])

    def discover(self, queue, args):
        job = queue.submit(*args)
        form = FormSnapshot(fields=(FieldSnapshot('text', 'Username'), FieldSnapshot('password', 'Password')),
                            buttons=('Continue',))
        payload = {'pages': [asdict(PageSnapshot(self.settings['base_url'], (form,), (), True))], 'limitations': []}
        with patch('adaptive_qa.dashboard_worker.discover_configured_target', return_value=payload):
            self.assertEqual(process_discovery_once(queue)['status'], 'completed')
        return job

    def test_saved_alias_selects_real_observed_action_and_worker_receives_project_mapping(self):
        for shared in (False, True):
            store, args, queue, runs = self.scope(shared)
            store.save_configuration(*args, self.settings)
            job = self.discover(queue, args)
            run = runs.submit(*args, job['job_id'], ('LOGIN-001',))
            with patch('adaptive_qa.dashboard_run_worker.run_isolated_form_test',
                       return_value=TestResult('LOGIN-001', TestStatus.PASSED, 0.1, 'Controlled result.')) as child:
                self.assertEqual(process_run_once(runs)['status'], 'completed')
                mappings = child.call_args.kwargs['mappings']
                self.assertEqual(mappings.project_id, args[-1])
                self.assertEqual(mappings.mappings[0].locators[0].value, 'Continue')
            self.assertEqual(len(runs.get(*args, run['run_id'])['results']), 1)
            if shared:
                local_url = 'http://127.0.0.1:8000/'
                store.save_configuration(*args, dict(self.settings, base_url=local_url, allowed_hosts=['127.0.0.1']))
                local_job = queue.submit(*args)
                form = FormSnapshot(fields=(FieldSnapshot('text', 'Username'), FieldSnapshot('password', 'Password')),
                                    buttons=('Continue',))
                payload = {'pages': [asdict(PageSnapshot(local_url, (form,), (), True))], 'limitations': []}
                with patch('adaptive_qa.dashboard_worker.discover_local_sample', return_value=payload):
                    process_discovery_once(queue)
                pending = runs.submit(*args, local_job['job_id'], ('LOGIN-001',))
                registry = AgentRegistry(store)
                grant = registry.issue(*args)
                identity = registry.authenticate(grant.agent_id, grant.token.value, 1)
                self.assertIsNone(AgentBroker(registry, runs).claim(identity))
                self.assertEqual(runs.get(*args, pending['run_id'])['status'], 'queued')
                runs.cancel(*args, pending['run_id'])

    def test_mapping_change_invalidates_report_and_prevents_pending_dispatch(self):
        for shared in (False, True):
            store, args, queue, runs = self.scope(shared)
            store.save_configuration(*args, self.settings)
            job = self.discover(queue, args)
            runs.submit(*args, job['job_id'], ('LOGIN-001',))
            store.save_configuration(*args, dict(self.settings, form_mappings=[]))
            with self.assertRaises(ValueError):
                runs.submit(*args, job['job_id'], ('LOGIN-001',))
            with patch('adaptive_qa.dashboard_run_worker.run_isolated_form_test') as child:
                process_run_once(runs)
                child.assert_not_called()

    def test_empty_mapping_preserves_legacy_snapshot_and_excludes_secret_references(self):
        legacy = {key: self.settings[key] for key in ('base_url', 'allowed_hosts', 'allow_data_changes')}
        self.assertEqual(runtime_configuration(dict(self.settings, form_mappings=[])), legacy)

    def test_old_release_cannot_silently_ignore_saved_mapping_configuration(self):
        release = Path(self.temp.name)/'release'
        release.mkdir()
        _check_form_mapping_support(release, Path(self.temp.name))
        project = self.projects.create(self.actor, 'Mapped project')
        self.projects.save_configuration(self.actor, project.project_id, self.settings)
        with self.assertRaisesRegex(ValueError, 'cannot interpret'):
            _check_form_mapping_support(release, Path(self.temp.name))
        module = release/'site/adaptive_qa/form_configuration.py'
        module.parent.mkdir(parents=True); module.write_text('# trusted test capability marker', encoding='utf-8')
        _check_form_mapping_support(release, Path(self.temp.name))
