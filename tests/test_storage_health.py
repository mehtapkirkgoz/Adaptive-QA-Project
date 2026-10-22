"""Operator checks are bounded, fail closed and never output stored records."""

from contextlib import closing, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.__main__ import main
from adaptive_qa.auth_store import AuthStore
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.project_store import ProjectActor, ProjectStore
from adaptive_qa.storage_health import storage_health


class StorageHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plan = DeploymentPlan(Environment.LOCAL, Path(self.temp.name), 'http://127.0.0.1:8765')
        AuthStore(self.plan.directory / 'auth.sqlite')
        store = ProjectStore(self.plan.directory / 'projects.sqlite')
        store.create(ProjectActor('a' * 32), 'private project record')
        DashboardRunQueue(store)

    def test_ready_cli_output_has_no_records_paths_network_or_processes(self):
        output = StringIO()
        before = {path.name: path.read_bytes() for path in self.plan.directory.iterdir()}
        with patch('sys.argv', ['adaptive-qa', 'deployment', 'storage-health', '--environment', 'local',
                '--data-root', str(self.plan.data_root), '--origin', self.plan.public_origin]), \
                redirect_stdout(output), patch('socket.socket', side_effect=AssertionError('No network')), \
                patch('subprocess.Popen', side_effect=AssertionError('No processes')):
            main()
        result = json.loads(output.getvalue())
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['scope'], 'database_storage_only')
        self.assertNotIn('private project record', output.getvalue())
        self.assertNotIn(str(self.plan.data_root), output.getvalue())
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.plan.directory.iterdir()})

    def test_missing_database_is_not_created_and_cli_returns_failure(self):
        path = self.plan.directory / 'auth.sqlite'
        path.unlink()
        with patch('sys.argv', ['adaptive-qa', 'deployment', 'storage-health', '--environment', 'local',
                '--data-root', str(self.plan.data_root), '--origin', self.plan.public_origin]), redirect_stdout(StringIO()):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(path.exists())

    def test_future_schema_and_corrupt_files_return_generic_unavailability(self):
        with closing(sqlite3.connect(self.plan.directory / 'auth.sqlite')) as connection:
            connection.execute('PRAGMA user_version=99')
        (self.plan.directory / 'projects.sqlite').write_bytes(b'private corrupt fixture')
        result = storage_health(self.plan)
        self.assertEqual(result['status'], 'unavailable')
        self.assertTrue(all(item['status'] == 'unavailable' for item in result['databases'].values()))
        self.assertNotIn('private corrupt fixture', str(result))

    def test_shared_hardlink_is_rejected(self):
        source = self.plan.directory / 'projects.sqlite'
        os.link(source, self.plan.data_root / 'shared.sqlite')
        self.assertEqual(storage_health(self.plan)['databases']['projects.sqlite']['status'], 'unavailable')

    def test_verification_deadline_is_not_reported_as_ready(self):
        with patch('adaptive_qa.storage_health.monotonic', side_effect=[0, 3, 0, 3]):
            result = storage_health(self.plan)
        self.assertEqual(result['status'], 'unavailable')

    def test_exclusive_lock_produces_bounded_unavailability(self):
        with closing(sqlite3.connect(self.plan.directory / 'projects.sqlite')) as writer:
            writer.execute('BEGIN EXCLUSIVE')
            self.assertEqual(storage_health(self.plan)['databases']['projects.sqlite']['status'], 'unavailable')
            writer.rollback()
