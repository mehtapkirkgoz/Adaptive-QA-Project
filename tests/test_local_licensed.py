"""Upgrade preserves ownership; paid creation requires current signed capacity."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from adaptive_qa.auth_store import AuthStore, AuthenticationError
from adaptive_qa.license_store import LicenseStore
from adaptive_qa.licensing import LicenseClaims, LicenseError, license_message
from adaptive_qa.local_free import LOCAL_ACTOR, LocalFreeProjects
from adaptive_qa.local_licensed import LicensedLocalProjects, LicensedLocalSessions


class LocalLicensedTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = 150
        self.private = Ed25519PrivateKey.generate()
        self.licenses = LicenseStore(self.root/'license.sqlite',
            {'issuer': self.private.public_key().public_bytes_raw()}, clock=lambda:self.now)
        self.database = self.root/'projects.sqlite'

    def install(self, limit):
        payload = asdict(LicenseClaims('a'*32, 'b'*32, 100, 100, 200, limit, 1))
        signature = base64.urlsafe_b64encode(self.private.sign(license_message('issuer', payload))).rstrip(b'=').decode()
        self.licenses.install(json.dumps(dict(key_id='issuer', payload=payload, signature=signature)).encode())

    def test_upgrade_and_expiry_preserve_existing_projects(self):
        free = LocalFreeProjects(self.database)
        first = free.create(LOCAL_ACTOR, 'Existing site')
        paid = LicensedLocalProjects(self.database, self.licenses)
        with self.assertRaises(LicenseError): paid.create(LOCAL_ACTOR, 'Denied')
        self.install(2)
        second = paid.create(LOCAL_ACTOR, 'Second site')
        self.assertEqual(paid.get(LOCAL_ACTOR, first.project_id), first)
        with self.assertRaises(LicenseError): paid.create(LOCAL_ACTOR, 'Over cap')
        self.now = 200
        with self.assertRaises(LicenseError): paid.create(LOCAL_ACTOR, 'Expired')
        self.assertEqual({p.project_id for p in paid.list(LOCAL_ACTOR)}, {first.project_id, second.project_id})
        with self.assertRaises(ValueError): free.create(LOCAL_ACTOR, 'Downgrade cannot erase cap')

    def test_concurrent_creation_and_license_replacement_use_current_capacity(self):
        self.install(3)
        paid = LicensedLocalProjects(self.database, self.licenses)
        def create(index):
            try: return paid.create(LOCAL_ACTOR, str(index))
            except LicenseError: return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(item is not None for item in pool.map(create, range(8))), 3)
        self.install(1)
        with self.assertRaises(LicenseError): paid.create(LOCAL_ACTOR, 'Reduced')
        self.assertEqual(len(paid.list(LOCAL_ACTOR)), 3)
        self.install(None)
        self.assertIsNotNone(paid.create(LOCAL_ACTOR, 'Unlimited projects'))

    def test_only_designated_password_admin_maps_to_existing_workspace(self):
        auth = AuthStore(self.root/'auth.sqlite')
        administrator = auth.create_user('owner@example.test', 'long owner password')
        auth.create_user('other@example.test', 'long other password')
        sessions = LicensedLocalSessions(auth, administrator)
        grant = sessions.login('owner@example.test', 'long owner password')
        self.assertEqual(grant.actor, LOCAL_ACTOR)
        self.assertEqual(sessions.actor_for_session(grant.token.value), LOCAL_ACTOR)
        self.assertEqual(sessions.verify_csrf(grant.token.value, grant.csrf_token.value), LOCAL_ACTOR)
        with self.assertRaises(AuthenticationError): sessions.verify_csrf(grant.token.value, 'wrong')
        with self.assertRaises(AuthenticationError): sessions.login('other@example.test', 'long other password')
        with self.assertRaises(AuthenticationError): sessions.login('owner@example.test', 'incorrect password')
        sessions.logout(grant.token.value)
        with self.assertRaises(AuthenticationError): sessions.actor_for_session(grant.token.value)

    def test_worker_claims_share_capacity_and_recheck_expiry(self):
        from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
        from adaptive_qa.dashboard_runs import DashboardRunQueue
        self.install(None)
        projects = LicensedLocalProjects(self.database, self.licenses)
        project = projects.create(LOCAL_ACTOR, 'Site')
        discovery, runs = DashboardDiscoveryQueue(projects), DashboardRunQueue(projects)
        with projects._connection() as connection:
            for index in range(2):
                connection.execute("INSERT INTO dashboard_discovery_jobs(job_id,project_id,owner_id,status,configuration_json) VALUES(?,?,?,'queued','{}')",
                    (str(index)*32, project.project_id, LOCAL_ACTOR.user_id))
            connection.execute("INSERT INTO dashboard_test_runs(run_id,project_id,owner_id,discovery_job_id,case_ids_json,configuration_json,status) VALUES(?,?,?,?,?,?,?)",
                ('a'*32,project.project_id,LOCAL_ACTOR.user_id,'0'*32,'["LOGIN-001"]','{}','queued'))
        first = discovery.claim_next()
        self.assertIsNotNone(first)
        self.assertIsNone(discovery.claim_next())
        self.assertIsNone(runs.claim_next())
        discovery.finish(first, failed=True)
        run = runs.claim_next()
        self.assertIsNotNone(run)
        self.now = 200
        self.assertTrue(runs.cancellation_requested(run))
        with projects._connection() as connection:
            self.assertEqual(connection.execute('SELECT status FROM dashboard_test_runs WHERE run_id=?', (run.run_id,)).fetchone()[0], 'cancel_requested')
        self.assertIsNone(discovery.claim_next())
        with self.assertRaises(LicenseError): discovery.submit(LOCAL_ACTOR, project.project_id)
        with self.assertRaises(LicenseError): runs.submit(LOCAL_ACTOR, project.project_id, '0'*32, ('LOGIN-001',))
        with projects._connection() as connection, self.assertRaises(LicenseError):
            projects.admit_execution(connection)

    def test_licensed_http_requires_password_and_preserves_free_project(self):
        from starlette.testclient import TestClient
        from adaptive_qa.local_licensed import create_licensed_app
        free_project = LocalFreeProjects(self.database).create(LOCAL_ACTOR, 'Prior free site')
        auth = AuthStore(self.root/'auth.sqlite')
        administrator = auth.create_user('owner@example.test', 'long owner password')
        self.install(2)
        origin = 'http://127.0.0.1:8767'
        with TestClient(create_licensed_app(self.database, auth, administrator, self.licenses), base_url=origin) as client:
            self.assertEqual(client.get('/api/auth/me').status_code, 401)
            response = client.post('/api/auth/login', json={'email':'owner@example.test', 'password':'long owner password'}, headers={'Origin':origin})
            self.assertEqual(response.status_code, 200)
            headers = {'Origin':origin, 'X-CSRF-Token':client.cookies['adaptive_csrf']}
            self.assertEqual(client.get('/api/auth/me').json()['user_id'], LOCAL_ACTOR.user_id)
            self.assertEqual(client.get('/api/projects').json()['projects'][0]['project_id'], free_project.project_id)
            self.assertEqual(client.get('/api/organizations').status_code, 404)
            self.assertEqual(client.post('/api/projects', json={'name':'Second'}, headers={'Origin':origin}).status_code, 401)
            self.assertEqual(client.post('/api/projects', json={'name':'Second'}, headers=headers).status_code, 201)
            self.now = 200
            self.assertEqual(client.post('/api/projects', json={'name':'Expired'}, headers=headers).status_code, 400)
            self.assertEqual(len(client.get('/api/projects').json()['projects']), 2)
