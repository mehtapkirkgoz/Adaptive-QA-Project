"""Local selection cannot bypass trust, process leases, inventory or schema guards."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.backup import create_backup
from adaptive_qa.backup_restore import prepare_restore
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.local_runtime import prepare_local, select_local, component_lease, local_status, run_local
from adaptive_qa.project_store import ProjectStore


class LocalRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.plan = DeploymentPlan(Environment.LOCAL, self.root, 'http://127.0.0.1:8877')
        AuthStore(self.plan.directory / 'auth.sqlite')
        DashboardRunQueue(ProjectStore(self.plan.directory / 'projects.sqlite'))
        self.candidate = self.root / 'candidate'
        self.candidate.mkdir()
        self.wheel = self.candidate / 'adaptive_qa-0.1.0-py3-none-any.whl'
        with zipfile.ZipFile(self.wheel, 'w') as wheel:
            wheel.writestr('adaptive_qa/__init__.py', "raise AssertionError('Candidate must never execute during preparation')")
        with zipfile.ZipFile(self.candidate / 'dashboard.zip', 'w') as ui:
            ui.writestr('index.html', '<html>local fixture</html>')
            ui.writestr('assets/app.js', '// inert fixture')
        for name in ('requirements.lock.txt', 'frontend-package-lock.json'):
            (self.candidate / name).write_text('fixture', encoding='utf-8')
        self.manifest()

    def test_licensed_workspace_refuses_legacy_runtime_data_selection(self):
        from adaptive_qa.local_runtime import _data
        (self.plan.directory/'license.sqlite').write_bytes(b'licensed marker')
        with self.assertRaisesRegex(ValueError, 'cannot enforce local licensing'):
            _data(self.plan)

    def manifest(self):
        files = [{'name': path.name, 'bytes': path.stat().st_size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                 for path in self.candidate.iterdir() if path.name != 'release.json']
        (self.candidate / 'release.json').write_text(json.dumps({'schema_version': 1,
            'source_commit': 'a' * 40, 'activation_enabled': False,
            'database_schema_revisions': [0, 1], 'files': files}), encoding='utf-8')

    def prepare(self):
        return prepare_local(self.plan, self.candidate, 'a' * 40, maintenance_confirmed=True, trusted_release=True)

    def select(self, **options):
        return select_local(self.plan, 'a' * 40, maintenance_confirmed=True, **options)

    def test_preparation_does_not_execute_candidate_and_never_overwrites_release(self):
        self.assertFalse(self.prepare()['service_started'])
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.prepare()

    def test_trust_confirmation_and_local_only_profile_are_required(self):
        with self.assertRaises(ValueError):
            prepare_local(self.plan, self.candidate, 'a' * 40, maintenance_confirmed=True)
        staging = DeploymentPlan(Environment.STAGING, self.root, 'https://qa.example.test')
        with self.assertRaisesRegex(ValueError, 'local loopback'):
            prepare_local(staging, self.candidate, 'a' * 40, maintenance_confirmed=True, trusted_release=True)

    def test_stale_selection_never_changes_the_current_pointer(self):
        self.prepare()
        first = self.select()
        with self.assertRaisesRegex(ValueError, 'selection changed'):
            self.select()
        self.assertEqual(local_status(self.plan)['selection']['selection_id'], first['selection_id'])
        second = self.select(expected_selection=first['selection_id'])
        self.assertNotEqual(first['selection_id'], second['selection_id'])

    def test_component_lease_blocks_switches_and_duplicate_component_start(self):
        self.prepare()
        selected = self.select()
        with component_lease(self.plan, 'serve', selected['selection_id']):
            self.assertEqual(local_status(self.plan)['components']['serve'], 'active')
            with self.assertRaises(ValueError):
                self.select(expected_selection=selected['selection_id'])
            with self.assertRaises(ValueError):
                with component_lease(self.plan, 'serve', selected['selection_id']):
                    self.fail('Duplicate lease was admitted.')
        self.assertEqual(local_status(self.plan)['components']['serve'], 'inactive')

    def test_maintenance_lease_blocks_selection_and_duplicate_maintenance(self):
        self.prepare()
        selected = self.select()
        with component_lease(self.plan, 'maintenance-once', selected['selection_id']):
            self.assertEqual(local_status(self.plan)['components']['maintenance-once'], 'active')
            with self.assertRaises(ValueError):
                self.select(expected_selection=selected['selection_id'])
            with self.assertRaises(ValueError):
                with component_lease(self.plan, 'maintenance-once', selected['selection_id']):
                    self.fail('Duplicate maintenance was admitted.')
        self.assertEqual(local_status(self.plan)['components']['maintenance-once'], 'inactive')

    def test_maintenance_duration_is_bounded_before_startup(self):
        for duration in (True, 0, -1, 61, 180):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                run_local(self.plan, 'maintenance-once', duration_seconds=duration)

    def test_tampered_prepared_payload_is_refused_before_selection(self):
        self.prepare()
        (self.plan.directory / 'runtime/releases' / ('a' * 40) / 'ui/index.html').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'verification failed'):
            self.select()
        self.assertIsNone(local_status(self.plan)['selection'])

    def test_archive_traversal_is_rejected_and_no_release_is_published(self):
        with zipfile.ZipFile(self.wheel, 'a') as wheel:
            wheel.writestr('../outside.py', 'raise AssertionError()')
        self.manifest()
        with self.assertRaisesRegex(ValueError, 'unsupported or redirected'):
            self.prepare()
        releases = self.plan.directory / 'runtime/releases'
        self.assertEqual(list(releases.iterdir()), [])

    def test_changed_selection_is_refused_before_component_startup(self):
        self.prepare()
        selected = self.select()
        self.select(expected_selection=selected['selection_id'])
        with self.assertRaisesRegex(ValueError, 'changed before'):
            with component_lease(self.plan, 'run-once', selected['selection_id']):
                self.fail('Stale component was admitted.')

    def test_binary_reselection_preserves_recovery_data_unless_live_data_is_explicit(self):
        self.prepare()
        bundle = create_backup(self.plan, maintenance_confirmed=True)['bundle_id']
        recovery = prepare_restore(self.plan, bundle, maintenance_confirmed=True)['recovery_id']
        first = self.select(recovery_id=recovery)
        second = self.select(expected_selection=first['selection_id'])
        self.assertEqual(second['recovery_id'], recovery)
        third = self.select(expected_selection=second['selection_id'], use_live_data=True)
        self.assertIsNone(third['recovery_id'])
