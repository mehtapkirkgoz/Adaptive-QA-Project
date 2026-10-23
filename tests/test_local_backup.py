"""Free/paid offline backups preserve licenses and never reactivate queued work."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.auth_store import AuthStore, AuthenticationError
from adaptive_qa.local_backup import create_local_backup, restore_local_backup
from adaptive_qa.local_free import create_free_app, LOCAL_ACTOR, LocalFreeProjects
from adaptive_qa.license_store import LicenseStore
from adaptive_qa.licensing import LicenseError
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class LocalBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.workspace,self.bundle,self.recovered = (self.root/name for name in ('workspace','snapshot','recovered'))
        create_free_app(self.workspace/'projects.sqlite')
        self.project = LocalFreeProjects(self.workspace/'projects.sqlite').create(LOCAL_ACTOR,'Preserved')

    def test_free_project_only_roundtrip_creates_no_account_or_license_database(self):
        self.assertEqual(create_local_backup(self.workspace,self.bundle,maintenance_confirmed=True)['databases'],1)
        result = restore_local_backup(self.bundle,self.recovered,maintenance_confirmed=True)
        self.assertFalse(result['activation_enabled'])
        self.assertEqual(LocalFreeProjects(self.recovered/'projects.sqlite').get(LOCAL_ACTOR,self.project.project_id), self.project)
        self.assertFalse((self.recovered/'auth.sqlite').exists())
        self.assertFalse((self.recovered/'license.sqlite').exists())
        with self.assertRaises(ValueError): restore_local_backup(self.bundle,self.recovered,maintenance_confirmed=True)

    def test_paid_snapshot_preserves_raw_license_but_revalidates_and_invalidates_sessions(self):
        auth = AuthStore(self.workspace/'auth.sqlite')
        auth.create_user('owner@example.test','long local password')
        grant = auth.login('owner@example.test','long local password')
        keys = {'issuer':Ed25519PrivateKey.generate().public_key().public_bytes_raw()}
        store = LicenseStore(self.workspace/'license.sqlite',keys)
        with store._connection() as connection:
            connection.execute('INSERT INTO local_license VALUES(1,?)',(b'{}',))
        with closing(sqlite3.connect(self.workspace/'projects.sqlite')) as connection:
            connection.execute("INSERT INTO dashboard_discovery_jobs(job_id,project_id,owner_id,status,configuration_json,claim_token) VALUES(?,?,?,'running','{}','old-claim')",('a'*32,self.project.project_id,LOCAL_ACTOR.user_id))
            connection.commit()
        self.assertEqual(create_local_backup(self.workspace,self.bundle,maintenance_confirmed=True)['databases'],3)
        restore_local_backup(self.bundle,self.recovered,maintenance_confirmed=True)
        restored = AuthStore(self.recovered/'auth.sqlite')
        with self.assertRaises(AuthenticationError): restored.actor_for_session(grant.token.value)
        restored.login('owner@example.test','long local password')
        with self.assertRaises(LicenseError): LicenseStore(self.recovered/'license.sqlite',keys).current()
        with closing(sqlite3.connect(self.recovered/'projects.sqlite')) as connection:
            self.assertEqual(connection.execute('SELECT status,claim_token FROM dashboard_discovery_jobs').fetchone(),('cancelled',None))
        with closing(sqlite3.connect(self.recovered/'license.sqlite')) as connection:
            self.assertEqual(connection.execute('SELECT document FROM local_license').fetchone()[0],b'{}')

    def test_confirmation_tampering_and_unexpected_files_prevent_publication(self):
        with self.assertRaises(ValueError): create_local_backup(self.workspace,self.bundle)
        create_local_backup(self.workspace,self.bundle,maintenance_confirmed=True)
        with self.assertRaises(ValueError): restore_local_backup(self.bundle,self.recovered)
        (self.bundle/'unexpected').write_text('extra',encoding='utf-8')
        with self.assertRaises(ValueError): restore_local_backup(self.bundle,self.recovered,maintenance_confirmed=True)
        self.assertFalse(self.recovered.exists())
        (self.bundle/'unexpected').unlink()
        with (self.bundle/'projects.sqlite').open('ab') as stream: stream.write(b'changed')
        with self.assertRaises(ValueError): restore_local_backup(self.bundle,self.recovered,maintenance_confirmed=True)
        self.assertFalse(self.recovered.exists())

    def test_valid_license_restore_does_not_extend_its_original_expiry(self):
        import base64
        from dataclasses import asdict
        from adaptive_qa.licensing import LicenseClaims, license_message
        private = Ed25519PrivateKey.generate()
        keys = {'issuer':private.public_key().public_bytes_raw()}
        original = LicenseStore(self.workspace/'license.sqlite',keys,clock=lambda:150)
        payload = asdict(LicenseClaims('a'*32,'b'*32,100,100,200,3,1))
        signature = base64.urlsafe_b64encode(private.sign(license_message('issuer',payload))).rstrip(b'=').decode()
        original.install(json.dumps(dict(key_id='issuer',payload=payload,signature=signature)).encode())
        create_local_backup(self.workspace,self.bundle,maintenance_confirmed=True)
        restore_local_backup(self.bundle,self.recovered,maintenance_confirmed=True)
        self.assertEqual(LicenseStore(self.recovered/'license.sqlite',keys,clock=lambda:150).current().expires_at,200)
        with self.assertRaises(LicenseError): LicenseStore(self.recovered/'license.sqlite',keys,clock=lambda:200).current()

    def test_writes_during_snapshot_prevent_publishing_mixed_workspace(self):
        from unittest.mock import patch
        from adaptive_qa.local_backup import _digest
        changed = False
        def mutate(path):
            nonlocal changed
            result = _digest(path)
            if not changed:
                changed = True
                with closing(sqlite3.connect(self.workspace/'projects.sqlite')) as connection:
                    connection.execute("UPDATE dashboard_projects SET name='Concurrent write'")
                    connection.commit()
            return result
        with patch('adaptive_qa.local_backup._digest',side_effect=mutate), self.assertRaisesRegex(ValueError,'Workspace changed'):
            create_local_backup(self.workspace,self.bundle,maintenance_confirmed=True)
        self.assertFalse(self.bundle.exists())
