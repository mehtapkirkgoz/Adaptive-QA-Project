"""Explicit loopback runtime selection with immutable releases and process leases."""

from contextlib import ExitStack, contextmanager, closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
from uuid import uuid4
import zipfile

from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.schema_migrations import validate_runtime_schema, AUTH_COLUMNS, PROJECT_COLUMNS, ADDITIONS
from adaptive_qa.worker_lock import worker_lock


ROLES = ('serve', 'discovery-once', 'run-once', 'maintenance-once')


@contextmanager
def _lock(root, name):
    key = root / name
    lock_path = key.with_suffix(key.suffix + '.worker.lock')
    if (key.resolve() != key or lock_path.resolve() != lock_path
            or (lock_path.exists() and lock_path.stat().st_nlink != 1)):
        raise ValueError('Runtime process lock must not be redirected or shared.')
    with worker_lock(key):
        yield


def _root(plan):
    if not isinstance(plan, DeploymentPlan) or plan.environment != Environment.LOCAL:
        raise ValueError('Runtime activation supports the explicit local loopback profile only.')
    root = plan.directory / 'runtime'
    if root.resolve() != root:
        raise ValueError('Runtime storage must not be redirected.')
    root.mkdir(mode=0o700, exist_ok=True)
    return root


def _read(path):
    if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError('Runtime metadata must be a regular, unredirected file.')
    with path.open('rb') as stream:
        raw = stream.read(262145)
    if len(raw) > 262144:
        raise ValueError('Runtime metadata is oversized.')
    try:
        result = json.loads(raw)
    except (ValueError, RecursionError):
        raise ValueError('Runtime metadata is invalid.') from None
    if not isinstance(result, dict):
        raise ValueError('Runtime metadata must be an object.')
    return result


def _hash(path):
    if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError('Runtime payload was redirected.')
    digest, total, deadline = hashlib.sha256(), 0, monotonic() + 10
    with path.open('rb') as stream:
        while chunk := stream.read(1048576):
            total += len(chunk)
            if total > 64 * 1024 * 1024 or monotonic() >= deadline:
                raise ValueError('Runtime payload verification budget exceeded.')
            digest.update(chunk)
    return digest.hexdigest()


def _extract(archive, target, *, wheel=False):
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if len(entries) > 1000 or sum(item.file_size for item in entries) > 64 * 1024 * 1024:
            raise ValueError('Runtime archive exceeds its extraction limit.')
        names = set()
        for item in entries:
            path = target / item.filename
            first = item.filename.split('/')[0]
            if (item.filename in names or '\\' in item.filename or not path.resolve().is_relative_to(target)
                    or (item.external_attr >> 16) & 0o170000 == 0o120000
                    or (wheel and not (first == 'adaptive_qa' or re.fullmatch(r'adaptive_qa-[^/]+\.dist-info', first)))
                    or path.suffix in ('.pth', '.pyc')):
                raise ValueError('Runtime archive contains unsupported or redirected entries.')
            names.add(item.filename)
        bundle.extractall(target)


def _snapshot(source, destination, entry):
    digest, total, deadline = hashlib.sha256(), 0, monotonic() + 10
    with source.open('rb') as original, destination.open('xb') as output:
        while chunk := original.read(1048576):
            total += len(chunk)
            if total > 64 * 1024 * 1024 or monotonic() >= deadline:
                raise ValueError('Runtime preparation copy exceeded its budget.')
            digest.update(chunk)
            output.write(chunk)
    if total != entry.get('bytes') or digest.hexdigest() != entry.get('sha256'):
        raise ValueError('Candidate changed during runtime preparation.')


