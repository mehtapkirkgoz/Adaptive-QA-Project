"""Edition-aware offline snapshots and recovery into a fresh local directory."""
from contextlib import ExitStack, closing
import hashlib
import json
from itertools import islice
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory
from time import monotonic

from adaptive_qa.schema_migrations import migrate_recovery_connection

NAMES = {'projects.sqlite', 'auth.sqlite', 'license.sqlite'}
LIMIT = 256 * 1024 * 1024


def _path(path):
    path = Path(path)
    if not path.is_absolute() or str(path).startswith(('\\\\', '//')) or path.resolve() != path or path.parent == path:
        raise ValueError('Use an absolute unredirected local directory below the filesystem root.')
    return path


def _regular(path):
    if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1 or not 0 < path.stat().st_size <= LIMIT:
        raise ValueError('Snapshot databases must be bounded regular unredirected files.')


def _digest(path):
    deadline, result, size = monotonic()+10, hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(1048576):
            size += len(chunk)
            if size > LIMIT or monotonic() >= deadline:
                raise ValueError('Snapshot size or time budget exceeded.')
            result.update(chunk)
    return size, result.hexdigest()


def _integrity(path):
    deadline = monotonic()+10
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)) as connection:
        connection.execute('PRAGMA trusted_schema=OFF')
        connection.set_progress_handler(lambda:int(monotonic() >= deadline),1000)
        if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('Snapshot database integrity failed.')


def create_local_backup(workspace, destination, *, maintenance_confirmed=False):
    if maintenance_confirmed is not True:
        raise ValueError('Stop local servers/workers and explicitly confirm offline maintenance.')
    workspace, destination = _path(workspace), _path(destination)
    if not workspace.is_dir() or destination.exists() or destination.is_relative_to(workspace):
        raise ValueError('Use an existing workspace and a fresh backup outside it.')
    names = {name for name in NAMES if (workspace/name).exists() or (workspace/name).is_symlink()}
    if 'projects.sqlite' not in names:
        raise ValueError('The local project database is required.')
    for name in names: _regular(workspace/name)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='.local-backup-',dir=destination.parent) as temporary, ExitStack() as stack:
        pending = Path(temporary).resolve(); pending.chmod(0o700)
        connections = []
        for name in sorted(names):
            connection = stack.enter_context(closing(sqlite3.connect((workspace/name).as_uri()+'?mode=ro',uri=True,timeout=1)))
            connection.execute('PRAGMA query_only=ON')
            connections.append((name,connection,connection.execute('PRAGMA data_version').fetchone()[0]))
        files = []
        for name,connection,_ in connections:
            deadline = monotonic()+10
            page_size = connection.execute('PRAGMA page_size').fetchone()[0]
            def progress(status,remaining,total):
                if monotonic() >= deadline or total*page_size > LIMIT:
                    raise ValueError('Snapshot size or time budget exceeded.')
            with closing(sqlite3.connect(pending/name)) as output:
                connection.backup(output,pages=128,progress=progress,sleep=.01)
            _regular(pending/name); _integrity(pending/name)
            size,digest = _digest(pending/name)
            files.append(dict(name=name,bytes=size,sha256=digest))
        if any(connection.execute('PRAGMA data_version').fetchone()[0] != version for _,connection,version in connections):
            raise ValueError('Workspace changed during backup; stop services and retry.')
        if names != {name for name in NAMES if (workspace/name).exists() or (workspace/name).is_symlink()}:
            raise ValueError('Workspace file set changed during backup.')
        (pending/'manifest.json').write_text(json.dumps(dict(format='adaptive-local-workspace-1',files=files))+'\n',encoding='utf-8')
        pending.rename(destination)
    return {'databases':len(files),'activation_enabled':False}


