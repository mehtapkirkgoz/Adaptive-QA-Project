"""Bounded operator-only storage checks without provisioning or record output."""

from contextlib import closing
import sqlite3
from time import monotonic

from adaptive_qa.deployment import DeploymentPlan
from adaptive_qa.schema_migrations import AUTH_COLUMNS, PROJECT_COLUMNS, ADDITIONS, validate_runtime_schema


def storage_health(plan):
    if not isinstance(plan, DeploymentPlan):
        raise ValueError('A validated environment plan is required.')
    checks = {}
    for name in ('auth.sqlite', 'projects.sqlite'):
        path = plan.directory / name
        try:
            if (path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1
                    or not 0 < path.stat().st_size <= 256 * 1024 * 1024):
                raise ValueError()
            deadline = monotonic() + 2
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as connection:
                connection.execute('PRAGMA query_only=ON')
                connection.execute('PRAGMA trusted_schema=OFF')
                connection.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
                validate_runtime_schema(connection, name)
                required = AUTH_COLUMNS if name == 'auth.sqlite' else PROJECT_COLUMNS
                for table, columns in required.items():
                    definition = connection.execute('SELECT type FROM sqlite_master WHERE name=?', (table,)).fetchone()
                    actual = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
                    expected = columns | {column for column, _ in ADDITIONS.get(table, ())}
                    if definition is None or definition[0] != 'table' or not expected <= actual:
                        raise ValueError()
                if connection.execute('PRAGMA quick_check(1)').fetchone() != ('ok',):
                    raise ValueError()
                if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
                    raise ValueError()
                revision = connection.execute('PRAGMA user_version').fetchone()[0]
            if monotonic() >= deadline:
                raise ValueError()
            checks[name] = {'status': 'ready', 'schema_revision': revision}
        except (OSError, RuntimeError, ValueError, sqlite3.Error):
            checks[name] = {'status': 'unavailable', 'reason': 'Storage is missing, unreadable or incompatible.'}
    return {'environment': plan.environment.value, 'scope': 'database_storage_only',
            'status': 'ready' if all(item['status'] == 'ready' for item in checks.values()) else 'unavailable',
            'databases': checks, 'activation_enabled': False}
