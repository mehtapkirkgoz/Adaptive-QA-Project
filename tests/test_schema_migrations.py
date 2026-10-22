"""Legacy copies migrate additively; unsupported revisions never reach publication."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.backup import create_backup
from adaptive_qa.backup_restore import prepare_restore
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.project_store import ProjectActor, ProjectStore
from adaptive_qa.schema_migrations import migrate_recovery_connection


class RecoveryMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plan = DeploymentPlan(Environment.STAGING, Path(self.temp.name), 'https://qa.example.test')
        AuthStore(self.plan.directory / 'auth.sqlite')
        projects = ProjectStore(self.plan.directory / 'projects.sqlite')
        projects.create(ProjectActor('a' * 32), 'Preserved project')
        DashboardRunQueue(projects)

    def backup_and_restore(self):
        bundle = create_backup(self.plan, maintenance_confirmed=True)['bundle_id']
        result = prepare_restore(self.plan, bundle, maintenance_confirmed=True)
        return self.plan.directory / 'recovery' / result['recovery_id']

    def test_legacy_columns_are_added_only_to_copies_and_reapplication_is_idempotent(self):
        source = self.plan.directory / 'projects.sqlite'
        with closing(sqlite3.connect(source)) as connection:
            connection.execute('DROP INDEX dashboard_evidence_expiry')
            for table, column in (('dashboard_run_evidence', 'expires_at'),
                                  ('dashboard_test_runs', 'rerun_of'),
                                  ('dashboard_discovery_jobs', 'report_json')):
                connection.execute(f'ALTER TABLE {table} DROP COLUMN {column}')
            connection.commit()
        original = source.read_bytes()
        target = self.backup_and_restore()
        self.assertEqual(source.read_bytes(), original)
        with closing(sqlite3.connect(target / 'projects.sqlite')) as connection:
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT name FROM dashboard_projects').fetchone()[0], 'Preserved project')
            self.assertEqual(migrate_recovery_connection(connection, 'projects.sqlite')['added_columns'], [])
        metadata = json.loads((target / 'recovery.json').read_text())
        self.assertEqual(set(metadata['migrations']['projects.sqlite']['added_columns']),
                         {'dashboard_run_evidence.expires_at', 'dashboard_test_runs.rerun_of',
                          'dashboard_discovery_jobs.report_json'})

    def test_future_revision_refuses_downgrade_and_removes_partial_recovery(self):
        path = self.plan.directory / 'auth.sqlite'
        with closing(sqlite3.connect(path)) as connection:
            connection.execute('PRAGMA user_version=7')
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'downgrade'):
            self.backup_and_restore()
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list((self.plan.directory / 'recovery').iterdir()), [])

    def test_versioned_database_missing_an_expected_column_is_not_repaired_silently(self):
        with closing(sqlite3.connect(self.plan.directory / 'projects.sqlite')) as connection:
            connection.execute('ALTER TABLE dashboard_test_runs DROP COLUMN rerun_of')
            connection.execute('PRAGMA user_version=1')
        with self.assertRaisesRegex(ValueError, 'missing required'):
            self.backup_and_restore()
        self.assertEqual(list((self.plan.directory / 'recovery').iterdir()), [])

    def test_unknown_core_schema_is_rejected_without_publishing_fake_empty_tables(self):
        with closing(sqlite3.connect(self.plan.directory / 'projects.sqlite')) as connection:
            connection.execute('ALTER TABLE dashboard_discovery_jobs DROP COLUMN configuration_json')
        with self.assertRaisesRegex(ValueError, 'core columns'):
            self.backup_and_restore()
        self.assertEqual(list((self.plan.directory / 'recovery').iterdir()), [])
