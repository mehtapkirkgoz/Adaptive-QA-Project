"""Offline backup corruption, environment binding and non-restoration checks."""

from contextlib import closing, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.__main__ import main
from adaptive_qa.backup import create_backup
from adaptive_qa.backup_verification import verify_backup
from adaptive_qa.deployment import DeploymentPlan, Environment


class BackupVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plan = DeploymentPlan(Environment.STAGING, Path(self.temp.name), 'https://qa.example.test')
        self.plan.directory.mkdir()
        for name in ('auth.sqlite', 'projects.sqlite'):
            with closing(sqlite3.connect(self.plan.directory / name)) as connection:
                connection.execute('CREATE TABLE sample(value TEXT)')
                connection.execute("INSERT INTO sample VALUES ('original')")
                connection.commit()
        self.bundle_id = create_backup(self.plan, maintenance_confirmed=True)['bundle_id']
        self.bundle = self.plan.directory / 'backups' / self.bundle_id
        self.manifest_path = self.bundle / 'manifest.json'

    def rewrite(self, change):
        manifest = json.loads(self.manifest_path.read_text())
        change(manifest)
        self.manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

    def test_cli_verifies_without_restoring_live_records_or_creating_sidecars(self):
        with closing(sqlite3.connect(self.plan.directory / 'projects.sqlite')) as connection:
            connection.execute("UPDATE sample SET value='new live value'")
            connection.commit()
        before = {path.relative_to(self.plan.directory): path.read_bytes()
                  for path in self.plan.directory.rglob('*') if path.is_file()}
        output = StringIO()
        with patch('sys.argv', ['adaptive-qa', 'deployment', 'verify-backup', '--environment', 'staging',
                '--data-root', str(self.plan.data_root), '--origin', self.plan.public_origin,
                '--bundle-id', self.bundle_id]), redirect_stdout(output), \
                patch('socket.socket', side_effect=AssertionError('No network')):
            main()
        result = json.loads(output.getvalue())
        self.assertTrue(result['verified'])
        self.assertFalse(result['restored'])
        after = {path.relative_to(self.plan.directory): path.read_bytes()
                 for path in self.plan.directory.rglob('*') if path.is_file()}
        self.assertEqual(before, after)

    def test_tampered_snapshot_fails_even_when_length_is_unchanged(self):
        path = self.bundle / 'projects.sqlite'
        raw = path.read_bytes()
        path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            verify_backup(self.plan, self.bundle_id)

    def test_digest_alone_cannot_make_corrupt_sqlite_valid(self):
        path = self.bundle / 'projects.sqlite'
        path.write_bytes(b'not sqlite')
        def corrupt(manifest):
            entry = next(item for item in manifest['files'] if item['name'] == path.name)
            entry.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.rewrite(corrupt)
        with self.assertRaises(sqlite3.DatabaseError):
            verify_backup(self.plan, self.bundle_id)

    def test_wrong_environment_and_duplicate_database_entries_are_rejected(self):
        original = self.manifest_path.read_bytes()
        for change in (lambda value: value.update(environment='production'),
                       lambda value: value['files'].__setitem__(1, value['files'][0])):
            self.manifest_path.write_bytes(original)
            self.rewrite(change)
            with self.assertRaises(ValueError):
                verify_backup(self.plan, self.bundle_id)

    def test_traversal_ids_and_extra_bundle_files_are_rejected(self):
        for value in ('../production', '..', '/tmp/backup', 'A' * 32, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify_backup(self.plan, value)
        (self.bundle / 'projects.sqlite-wal').write_bytes(b'unexpected')
        with self.assertRaisesRegex(ValueError, 'exactly'):
            verify_backup(self.plan, self.bundle_id)

    def test_duplicate_json_keys_and_oversized_manifests_are_rejected(self):
        for raw in ('{"schema_version":1,"schema_version":1}', ' ' * 16385):
            self.manifest_path.write_text(raw, encoding='utf-8')
            with self.assertRaises(ValueError):
                verify_backup(self.plan, self.bundle_id)

    def test_deadline_and_missing_database_fail_without_creating_files(self):
        with patch('adaptive_qa.backup_verification.monotonic', side_effect=[0, 11]):
            with self.assertRaisesRegex(ValueError, 'deadline'):
                verify_backup(self.plan, self.bundle_id)
        (self.bundle / 'auth.sqlite').unlink()
        with self.assertRaises(ValueError):
            verify_backup(self.plan, self.bundle_id)
        self.assertFalse((self.bundle / 'auth.sqlite').exists())
