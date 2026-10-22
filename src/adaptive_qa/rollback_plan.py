"""Read-only release/schema comparison; never activates a rollback candidate."""

from contextlib import closing
import hashlib
import json
from itertools import islice
import os
from pathlib import Path
import re
import sqlite3
from time import monotonic

from adaptive_qa.deployment import DeploymentPlan


def plan_rollback(plan, candidate, candidate_commit, *, maintenance_confirmed=False):
    if (not isinstance(plan, DeploymentPlan) or maintenance_confirmed is not True
            or not isinstance(candidate_commit, str) or not re.fullmatch('[0-9a-f]{40}', candidate_commit)):
        raise ValueError('A validated environment, exact candidate commit and offline confirmation are required.')
    candidate = Path(candidate)
    if not candidate.is_absolute() or candidate.resolve() != candidate or not candidate.is_dir():
        raise ValueError('Candidate must be an absolute, unredirected release directory.')
    manifest_path = candidate / 'release.json'
    if (manifest_path.resolve() != manifest_path or not manifest_path.is_file()
            or manifest_path.stat().st_nlink != 1 or manifest_path.stat().st_size > 65536):
        raise ValueError('Release manifest is missing, redirected or oversized.')
    with manifest_path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('Release manifest exceeds its size limit.')
    try:
        manifest = json.loads(raw)
    except (ValueError, RecursionError):
        raise ValueError('Release manifest is invalid.') from None
    if (not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int
            or manifest.get('schema_version') != 1
            or manifest.get('source_commit') != candidate_commit or manifest.get('activation_enabled') is not False):
        raise ValueError('Release identity or inactive manifest does not match the candidate.')
    files = manifest.get('files')
    if not isinstance(files, list) or len(files) != 4:
        raise ValueError('Candidate must contain the fixed four release payloads.')
    names = set()
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get('name'), str):
            raise ValueError('Invalid candidate file metadata.')
        name = entry['name']
        if name in names or not (name in ('dashboard.zip', 'requirements.lock.txt', 'frontend-package-lock.json')
                                 or re.fullmatch(r'adaptive_qa-[A-Za-z0-9_.+-]+\.whl', name)):
            raise ValueError('Unexpected candidate payload name.')
        names.add(name)
        path = candidate / name
        if (path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1
                or type(entry.get('bytes')) is not int or not 0 < entry['bytes'] <= 64 * 1024 * 1024
                or path.stat().st_size != entry['bytes']):
            raise ValueError('Candidate file size or storage is invalid.')
        digest, deadline, read_bytes = hashlib.sha256(), monotonic() + 10, 0
        with path.open('rb') as stream:
            while chunk := stream.read(1048576):
                read_bytes += len(chunk)
                if read_bytes > entry['bytes'] or monotonic() >= deadline:
                    raise ValueError('Candidate verification deadline exceeded.')
                digest.update(chunk)
        if digest.hexdigest() != entry.get('sha256'):
            raise ValueError('Candidate file checksum mismatch.')
    with os.scandir(candidate) as entries:
        actual_names = {entry.name for entry in islice(entries, 6)}
    if actual_names != names | {'release.json'}:
        raise ValueError('Candidate directory contains unlisted or missing files.')
    if not {'dashboard.zip', 'requirements.lock.txt', 'frontend-package-lock.json'} <= names:
        raise ValueError('Candidate release payloads are incomplete.')
    supported = manifest.get('database_schema_revisions')
    if supported is not None and (not isinstance(supported, list) or not 1 <= len(supported) <= 16
            or any(type(value) is not int or not 0 <= value <= 2147483647 for value in supported)
            or len(set(supported)) != len(supported)):
        raise ValueError('Candidate schema compatibility declaration is invalid.')
    revisions = {}
    for name in ('auth.sqlite', 'projects.sqlite'):
        path = plan.directory / name
        if (path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1
                or any(Path(str(path) + suffix).exists() for suffix in ('-wal', '-shm', '-journal'))):
            raise ValueError('Planning requires offline, checkpointed, unredirected database files.')
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as connection:
            revisions[name] = connection.execute('PRAGMA user_version').fetchone()[0]
    compatible = supported is not None and all(value in supported for value in revisions.values())
    return {'candidate_commit': candidate_commit, 'environment': plan.environment.value,
            'database_revisions': revisions, 'schema_compatible': compatible,
            'reason': ('Declared schema revisions match.' if compatible else
                       'Schema support is missing or does not include this database pair.'),
            'activation_enabled': False,
            'remaining_requirements': ['Verify trusted release provenance and installed candidate behavior.',
                'Review runtime/dependency compatibility and a fresh backup.',
                'Review explicit cutover and rollback authorization before starting any service.']}
