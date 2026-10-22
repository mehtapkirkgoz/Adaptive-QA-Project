"""Real SQLite snapshot integrity without provisioning or publishing any service."""

import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from contextlib import closing
from unittest.mock import patch
from adaptive_qa.backup import create_backup
from adaptive_qa.deployment import DeploymentPlan, Environment


class EnvironmentBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plan = DeploymentPlan(Environment.STAGING, Path(self.temp.name), 'https://staging.example.test')
        self.plan.directory.mkdir()
        for name in ('auth.sqlite', 'projects.sqlite'):
            with closing(sqlite3.connect(self.plan.directory / name)) as connection:
                connection.execute('CREATE TABLE sample (value TEXT)')
                connection.execute('INSERT INTO sample VALUES (?)', ('private fixture',))
                connection.commit()

    def test_bundle_checksums_integrity_and_original_records_are_preserved(self):
        result = create_backup(self.plan, maintenance_confirmed=True)
        bundle = self.plan.directory / 'backups' / result['bundle_id']
        manifest = json.loads((bundle / 'manifest.json').read_text())
        self.assertEqual(manifest['environment'], 'staging')
        self.assertEqual({file['name'] for file in manifest['files']}, {'auth.sqlite', 'projects.sqlite'})
        for file in manifest['files']:
            path = bundle / file['name']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), file['sha256'])
            with closing(sqlite3.connect(path)) as connection:
                self.assertEqual(connection.execute('PRAGMA quick_check').fetchone(), ('ok',))
                self.assertEqual(connection.execute('SELECT value FROM sample').fetchone(), ('private fixture',))
            with closing(sqlite3.connect(self.plan.directory / file['name'])) as connection:
                self.assertEqual(connection.execute('SELECT value FROM sample').fetchone(), ('private fixture',))
        self.assertNotIn('private fixture', str(result))
        self.assertNotIn('private fixture', str(manifest))

    def test_confirmation_is_required_before_creating_backup_storage(self):
        for value in (False, None, 1, 'yes'):
            with self.assertRaises(ValueError):
                create_backup(self.plan, maintenance_confirmed=value)
        self.assertFalse((self.plan.directory / 'backups').exists())

    def test_missing_source_never_creates_an_empty_replacement_database(self):
        path = self.plan.directory / 'auth.sqlite'
        path.unlink()
        with self.assertRaises(ValueError):
            create_backup(self.plan, maintenance_confirmed=True)
        self.assertFalse(path.exists())
        self.assertFalse((self.plan.directory / 'backups').exists())

    def test_corrupt_source_is_not_published_as_a_verified_bundle(self):
        (self.plan.directory / 'projects.sqlite').write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            create_backup(self.plan, maintenance_confirmed=True)
        self.assertEqual(list((self.plan.directory / 'backups').iterdir()), [])

    def test_wal_commits_are_included_in_the_snapshot(self):
        source = self.plan.directory / 'projects.sqlite'
        with closing(sqlite3.connect(source)) as writer:
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute('INSERT INTO sample VALUES (?)', ('committed WAL value',))
            writer.commit()
            result = create_backup(self.plan, maintenance_confirmed=True)
            target = self.plan.directory / 'backups' / result['bundle_id'] / 'projects.sqlite'
            with closing(sqlite3.connect(target)) as snapshot:
                self.assertEqual(snapshot.execute('SELECT count(*) FROM sample').fetchone()[0], 2)

    def test_deadline_failure_does_not_publish_partial_snapshots(self):
        with patch('adaptive_qa.backup.monotonic', side_effect=[0, 11]):
            with self.assertRaisesRegex(ValueError, 'deadline'):
                create_backup(self.plan, maintenance_confirmed=True)
        self.assertEqual(list((self.plan.directory / 'backups').iterdir()), [])

    def test_concurrent_commit_invalidates_pair_instead_of_publishing_it(self):
        original_hash = hashlib.sha256
        changed = False
        def hash_during_backup(*args, **kwargs):
            nonlocal changed
            if not changed:
                changed = True
                with closing(sqlite3.connect(self.plan.directory / 'auth.sqlite')) as writer:
                    writer.execute('INSERT INTO sample VALUES (?)', ('concurrent commit',))
                    writer.commit()
            return original_hash(*args, **kwargs)
        with patch('adaptive_qa.backup.hashlib.sha256', side_effect=hash_during_backup):
            with self.assertRaisesRegex(ValueError, 'writes occurred'):
                create_backup(self.plan, maintenance_confirmed=True)
        self.assertEqual(list((self.plan.directory / 'backups').iterdir()), [])