def _release(root, release_id):
    if not isinstance(release_id, str) or not re.fullmatch('[0-9a-f]{40}', release_id):
        raise ValueError('An exact prepared release commit is required.')
    release = root / 'releases' / release_id
    if release.resolve() != release:
        raise ValueError('Prepared release path was redirected.')
    metadata = _read(release / 'installed.json')
    files = metadata.get('files')
    if metadata.get('release_id') != release_id or not isinstance(files, dict) or not 1 <= len(files) <= 1000:
        raise ValueError('Prepared release inventory is invalid.')
    deadline = monotonic() + 15
    for name, digest in files.items():
        if not isinstance(name, str) or not isinstance(digest, str) or monotonic() >= deadline:
            raise ValueError('Prepared release inventory is invalid or exceeded its time budget.')
        path = release / name
        if (not isinstance(name, str) or not path.resolve().is_relative_to(release)
                or name == 'installed.json' or _hash(path) != digest):
            raise ValueError('Prepared release payload verification failed.')
    actual = set()
    for index, path in enumerate(release.rglob('*')):
        if index > 2000 or monotonic() >= deadline:
            raise ValueError('Prepared release tree exceeds its verification budget.')
        if path.is_symlink() or not path.resolve().is_relative_to(release):
            raise ValueError('Prepared release tree was redirected.')
        if path.is_file():
            actual.add(path.relative_to(release).as_posix())
        if len(actual) > 1001:
            raise ValueError('Prepared release tree exceeds its file limit.')
    if actual != set(files) | {'installed.json'}:
        raise ValueError('Prepared release inventory does not match its files.')
    return release


def _selection(root):
    selected = _read(root / 'current.json')
    if (type(selected.get('schema_version')) is not int or selected.get('schema_version') != 1
            or selected.get('environment') != 'local'
            or not isinstance(selected.get('selection_id'), str)
            or re.fullmatch('[0-9a-f]{32}', selected['selection_id']) is None):
        raise ValueError('Runtime selection metadata is invalid.')
    return selected


def _data(plan, recovery_id=None):
    directory = plan.directory
    if recovery_id is not None:
        if not isinstance(recovery_id, str) or not re.fullmatch('[0-9a-f]{32}', recovery_id):
            raise ValueError('An exact recovery ID is required.')
        directory = directory / 'recovery' / recovery_id
        record = _read(directory / 'recovery.json')
        if (record.get('environment') != 'local' or record.get('sessions_invalidated') is not True
                or record.get('pending_work_cancelled') is not True):
            raise ValueError('Recovery safety metadata does not match the local environment.')
    if directory.resolve() != directory:
        raise ValueError('Runtime data was redirected.')
    for name in ('auth.sqlite', 'projects.sqlite'):
        path = directory / name
        if (path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1
                or not 0 < path.stat().st_size <= 256 * 1024 * 1024):
            raise ValueError('Runtime requires an existing private database pair.')
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as connection:
            deadline = monotonic() + 2
            connection.execute('PRAGMA query_only=ON')
            connection.execute('PRAGMA trusted_schema=OFF')
            connection.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
            validate_runtime_schema(connection, name)
            required = AUTH_COLUMNS if name == 'auth.sqlite' else PROJECT_COLUMNS
            for table, columns in required.items():
                definition = connection.execute('SELECT type FROM sqlite_master WHERE name=?', (table,)).fetchone()
                actual = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
                if (definition is None or definition[0] != 'table'
                        or not columns | {column for column, _ in ADDITIONS.get(table, ())} <= actual):
                    raise ValueError('Runtime database schema is incomplete.')
            if (connection.execute('PRAGMA quick_check(1)').fetchone() != ('ok',)
                    or connection.execute('PRAGMA foreign_key_check').fetchone() is not None
                    or monotonic() >= deadline):
                raise ValueError('Runtime data integrity verification failed.')
    return directory


@contextmanager
def maintenance(plan):
    root = _root(plan)
    with ExitStack() as stack:
        stack.enter_context(_lock(root, 'admission'))
        for role in ROLES:
            stack.enter_context(_lock(root, role))
        yield root


