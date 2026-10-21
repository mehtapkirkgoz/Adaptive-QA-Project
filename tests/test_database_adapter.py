"""Exercise SQLite policy with real disposable database files."""

from dataclasses import asdict, replace
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_adapter import run_database_case
from adaptive_qa.database_models import (
    DatabaseCase, DatabaseCheck, DatabaseConfiguration, DatabaseOperator, QueryTemplate,
)
from adaptive_qa.models import TestCase, TestStatus, TestType
from adaptive_qa.secrets import SecretReference


class DatabaseAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / 'private# fixture.db'
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('CREATE TABLE records (id INTEGER, name TEXT)')
            connection.executemany('INSERT INTO records VALUES (?, ?)', [(1, 'private-row'), (2, 'other')])
        self.environment = patch.dict(os.environ, {'QA_DB_TEST_PATH': str(self.path)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        project = ProjectConfig('db', 'Database', 'http://127.0.0.1:8000', ('127.0.0.1',))
        self.config = DatabaseConfiguration(project, SecretReference('QA_DB_TEST_PATH'))
        self.definition = TestCase('DB-TEST', 'Read record', TestType.DATABASE, (),
                                   ('Query fixture',), 'Configured rows match.')

    def run_query(self, sql, checks=None, parameters=(), configuration=None, **kwargs):
        template = QueryTemplate('db', 'query', sql, tuple(name for name, _ in parameters))
        case = DatabaseCase(self.definition, template, parameters,
                            checks or (DatabaseCheck(DatabaseOperator.ROW_COUNT, 1),))
        return run_database_case(case, configuration or self.config, fixture_root=self.root, **kwargs)

    def test_bound_values_cannot_turn_into_sql(self):
        result = self.run_query('SELECT id FROM records WHERE name = :name',
            (DatabaseCheck(DatabaseOperator.ROW_COUNT, 0),), (('name', "' OR 1=1 --"),))
        self.assertEqual(result.status, TestStatus.PASSED)

    def test_row_and_cell_assertions_preserve_failure_and_hide_values(self):
        result = self.run_query('SELECT name FROM records WHERE id=1',
            (DatabaseCheck(DatabaseOperator.CELL_EQUALS, 'private-expected'),))
        self.assertEqual(result.status, TestStatus.FAILED)
        report = json.dumps(asdict(result))
        for private in ('private-row', 'private-expected', str(self.path), 'SELECT'):
            self.assertNotIn(private, report)

    def test_write_attach_pragma_and_dangerous_functions_are_denied(self):
        before = self.path.read_bytes()
        for sql in ('DELETE FROM records', 'DROP TABLE records',
                    'PRAGMA query_only=OFF', "ATTACH DATABASE ':memory:' AS extra",
                    "SELECT load_extension('private-path')", "VACUUM INTO 'private-copy.db'",
                    'CREATE TEMP TABLE leaked (id INTEGER)'):
            with self.subTest(sql=sql):
                self.assertEqual(self.run_query(sql).status, TestStatus.BLOCKED)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_row_byte_and_blob_limits_are_errors_not_partial_success(self):
        limited = replace(self.config, max_rows=1)
        self.assertEqual(self.run_query('SELECT id FROM records', configuration=limited).status, TestStatus.ERROR)
        limited = replace(self.config, max_result_bytes=1024)
        self.assertEqual(self.run_query("SELECT '" + 'x' * 2000 + "'", configuration=limited).status, TestStatus.ERROR)
        self.assertEqual(self.run_query("SELECT x'0102'").status, TestStatus.ERROR)
        # Individual values fit SQLite's length bound but the aggregate exceeds it.
        limited = replace(self.config, max_result_bytes=32)
        self.assertEqual(self.run_query("SELECT 'abcdefghijklmnopqrst' UNION ALL SELECT 'abcdefghijklmnopqrst'",
                                        configuration=limited).status, TestStatus.ERROR)

    def test_invalid_sql_and_assertion_mismatch_have_distinct_statuses(self):
        self.assertEqual(self.run_query('SELECT missing FROM records').status, TestStatus.ERROR)
        self.assertEqual(self.run_query('SELECT id FROM records').status, TestStatus.FAILED)

    def test_recursive_query_deadline_and_cancellation_release_connection(self):
        query = 'WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT sum(x) FROM n'
        self.assertEqual(self.run_query(query, configuration=replace(self.config, timeout_seconds=0.02)).status,
                         TestStatus.ERROR)
        calls = 0
        def cancel():
            nonlocal calls
            calls += 1
            return calls > 3
        self.assertEqual(self.run_query(query, should_cancel=cancel).status, TestStatus.CANCELLED)
        with closing(sqlite3.connect(self.path, timeout=0)) as connection:
            connection.execute('BEGIN EXCLUSIVE')
            connection.rollback()

    def test_missing_reference_wrong_project_and_outside_paths_do_not_connect(self):
        template = QueryTemplate('other', 'query', 'SELECT 1')
        case = DatabaseCase(self.definition, template, (), (DatabaseCheck(DatabaseOperator.ROW_COUNT, 1),))
        with patch('sqlite3.connect', side_effect=AssertionError('Unexpected connection')):
            self.assertEqual(run_database_case(case, self.config, fixture_root=self.root).status, TestStatus.BLOCKED)
            self.assertEqual(run_database_case(case, None, fixture_root=self.root).status, TestStatus.BLOCKED)
            with patch.dict(os.environ, {'QA_DB_TEST_PATH': str(self.root / 'missing.db')}):
                self.assertEqual(self.run_query('SELECT 1').status, TestStatus.BLOCKED)
            with patch.dict(os.environ, {'QA_DB_TEST_PATH': str(self.path)}):
                self.assertEqual(run_database_case(replace(case, template=replace(template, project_id='db')),
                    self.config, fixture_root=self.root / 'missing').status, TestStatus.BLOCKED)
            child = self.root / 'authorized'
            child.mkdir()
            self.assertEqual(run_database_case(replace(case, template=replace(template, project_id='db')),
                self.config, fixture_root=child).status, TestStatus.BLOCKED)

    def test_nonlocal_project_is_blocked(self):
        project = replace(self.config.project, base_url='https://example.com', allowed_hosts=('example.com',))
        with patch('sqlite3.connect', side_effect=AssertionError('Unexpected connection')):
            self.assertEqual(self.run_query('SELECT 1', configuration=replace(self.config, project=project)).status,
                             TestStatus.BLOCKED)


if __name__ == '__main__':
    unittest.main()
