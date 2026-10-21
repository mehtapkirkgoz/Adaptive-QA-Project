"""Read-only SQLite validation for explicitly supplied local fixture roots.

This in-process primitive uses cooperative SQLite deadlines. Callers requiring
a hard wall-clock deadline must use process isolation before exposing execution.
"""

import json
from pathlib import Path
import sqlite3
from time import monotonic, perf_counter

from adaptive_qa.database_models import DatabaseCase, DatabaseConfiguration, DatabaseOperator
from adaptive_qa.models import TestResult, TestStatus


class DatabasePolicyError(Exception):
    """Private configuration or SQLite authorization rejected execution."""


def _fixture_path(configuration, fixture_root):
    if configuration.project.base_url.rstrip('/') != 'http://127.0.0.1:8000':
        raise DatabasePolicyError()
    try:
        raw = configuration.database_path.resolve().value
        path = Path(raw)
        root = Path(fixture_root).resolve(strict=True)
        if not path.is_absolute() or not root.is_dir():
            raise DatabasePolicyError()
        path = path.resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise DatabasePolicyError()
        return path
    except (OSError, ValueError, TypeError):
        raise DatabasePolicyError() from None


def _equal(actual, expected):
    # SQLite boolean bindings are represented as integers. Explicit booleans
    # match only their corresponding 0/1 integer; other scalars stay typed.
    if type(expected) is bool:
        return type(actual) is int and actual == int(expected)
    numeric = type(actual) in (int, float) and type(expected) in (int, float)
    return (numeric or type(actual) is type(expected)) and actual == expected


def run_database_case(case, configuration, *, fixture_root, should_cancel=None):
    """Return metadata only; never expose rows, SQL, paths, or SQLite messages."""
    if not isinstance(case, DatabaseCase):
        raise ValueError('case must be a DatabaseCase.')
    if configuration is not None and not isinstance(configuration, DatabaseConfiguration):
        raise ValueError('configuration must be a DatabaseConfiguration or None.')
    started = perf_counter()

    def outcome(status, message):
        return TestResult(case.definition.case_id, status, perf_counter() - started, message)

    if configuration is None:
        return outcome(TestStatus.BLOCKED, 'Database configuration is missing.')
    if case.template.project_id != configuration.project.project_id:
        return outcome(TestStatus.BLOCKED, 'Database template project does not match configuration.')
    if should_cancel is not None and should_cancel():
        return outcome(TestStatus.CANCELLED, 'Database validation was cancelled.')
    connection = None
    denied = False
    interrupted = False
    cancelled = False
    deadline = monotonic() + configuration.timeout_seconds

    def progress():
        nonlocal interrupted, cancelled
        cancelled = should_cancel is not None and should_cancel()
        interrupted = cancelled or monotonic() >= deadline
        return int(interrupted)

    def authorize(action, first, second, database, source):
        nonlocal denied
        allowed = action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE)
        if action == sqlite3.SQLITE_READ:
            allowed = database == 'main'
        if action == sqlite3.SQLITE_FUNCTION:
            allowed = second in ('count', 'sum', 'avg', 'min', 'max', 'length',
                                 'lower', 'upper', 'coalesce', 'abs', 'round')
        if not allowed:
            denied = True
        return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY

    try:
        path = _fixture_path(configuration, fixture_root)
        # URI encoding prevents a private filename from injecting SQLite flags.
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True,
                                     timeout=min(0.1, configuration.timeout_seconds))
        connection.enable_load_extension(False)
        connection.execute('PRAGMA query_only = ON')
        connection.execute('PRAGMA trusted_schema = OFF')
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, configuration.max_result_bytes)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 16384)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 100)
        connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        connection.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 100)
        connection.set_authorizer(authorize)
        connection.set_progress_handler(progress, 100)
        cursor = connection.execute(case.template.sql, dict(case.parameters))
        rows = []
        size = 0
        for row in cursor:
            if progress():
                raise sqlite3.OperationalError()
            if len(rows) >= configuration.max_rows:
                return outcome(TestStatus.ERROR, 'Database result row limit exceeded.')
            if any(type(value) not in (int, float, str, type(None)) for value in row):
                return outcome(TestStatus.ERROR, 'Database result contains an unsupported value type.')
            encoded = json.dumps(row, ensure_ascii=True, allow_nan=False).encode('utf-8')
            size += len(encoded)
            if size > configuration.max_result_bytes:
                return outcome(TestStatus.ERROR, 'Database result byte limit exceeded.')
            rows.append(row)
        if progress():
            raise sqlite3.OperationalError()
        failures = []
        for index, check in enumerate(case.checks):
            if check.operator == DatabaseOperator.ROW_COUNT:
                passed = len(rows) == check.expected
            else:
                passed = (check.row < len(rows) and check.column < len(rows[check.row])
                          and _equal(rows[check.row][check.column], check.expected))
            if not passed:
                failures.append(index)
        if failures:
            return outcome(TestStatus.FAILED, 'Database assertion indexes failed: '
                           + ', '.join(map(str, failures)) + '.')
        return outcome(TestStatus.PASSED, 'Database results satisfied all explicit checks.')
    except DatabasePolicyError:
        return outcome(TestStatus.BLOCKED, 'Database reference or local fixture policy blocked execution.')
    except (sqlite3.Error, OSError, ValueError, UnicodeError):
        if cancelled:
            return outcome(TestStatus.CANCELLED, 'Database validation was cancelled.')
        if denied:
            return outcome(TestStatus.BLOCKED, 'SQLite authorization rejected the operation.')
        if interrupted:
            return outcome(TestStatus.ERROR, 'Database query exceeded its time limit.')
        return outcome(TestStatus.ERROR, 'Database connection or bounded query processing failed.')
    finally:
        if connection is not None:
            connection.close()