def prepare_local(plan, candidate, candidate_commit, *, maintenance_confirmed=False, trusted_release=False):
    if maintenance_confirmed is not True or trusted_release is not True:
        raise ValueError('Offline maintenance and explicit trusted-release review are required.')
    from adaptive_qa.rollback_plan import plan_rollback
    with maintenance(plan) as root:
        check = plan_rollback(plan, candidate, candidate_commit, maintenance_confirmed=True)
        if not check['schema_compatible']:
            raise ValueError('Candidate schema support is incompatible or unknown.')
        releases = root / 'releases'
        if releases.resolve() != releases:
            raise ValueError('Release storage was redirected.')
        releases.mkdir(mode=0o700, exist_ok=True)
        destination = releases / candidate_commit
        if destination.exists():
            raise ValueError('Prepared releases are immutable and cannot be overwritten.')
        candidate = Path(candidate)
        manifest = _read(candidate / 'release.json')
        if manifest.get('source_commit') != candidate_commit:
            raise ValueError('Candidate identity changed during preparation.')
        payloads = {entry['name']: entry for entry in manifest['files']}
        with TemporaryDirectory(prefix='.pending-', dir=releases) as temporary:
            pending = Path(temporary).resolve()
            site, ui = pending / 'site', pending / 'ui'
            site.mkdir()
            ui.mkdir()
            wheels = list(candidate.glob('adaptive_qa-*.whl'))
            if len(wheels) != 1 or not wheels[0].name.endswith('-py3-none-any.whl'):
                raise ValueError('Exactly one pure Python application wheel is required.')
            wheel_copy, ui_copy = pending / 'wheel.snapshot', pending / 'ui.snapshot'
            _snapshot(wheels[0], wheel_copy, payloads[wheels[0].name])
            _snapshot(candidate / 'dashboard.zip', ui_copy, payloads['dashboard.zip'])
            _extract(wheel_copy, site, wheel=True)
            _extract(ui_copy, ui)
            wheel_copy.unlink()
            ui_copy.unlink()
            if not (site / 'adaptive_qa' / '__init__.py').is_file() or not (ui / 'index.html').is_file():
                raise ValueError('Prepared release lacks its application or UI entry point.')
            (pending / 'release.json').write_text(json.dumps(manifest), encoding='utf-8')
            files = {path.relative_to(pending).as_posix(): _hash(path)
                     for path in pending.rglob('*') if path.is_file()}
            (pending / 'installed.json').write_text(json.dumps({'release_id': candidate_commit, 'files': files}), encoding='utf-8')
            if not pending.is_relative_to(releases) or destination.resolve() != destination:
                raise ValueError('Runtime publication path is unsafe.')
            pending.rename(destination)
    return {'release_id': candidate_commit, 'prepared': True, 'service_started': False}


def _check_form_mapping_support(release, data):
    """Older selected binaries must not silently ignore saved execution mappings."""
    if (release / 'site/adaptive_qa/form_configuration.py').is_file():
        return
    with closing(sqlite3.connect((data/'projects.sqlite').as_uri()+'?mode=ro', uri=True, timeout=1)) as connection:
        steps = [0]
        def budget():
            steps[0] += 1
            return int(steps[0] > 200)
        connection.set_progress_handler(budget, 1000)
        for table, column in (('dashboard_project_settings', 'settings_json'),
                              ('dashboard_organization_projects', 'settings_json'),
                              ('dashboard_test_runs', 'configuration_json'),
                              ('dashboard_organization_runs', 'configuration_json')):
            if not connection.execute('SELECT 1 FROM sqlite_master WHERE type=\'table\' AND name=?', (table,)).fetchone():
                continue
            rows = connection.execute(f'SELECT CASE WHEN length({column})>65536 THEN NULL ELSE {column} END '
                                      f'FROM {table} WHERE {column} IS NOT NULL LIMIT 1001').fetchall()
            if len(rows) > 1000:
                raise ValueError('Mapping compatibility cannot be established within the inspection budget.')
            for (raw,) in rows:
                value = json.loads(raw) if raw is not None else None
                if not isinstance(value, dict) or value.get('form_mappings'):
                    raise ValueError('The selected release cannot interpret saved form mappings.')


