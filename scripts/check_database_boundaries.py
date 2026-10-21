"""Real isolated SQLite boundaries; retain outcomes, never private inputs."""

from contextlib import closing
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from time import monotonic
from uuid import uuid4

from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_catalog import DATABASE_CASES
from adaptive_qa.database_models import DatabaseConfiguration, QueryTemplate
from adaptive_qa.database_process import run_isolated_database_case
from adaptive_qa.models import TestStatus
from adaptive_qa.sample_database import prepare_sample_database
from adaptive_qa.secrets import SecretReference


def main():
    variable = 'QA_DATABASE_BOUNDARY_PATH'
    previous = os.environ.get(variable)
    checks = []
    reverse = []
    sentinel = uuid4().hex
    try:
        with TemporaryDirectory(prefix='adaptive-qa-db-boundaries-') as temporary:
            root = Path(temporary)
            allowed = root / 'allowed'
            allowed.mkdir()
            path = prepare_sample_database(allowed / (sentinel + '.db'))
            original = path.read_bytes()
            os.environ[variable] = str(path)
            project = ProjectConfig('local-database', 'Database boundaries',
                'http://127.0.0.1:8000', ('127.0.0.1',))
            config = DatabaseConfiguration(project, SecretReference(variable), timeout_seconds=10)
            base = DATABASE_CASES[0]

            def query(sql):
                return replace(base, template=QueryTemplate(project.project_id, 'boundary', sql), parameters=())

            def check(name, expected, case=base, configuration=config, **kwargs):
                started = monotonic()
                result = run_isolated_database_case(case, configuration, fixture_root=allowed, **kwargs)
                assert result.status == expected, (name, result)
                assert monotonic() - started < 8, name
                checks.append({'name': name, 'expected': expected, 'result': asdict(result)})

            check('missing_configuration', TestStatus.BLOCKED, configuration=None)
            check('foreign_project', TestStatus.BLOCKED,
                  configuration=replace(config, project=replace(project, project_id='foreign')))
            os.environ.pop(variable)
            check('missing_reference', TestStatus.BLOCKED)
            os.environ[variable] = str(root / 'missing.db')
            check('missing_file_not_created', TestStatus.BLOCKED)
            assert not (root / 'missing.db').exists()
            outside = prepare_sample_database(root / 'outside.db')
            outside_before = outside.read_bytes()
            os.environ[variable] = str(outside)
            check('outside_fixture_root', TestStatus.BLOCKED)
            os.environ[variable] = str(path)
            for name, sql in (
                ('delete', 'DELETE FROM orders'),
                ('schema_write', 'DROP TABLE orders'),
                ('query_only_override', 'PRAGMA query_only=OFF'),
                ('attach', "ATTACH DATABASE ':memory:' AS extra"),
                ('extension', "SELECT load_extension('" + sentinel + "')"),
                ('temporary_write', 'CREATE TEMP TABLE leaked (id INTEGER)'),
            ):
                check(name, TestStatus.BLOCKED, query(sql))
            check('multiple_statements', TestStatus.ERROR, query('SELECT 1; DELETE FROM orders'))
            check('row_limit', TestStatus.ERROR, query('SELECT id FROM products'),
                  configuration=replace(config, max_rows=1))
            check('byte_limit', TestStatus.ERROR,
                  query("SELECT 'abcdefghijklmnopqrst' UNION ALL SELECT 'abcdefghijklmnopqrst'"),
                  configuration=replace(config, max_result_bytes=32))
            check('binary_result', TestStatus.ERROR, query("SELECT x'0102'"))
            corrupt = allowed / 'corrupt.db'
            corrupt.write_bytes(sentinel.encode())
            os.environ[variable] = str(corrupt)
            check('invalid_database', TestStatus.ERROR)
            os.environ[variable] = str(path)
            recursive = query('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT sum(x) FROM n')
            check('total_deadline', TestStatus.ERROR, recursive, timeout_seconds=0.5)
            started = monotonic()
            check('active_cancellation', TestStatus.CANCELLED, recursive,
                  should_cancel=lambda: monotonic() - started > 0.5)
            check('prestart_cancellation', TestStatus.CANCELLED, should_cancel=lambda: True)
            with closing(sqlite3.connect(path, timeout=0)) as connection:
                connection.execute('BEGIN EXCLUSIVE')
                connection.rollback()
            for case in reversed(DATABASE_CASES):
                result = run_isolated_database_case(case, config, fixture_root=allowed)
                assert result.status == TestStatus.PASSED, result
                reverse.append(asdict(result))
            assert path.read_bytes() == original and outside.read_bytes() == outside_before
            assert set(allowed.iterdir()) == {path, corrupt}
            encoded = json.dumps({'checks': len(checks), 'results': checks,
                'reverse_order': reverse, 'fixture_unchanged': True, 'outside_unchanged': True}, indent=2)
            for private in (sentinel, str(path), 'SELECT ', 'demo-user'):
                assert private not in encoded
        destination = Path('artifacts/database/boundaries.json')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(encoded, encoding='utf-8')
        print(f'{len(checks)} database boundaries and 15 reverse-order checks passed.')
    finally:
        if previous is None:
            os.environ.pop(variable, None)
        else:
            os.environ[variable] = previous


if __name__ == '__main__':
    main()
