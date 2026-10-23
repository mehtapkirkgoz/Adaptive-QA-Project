"""Offline recovery into a fresh private directory, never over live databases."""

from contextlib import closing
import hashlib
import json
import sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path
from time import monotonic
from uuid import uuid4

from adaptive_qa.backup_verification import _verified_manifest
from adaptive_qa.schema_migrations import migrate_recovery_connection


def prepare_restore(plan, bundle_id, *, maintenance_confirmed=False):
    if maintenance_confirmed is not True:
        raise ValueError('Explicit offline-maintenance confirmation is required.')
    manifest = _verified_manifest(plan, bundle_id)
    source = plan.directory / 'backups' / bundle_id
    base = plan.directory / 'recovery'
    if base.resolve() != base:
        raise ValueError('Recovery storage was redirected.')
    base.mkdir(mode=0o700, exist_ok=True)
    base.chmod(0o700)
    recovery_id = uuid4().hex
    target = base / recovery_id
    migrations = {}
    with TemporaryDirectory(prefix='.pending-', dir=base) as temporary:
        pending = Path(temporary).resolve()
        if not pending.is_relative_to(base) or target.resolve() != target or target.exists():
            raise ValueError('Recovery publication path is unsafe.')
        for entry in manifest['files']:
            deadline = monotonic() + 10
            destination = pending / entry['name']
            digest, copied = hashlib.sha256(), 0
            with (source / entry['name']).open('rb') as original, destination.open('xb') as output:
                while chunk := original.read(1048576):
                    copied += len(chunk)
                    if copied > entry['bytes'] or monotonic() >= deadline:
                        raise ValueError('Recovery copy exceeded its size or time budget.')
                    digest.update(chunk)
                    output.write(chunk)
            if copied != entry['bytes'] or digest.hexdigest() != entry['sha256']:
                raise ValueError('Backup changed during recovery copying.')
            with closing(sqlite3.connect(destination)) as connection:
                connection.execute('PRAGMA trusted_schema=OFF')
                connection.execute('PRAGMA secure_delete=ON')
                connection.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
                if connection.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger', 'view') LIMIT 1").fetchone():
                    raise ValueError('Recovery requires the supported dashboard table schema.')
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                migrations[entry['name']] = migrate_recovery_connection(connection, entry['name'])
                if entry['name'] == 'auth.sqlite':
                    if not {'dashboard_users', 'dashboard_sessions', 'dashboard_login_admission'} <= tables:
                        raise ValueError('Recovery requires the supported authentication schema.')
                    connection.execute('DELETE FROM dashboard_sessions')
                else:
                    if not {'dashboard_projects', 'dashboard_project_settings', 'dashboard_discovery_jobs',
                            'dashboard_test_runs', 'dashboard_run_evidence'} <= tables:
                        raise ValueError('Recovery requires the supported project and queue schema.')
                    for table in ('dashboard_discovery_jobs', 'dashboard_test_runs'):
                        connection.execute(f"UPDATE {table} SET status='cancelled', claim_token=NULL "
                                           "WHERE status IN ('queued', 'running', 'cancel_requested')")
                    if 'dashboard_organization_discovery' in tables:
                        connection.execute("UPDATE dashboard_organization_discovery SET status='cancelled', claim_token=NULL "
                                           "WHERE status IN ('queued', 'running', 'cancel_requested')")
                    if 'dashboard_organization_runs' in tables:
                        connection.execute("UPDATE dashboard_organization_runs SET status='cancelled', claim_token=NULL "
                                           "WHERE status IN ('queued', 'running', 'cancel_requested')")
                    if 'dashboard_organization_admissions' in tables:
                        connection.execute("UPDATE dashboard_organization_admissions SET status='cancelled', claim_token=NULL "
                                           "WHERE status IN ('pending', 'active')")
                    if 'dashboard_agents' in tables:
                        # Restoring an older sequence counter must never revive credentials.
                        connection.execute('UPDATE dashboard_agents SET revoked=1')
                connection.commit()
                if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                    raise ValueError('Recovered database integrity check failed.')
                if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
                    raise ValueError('Recovered database references are invalid.')
            if monotonic() >= deadline:
                raise ValueError('Recovery verification deadline exceeded.')
        (pending / 'recovery.json').write_text(json.dumps({
            'schema_version': 1, 'source_bundle_id': bundle_id, 'environment': plan.environment.value,
            'sessions_invalidated': True, 'pending_work_cancelled': True, 'activation_enabled': False,
            'migrations': migrations,
        }, indent=2) + '\n', encoding='utf-8')
        # Both absolute publication paths are confined to the checked recovery root.
        pending.rename(target)
    return {'recovery_id': recovery_id, 'environment': plan.environment.value,
            'databases': 2, 'sessions_invalidated': True, 'pending_work_cancelled': True,
            'activation_enabled': False}