def _verified(bundle):
    bundle = _path(bundle)
    if not bundle.is_dir(): raise ValueError('Snapshot directory is unavailable.')
    manifest = bundle/'manifest.json'
    if manifest.resolve() != manifest or not manifest.is_file() or manifest.stat().st_nlink != 1:
        raise ValueError('Snapshot manifest is unavailable or redirected.')
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result: raise ValueError('Duplicate snapshot manifest keys.')
            result[key] = value
        return result
    with manifest.open('rb') as stream: raw = stream.read(16385)
    if len(raw)>16384: raise ValueError('Snapshot manifest exceeds its limit.')
    try: data = json.loads(raw,object_pairs_hook=unique)
    except (UnicodeError,RecursionError): raise ValueError('Invalid snapshot manifest.') from None
    if not isinstance(data,dict) or set(data) != {'format','files'} or data['format'] != 'adaptive-local-workspace-1':
        raise ValueError('Unsupported snapshot format.')
    files = data['files']
    if not isinstance(files,list) or not 1<=len(files)<=3: raise ValueError('Invalid snapshot file set.')
    seen = set()
    for entry in files:
        if (not isinstance(entry,dict) or set(entry) != {'name','bytes','sha256'}
                or not isinstance(entry['name'],str) or entry['name'] not in NAMES or entry['name'] in seen
                or type(entry['bytes']) is not int or not 0<entry['bytes']<=LIMIT
                or not isinstance(entry['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',entry['sha256'])):
            raise ValueError('Invalid snapshot metadata.')
        seen.add(entry['name'])
        path = bundle/entry['name']; _regular(path)
        if _digest(path) != (entry['bytes'],entry['sha256']): raise ValueError('Snapshot checksum mismatch.')
        _integrity(path)
    if 'projects.sqlite' not in seen or {p.name for p in islice(bundle.iterdir(),5)} != seen|{'manifest.json'}:
        raise ValueError('Snapshot contains missing or unexpected files.')
    return files


def restore_local_backup(bundle,destination,*,maintenance_confirmed=False):
    if maintenance_confirmed is not True:
        raise ValueError('Explicit offline maintenance confirmation is required.')
    bundle,destination = _path(bundle),_path(destination)
    files = _verified(bundle)
    if destination.exists() or destination.is_relative_to(bundle): raise ValueError('Restore requires a fresh directory outside the snapshot.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='.local-recovery-',dir=destination.parent) as temporary:
        pending = Path(temporary).resolve(); pending.chmod(0o700)
        for entry in files:
            source,target = bundle/entry['name'],pending/entry['name']
            _regular(source)
            deadline,size,digest = monotonic()+10,0,hashlib.sha256()
            with source.open('rb') as original,target.open('xb') as output:
                while chunk := original.read(1048576):
                    size += len(chunk)
                    if size>entry['bytes'] or monotonic()>=deadline: raise ValueError('Recovery copy budget exceeded.')
                    digest.update(chunk); output.write(chunk)
            if (size,digest.hexdigest()) != (entry['bytes'],entry['sha256']): raise ValueError('Snapshot changed during recovery.')
            with closing(sqlite3.connect(target)) as connection:
                connection.execute('PRAGMA trusted_schema=OFF')
                connection.set_progress_handler(lambda:int(monotonic()>=deadline),1000)
                if connection.execute("SELECT 1 FROM sqlite_master WHERE type IN ('view','trigger')").fetchone():
                    raise ValueError('Unsupported recovery database objects.')
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if entry['name'] == 'license.sqlite':
                    if tables != {'local_license'}: raise ValueError('Unsupported local license schema.')
                    rows = connection.execute('SELECT slot,length(document),typeof(document) FROM local_license LIMIT 2').fetchall()
                    if any(slot!=1 or not 1<=length<=8192 or kind!='blob' for slot,length,kind in rows) or len(rows)>1:
                        raise ValueError('Invalid stored license record.')
                else:
                    migrate_recovery_connection(connection,entry['name'])
                    if entry['name']=='auth.sqlite': connection.execute('DELETE FROM dashboard_sessions')
                    else:
                        for table in ('dashboard_discovery_jobs','dashboard_test_runs','dashboard_interactive_jobs','dashboard_api_jobs','dashboard_organization_discovery','dashboard_organization_runs'):
                            if table in tables:
                                connection.execute(f"UPDATE {table} SET status='cancelled',claim_token=NULL WHERE status IN ('queued','running','cancel_requested')")
                        if 'dashboard_organization_admissions' in tables:
                            connection.execute("UPDATE dashboard_organization_admissions SET status='cancelled',claim_token=NULL WHERE status IN ('pending','active')")
                        if 'dashboard_agents' in tables: connection.execute('UPDATE dashboard_agents SET revoked=1')
                        if 'dashboard_agent_leases' in tables: connection.execute("UPDATE dashboard_agent_leases SET status='cancelled' WHERE status='active'")
                connection.commit()
                if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
                    raise ValueError('Recovered database references are invalid.')
            _integrity(target)
        pending.rename(destination)
    return {'databases':len(files),'sessions_invalidated':True,'pending_work_cancelled':True,'activation_enabled':False}
