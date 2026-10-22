"""Bounded SQLite backup bundles for explicitly isolated operator environments."""

from contextlib import ExitStack, closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from time import monotonic
from uuid import uuid4

from adaptive_qa.deployment import DeploymentPlan


def create_backup(plan, *, maintenance_confirmed=False):
    if not isinstance(plan, DeploymentPlan) or maintenance_confirmed is not True:
        raise ValueError('A validated plan and explicit offline-maintenance confirmation are required.')
    directory = plan.directory
    if directory.resolve() != directory:
        raise ValueError('Environment storage was redirected.')
    sources = [directory / name for name in ('auth.sqlite', 'projects.sqlite')]
    for path in sources:
        if (path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1):
            raise ValueError('Both regular, unredirected environment databases must exist.')
    base = directory / 'backups'
    if base.resolve() != base:
        raise ValueError('Backup storage was redirected.')
    base.mkdir(mode=0o700, exist_ok=True)
    base.chmod(0o700)
    bundle_id = uuid4().hex
    target = base / bundle_id
    with ExitStack() as stack, TemporaryDirectory(prefix='.pending-', dir=base) as temporary:
        pending = Path(temporary).resolve()
        if not pending.is_relative_to(base.resolve()) or target.resolve() != target or target.exists():
            raise ValueError('Backup publication path is unsafe.')
        connections = []
        for path in sources:
            connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)
            stack.callback(connection.close)
            connection.execute('PRAGMA query_only=ON')
            connections.append(connection)
        versions = [connection.execute('PRAGMA data_version').fetchone()[0] for connection in connections]
        files = []
        for source, connection in zip(sources, connections, strict=True):
            destination = pending / source.name
            deadline = monotonic() + 10
            page_size = connection.execute('PRAGMA page_size').fetchone()[0]
            def progress(status, remaining, total):
                if monotonic() >= deadline:
                    raise ValueError('Backup deadline exceeded.')
                if total * page_size > 256 * 1024 * 1024:
                    raise ValueError('Backup database exceeds the local 256 MiB limit.')
            with closing(sqlite3.connect(destination)) as output:
                connection.backup(output, pages=128, progress=progress, sleep=.01)
                output.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
                if output.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                    raise ValueError('Backup integrity verification failed.')
            if destination.stat().st_size > 256 * 1024 * 1024:
                raise ValueError('Backup database exceeds the local 256 MiB limit.')
            digest = hashlib.sha256()
            with destination.open('rb') as stream:
                while chunk := stream.read(1048576):
                    if monotonic() >= deadline:
                        raise ValueError('Backup deadline exceeded.')
                    digest.update(chunk)
            files.append({'name': source.name, 'bytes': destination.stat().st_size,
                          'sha256': digest.hexdigest()})
        if versions != [connection.execute('PRAGMA data_version').fetchone()[0] for connection in connections]:
            raise ValueError('Database writes occurred during backup; stop services and retry.')
        manifest = {'schema_version': 1, 'bundle_id': bundle_id, 'environment': plan.environment.value,
            'created_at': datetime.now(timezone.utc).isoformat(), 'files': files,
            'maintenance_confirmation': True}
        (pending / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        # Both absolute paths were checked within the environment backup root above.
        pending.rename(target)
    return {'bundle_id': bundle_id, 'environment': plan.environment.value, 'databases': 2}
