"""Read-only, bounded verification of an offline environment backup bundle."""

from contextlib import closing
from datetime import datetime
import hashlib
import json
from itertools import islice
import os
import re
import sqlite3
from time import monotonic

from adaptive_qa.deployment import DeploymentPlan


def _regular(path):
    if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError('Backup files must be regular and unredirected.')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate backup manifest keys are not permitted.')
        result[key] = value
    return result


def verify_backup(plan, bundle_id):
    """Validate a private offline bundle without restoring or opening live stores."""
    if (not isinstance(plan, DeploymentPlan) or not isinstance(bundle_id, str)
            or re.fullmatch(r'[0-9a-f]{32}', bundle_id) is None):
        raise ValueError('A validated plan and a lowercase backup bundle ID are required.')
    bundle = plan.directory / 'backups' / bundle_id
    if bundle.resolve() != bundle or not bundle.is_dir():
        raise ValueError('Backup bundle is missing or redirected.')
    with os.scandir(bundle) as entries:
        names = {entry.name for entry in islice(entries, 4)}
    if names != {'manifest.json', 'auth.sqlite', 'projects.sqlite'}:
        raise ValueError('Backup bundle must contain exactly its manifest and database pair.')
    manifest_path = bundle / 'manifest.json'
    _regular(manifest_path)
    with manifest_path.open('rb') as stream:
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise ValueError('Backup manifest exceeds its size limit.')
    try:
        manifest = json.loads(raw, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError('Backup manifest is invalid.') from None
    if (not isinstance(manifest, dict)
            or set(manifest) != {'schema_version', 'bundle_id', 'environment', 'created_at',
                                 'files', 'maintenance_confirmation'}
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or manifest['bundle_id'] != bundle_id
            or manifest['environment'] != plan.environment.value
            or manifest['maintenance_confirmation'] is not True):
        raise ValueError('Backup manifest does not match this environment and format.')
    try:
        stamp = datetime.fromisoformat(manifest['created_at'])
        if stamp.utcoffset() is None:
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError('Backup creation time must include a timezone.') from None
    files = manifest['files']
    if not isinstance(files, list) or len(files) != 2:
        raise ValueError('Backup manifest requires both databases.')
    seen = set()
    for entry in files:
        if (not isinstance(entry, dict) or set(entry) != {'name', 'bytes', 'sha256'}
                or not isinstance(entry['name'], str)
                or entry['name'] not in ('auth.sqlite', 'projects.sqlite') or entry['name'] in seen
                or type(entry['bytes']) is not int or not 0 < entry['bytes'] <= 256 * 1024 * 1024
                or not isinstance(entry['sha256'], str)
                or re.fullmatch(r'[0-9a-f]{64}', entry['sha256']) is None):
            raise ValueError('Backup file metadata is invalid.')
        seen.add(entry['name'])
        path = bundle / entry['name']
        _regular(path)
        if path.stat().st_size != entry['bytes']:
            raise ValueError('Backup file length does not match its manifest.')
        deadline = monotonic() + 10
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while chunk := stream.read(1048576):
                if monotonic() >= deadline:
                    raise ValueError('Backup verification deadline exceeded.')
                digest.update(chunk)
        if digest.hexdigest() != entry['sha256']:
            raise ValueError('Backup file checksum does not match its manifest.')
        # Bundles are offline standalone snapshots. Immutable mode creates no WAL/SHM files.
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as connection:
            connection.execute('PRAGMA trusted_schema=OFF')
            connection.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
            if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise ValueError('Backup integrity verification failed.')
        if monotonic() >= deadline:
            raise ValueError('Backup verification deadline exceeded.')
    return {'bundle_id': bundle_id, 'environment': plan.environment.value,
            'databases': 2, 'verified': True, 'restored': False}
