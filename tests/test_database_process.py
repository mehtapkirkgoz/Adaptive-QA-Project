"""Exercise private transport and real child deadline/cancellation cleanup."""

from contextlib import closing
from dataclasses import replace
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from time import monotonic
import unittest
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_models import (
    DatabaseCase, DatabaseCheck, DatabaseConfiguration, DatabaseOperator, QueryTemplate,
)
from adaptive_qa.database_process import (
    decode_database_input, encode_database_input, run_isolated_database_case,
)
from adaptive_qa.models import TestCase, TestStatus, TestType
from adaptive_qa.secrets import SecretReference


class DatabaseProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / 'private database.db'
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('CREATE TABLE records (name TEXT)')
            connection.execute('INSERT INTO records VALUES (?)', ('private-value',))
        environment = patch.dict(os.environ, {'QA_DB_CHILD_PATH': str(self.path)})
        environment.start()
        self.addCleanup(environment.stop)
        project = ProjectConfig('db', 'Database', 'http://127.0.0.1:8000', ('127.0.0.1',))
        self.config = DatabaseConfiguration(project, SecretReference('QA_DB_CHILD_PATH'), timeout_seconds=10)
        definition = TestCase('DB-CHILD', 'Read fixture', TestType.DATABASE, (),
                              ('Read record',), 'One record matches.')
        template = QueryTemplate('db', 'record', 'SELECT name FROM records WHERE name=:name', ('name',))
        self.case = DatabaseCase(definition, template, (('name', 'private-value'),),
            (DatabaseCheck(DatabaseOperator.ROW_COUNT, 1),))

    def run_child(self, case=None, **kwargs):
        return run_isolated_database_case(case or self.case, self.config, fixture_root=self.root, **kwargs)

    def test_roundtrip_keeps_reference_and_immutable_contracts(self):
        encoded = encode_database_input(self.case, self.config, self.root)
        # Fixture root is private transport; the resolved database filename is absent.
        self.assertNotIn(self.path.name, encoded)
        case, config, root = decode_database_input(encoded)
        self.assertEqual((case, config, root), (self.case, self.config, self.root))

    def test_real_child_returns_safe_pass_and_assertion_failure(self):
        self.assertEqual(self.run_child().status, TestStatus.PASSED)
        case = replace(self.case, checks=(DatabaseCheck(DatabaseOperator.CELL_EQUALS, 'wrong'),))
        result = self.run_child(case)
        self.assertEqual(result.status, TestStatus.FAILED)
        self.assertNotIn('private-value', repr(result))
        self.assertNotIn(str(self.path), repr(result))

    def test_real_child_preserves_write_rejection(self):
        case = replace(self.case, template=QueryTemplate('db', 'write', 'DELETE FROM records'), parameters=())
        self.assertEqual(self.run_child(case).status, TestStatus.BLOCKED)
        self.assertEqual(self.run_child().status, TestStatus.PASSED)

    def test_real_total_deadline_stops_recursive_child_and_releases_file(self):
        query = 'WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT sum(x) FROM n'
        case = replace(self.case, template=QueryTemplate('db', 'recursive', query), parameters=())
        started = monotonic()
        result = self.run_child(case, timeout_seconds=0.5)
        self.assertEqual(result.status, TestStatus.ERROR)
        self.assertLess(monotonic() - started, 5)
        self.assertIn('total time limit', result.message)
        with closing(sqlite3.connect(self.path, timeout=0)) as connection:
            connection.execute('BEGIN EXCLUSIVE')
            connection.rollback()

    def test_real_active_cancellation_releases_child(self):
        query = 'WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT sum(x) FROM n'
        case = replace(self.case, template=QueryTemplate('db', 'recursive', query), parameters=())
        started = monotonic()
        result = self.run_child(case, should_cancel=lambda: monotonic() - started > 0.5)
        self.assertEqual(result.status, TestStatus.CANCELLED)
        self.assertLess(monotonic() - started, 5)
        self.assertEqual(self.run_child().status, TestStatus.PASSED)

    def test_prestart_block_and_cancel_never_spawn(self):
        with patch('adaptive_qa.database_process.subprocess.Popen') as popen:
            self.assertEqual(self.run_child(should_cancel=lambda: True).status, TestStatus.CANCELLED)
            self.assertEqual(run_isolated_database_case(self.case, None, fixture_root=self.root).status,
                             TestStatus.BLOCKED)
            other = replace(self.case, template=replace(self.case.template, project_id='other'))
            self.assertEqual(self.run_child(other).status, TestStatus.BLOCKED)
            popen.assert_not_called()

    def test_invalid_deadlines_are_rejected(self):
        for timeout in (True, 0, float('nan'), 61):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.run_child(timeout_seconds=timeout)

    def test_missing_child_output_cannot_pass(self):
        with patch('adaptive_qa.database_process.subprocess.Popen') as popen:
            popen.return_value.returncode = 0
            popen.return_value.poll.return_value = 0
            self.assertEqual(self.run_child().status, TestStatus.ERROR)


if __name__ == '__main__':
    unittest.main()