def select_local(plan, release_id, *, recovery_id=None, use_live_data=False, expected_selection=None, maintenance_confirmed=False):
    if maintenance_confirmed is not True:
        raise ValueError('Explicit offline-maintenance confirmation is required.')
    with maintenance(plan) as root:
        pointer = root / 'current.json'
        previous = _selection(root) if pointer.exists() else None
        if (previous and previous.get('selection_id') != expected_selection) or (not previous and expected_selection is not None):
            raise ValueError('Runtime selection changed; review the current selection before switching.')
        if type(use_live_data) is not bool or (use_live_data and recovery_id is not None):
            raise ValueError('Select either explicit live data or one recovery ID.')
        if recovery_id is None and previous and not use_live_data:
            recovery_id = previous.get('recovery_id')
        release = _release(root, release_id)
        data = _data(plan, recovery_id)
        _check_form_mapping_support(release, data)
        supported = _read(release / 'release.json').get('database_schema_revisions', [])
        for name in ('auth.sqlite', 'projects.sqlite'):
            with closing(sqlite3.connect((data / name).as_uri() + '?mode=ro', uri=True, timeout=1)) as connection:
                if connection.execute('PRAGMA user_version').fetchone()[0] not in supported:
                    raise ValueError('Selected data is incompatible with the prepared release.')
        selection = {'schema_version': 1, 'selection_id': uuid4().hex, 'release_id': release_id,
                     'recovery_id': recovery_id, 'environment': 'local'}
        temporary = root / ('.selection-' + uuid4().hex + '.json')
        try:
            temporary.write_text(json.dumps(selection), encoding='utf-8')
            os.replace(temporary, pointer)
        finally:
            temporary.unlink(missing_ok=True)
    return {**selection, 'service_started': False}


@contextmanager
def component_lease(plan, role, expected_selection):
    if role not in ROLES:
        raise ValueError('Unknown local runtime component.')
    root = _root(plan)
    with ExitStack() as stack:
        with _lock(root, 'admission'):
            stack.enter_context(_lock(root, role))
            selected = _selection(root)
            if selected.get('selection_id') != expected_selection:
                raise ValueError('Selected release changed before component startup.')
            release = _release(root, selected.get('release_id'))
            data = _data(plan, selected.get('recovery_id'))
            _check_form_mapping_support(release, data)
        yield selected, release, data


def local_status(plan):
    root = _root(plan)
    with _lock(root, 'admission'):
        selected = _selection(root) if (root / 'current.json').exists() else None
        components = {}
        for role in ROLES:
            try:
                with _lock(root, role):
                    components[role] = 'inactive'
            except ValueError:
                components[role] = 'active'
    return {'environment': 'local', 'selection': selected, 'components': components, 'public_backend': False}


def run_local(plan, role, *, duration_seconds=None):
    if duration_seconds is None:
        duration_seconds = 900 if role == 'serve' else (30 if role == 'maintenance-once' else 180)
    maximum = 3600 if role == 'serve' else (60 if role == 'maintenance-once' else 180)
    if role not in ROLES or type(duration_seconds) is not int or not 1 <= duration_seconds <= maximum:
        raise ValueError('Use a known component and a bounded local duration.')
    root = _root(plan)
    selected = _selection(root)
    release = _release(root, selected.get('release_id'))
    environment = dict(os.environ)
    for key in ('PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT', 'PYTHONPATH'):
        environment.pop(key, None)
    environment.update(PYTHONPATH=str(release / 'site'), PYTHONDONTWRITEBYTECODE='1')
    entry = Path(__file__).with_name('runtime_entry.py').resolve()
    command = [sys.executable, '-P', str(entry), '--data-root', str(plan.data_root),
               '--origin', plan.public_origin, '--role', role, '--selection', selected['selection_id']]
    options = {'start_new_session': True} if os.name != 'nt' else {
        'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    from adaptive_qa.browser_process import _terminate_process_tree
    process = subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, **options)
    print(json.dumps({'event': 'component_starting', 'role': role, 'release_id': selected['release_id']}), flush=True)
    timed_out = False
    try:
        try:
            process.wait(timeout=duration_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        except KeyboardInterrupt:
            pass
    finally:
        if process.poll() is None:
            _terminate_process_tree(process)
    return {'release_id': selected['release_id'], 'role': role, 'timed_out': timed_out,
            'status': 'completed' if process.returncode == 0 else 'stopped', 'public_backend': False}
