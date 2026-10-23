"""Local license imports remain atomic, bounded and reverified at use time."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict
import base64
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from adaptive_qa.license_store import LicenseStore
from adaptive_qa.licensing import LicenseClaims, LicenseError, license_message


class LicenseStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name)/'license.sqlite'
        self.private = Ed25519PrivateKey.generate()
        self.keys = {'issuer': self.private.public_key().public_bytes_raw()}
        self.now = 150
        self.store = LicenseStore(self.database, self.keys, clock=lambda: self.now)

    def document(self, limit=3):
        claims = LicenseClaims('a'*32, 'b'*32, 100, 100, 200, limit, 2)
        payload = asdict(claims)
        signature = base64.urlsafe_b64encode(self.private.sign(license_message('issuer', payload))).rstrip(b'=').decode()
        return json.dumps(dict(key_id='issuer', payload=payload, signature=signature)).encode()

    def test_import_restart_and_expiry_preserve_signed_document(self):
        self.assertIsNone(self.store.current())
        claims = self.store.install(self.document())
        restarted = LicenseStore(self.database, self.keys, clock=lambda: self.now)
        self.assertEqual(restarted.current(), claims)
        self.now = 200
        with self.assertRaises(LicenseError): restarted.current()
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute('SELECT document FROM local_license').fetchone()[0], self.document())

    def test_invalid_import_and_external_tampering_cannot_grant_access(self):
        claims = self.store.install(self.document())
        for raw in (b'{}', b'x'*8193, 'untyped'):
            with self.assertRaises(LicenseError): self.store.install(raw)
            self.assertEqual(self.store.current(), claims)
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute('UPDATE local_license SET document=?', (b'{}',))
            connection.commit()
        with self.assertRaises(LicenseError): self.store.current()

    def test_trust_is_copied_and_not_loaded_from_license_database(self):
        self.store.install(self.document())
        self.keys.clear()
        self.assertEqual(self.store.current().max_projects, 3)
        other = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        with self.assertRaises(LicenseError): LicenseStore(self.database, {'issuer': other}, clock=lambda:150).current()
        for keys in ({}, {'bad key': other}, {'issuer': b'bad'}):
            with self.assertRaises(LicenseError): LicenseStore(self.database, keys)

    def test_parallel_imports_leave_one_complete_signed_record(self):
        documents = [self.document(limit) for limit in range(1, 9)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            claims = list(pool.map(self.store.install, documents))
        self.assertEqual({claim.max_projects for claim in claims}, set(range(1,9)))
        self.assertIn(self.store.current().max_projects, range(1,9))
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM local_license').fetchone()[0], 1)
