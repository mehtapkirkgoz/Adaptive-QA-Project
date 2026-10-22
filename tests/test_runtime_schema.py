"""Runtime refuses future/inconsistent schemas before DDL or application writes."""

from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.project_store import ProjectActor, ProjectStore
from adaptive_qa.schema_migrations import migrate_recovery_connection


class RuntimeSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_future_auth_and_project_files_remain_byte_identical_on_startup_rejection(self):
        for factory, name in ((AuthStore, 'credentials.db'), (ProjectStore, 'projects.db')):
            path = self.root / name
            with closing(sqlite3.connect(path)) as connection:
                connection.execute('CREATE TABLE future_format(private_value TEXT)')
                connection.execute('PRAGMA user_version=9')
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'runtime access refused'):
                factory(path)
            self.assertEqual(path.read_bytes(), original)

    def test_existing_store_rechecks_revision_before_writing_a_project(self):
        path = self.root / 'projects.sqlite'
        store = ProjectStore(path)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute('PRAGMA user_version=9')
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'runtime access refused'):
            store.create(ProjectActor('a' * 32), 'Must not be written')
        self.assertEqual(path.read_bytes(), original)

    def test_inconsistent_versioned_schema_is_not_repaired_by_queue_initialization(self):
        path = self.root / 'projects.sqlite'
        store = ProjectStore(path)
        DashboardRunQueue(store)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute('ALTER TABLE dashboard_test_runs DROP COLUMN rerun_of')
            connection.execute('PRAGMA user_version=1')
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            DashboardRunQueue(store)
        self.assertEqual(path.read_bytes(), original)

    def test_valid_version_one_stores_open_and_preserve_projects(self):
        projects_path, auth_path = self.root / 'projects.sqlite', self.root / 'auth.sqlite'
        store = ProjectStore(projects_path)
        project = store.create(ProjectActor('a' * 32), 'Retained project')
        DashboardRunQueue(store)
        AuthStore(auth_path)
        for path, kind in ((projects_path, 'projects.sqlite'), (auth_path, 'auth.sqlite')):
            with closing(sqlite3.connect(path)) as connection:
                migrate_recovery_connection(connection, kind)
                connection.commit()
        AuthStore(auth_path)
        DashboardRunQueue(ProjectStore(projects_path))
        with closing(sqlite3.connect(projects_path)) as connection:
            self.assertEqual(connection.execute('SELECT project_id FROM dashboard_projects').fetchone()[0], project.project_id)

    def test_legacy_initialization_is_not_silently_stamped_as_migrated(self):
        path = self.root / 'projects.sqlite'
        DashboardRunQueue(ProjectStore(path))
        with closing(sqlite3.connect(path)) as connection:
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 0)
