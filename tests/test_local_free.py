"""Account-free local sessions retain HTTP guards and transactional project caps."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from starlette.testclient import TestClient
from adaptive_qa.local_free import create_free_app, LocalFreeProjects, LocalFreeSessions, LOCAL_ACTOR
from adaptive_qa.auth_store import AuthenticationError


class LocalFreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'projects.sqlite'
        self.client = TestClient(create_free_app(self.path), base_url='http://127.0.0.1:8766')
        self.addCleanup(self.client.close)

    def bootstrap(self):
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 200)
        return {'Origin': 'http://127.0.0.1:8766', 'X-CSRF-Token': self.client.cookies['adaptive_csrf']}

    def test_account_free_bootstrap_creates_no_auth_database_and_retains_csrf_guards(self):
        self.assertEqual(self.client.get('/api/projects').status_code, 401)
        self.assertEqual(self.client.get('/api/auth/me', headers={'Sec-Fetch-Site': 'cross-site'}).status_code, 403)
        self.assertEqual(self.client.get('/api/auth/me', headers={'Origin': 'https://foreign.test'}).status_code, 403)
        headers = self.bootstrap()
        self.assertFalse(self.path.with_name('auth.sqlite').exists())
        self.assertEqual(self.client.get('/api/auth/me').json()['edition'], 'free')
        self.assertEqual(self.client.post('/api/projects', json={'name': 'First'}, headers={'Origin': headers['Origin']}).status_code, 401)
        self.assertEqual(self.client.post('/api/projects', json={'name': 'First'}, headers={**headers, 'Origin': 'https://foreign.test'}).status_code, 403)
        self.assertEqual(self.client.post('/api/projects', json={'name': 'First'}, headers=headers).status_code, 201)
        self.assertEqual(self.client.post('/api/projects', json={'name': 'Second'}, headers=headers).status_code, 400)
        self.assertEqual(len(self.client.get('/api/projects').json()['projects']), 1)
        self.assertEqual(self.client.get('/api/organizations').status_code, 404)
        self.assertEqual(self.client.get('/api/local/license').status_code, 404)
        with TestClient(create_free_app(self.path), base_url='http://127.0.0.1:8766') as reopened:
            reopened.get('/api/auth/me')
            self.assertEqual(len(reopened.get('/api/projects').json()['projects']), 1)

    def test_concurrent_project_creation_has_one_winner(self):
        store = LocalFreeProjects(self.path)
        def create(index):
            try:
                store.create(LOCAL_ACTOR, f'Project {index}')
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(create, range(8))), 1)

    def test_ephemeral_sessions_expire_and_never_register_accounts(self):
        now = [0]
        sessions = LocalFreeSessions(self.path, clock=lambda: now[0])
        grant = sessions.bootstrap()
        self.assertEqual(sessions.verify_csrf(grant.token.value, grant.csrf_token.value), LOCAL_ACTOR)
        self.assertNotIn(grant.token.value, repr(grant))
        with self.assertRaises(AuthenticationError):
            sessions.verify_csrf(grant.token.value, 'forged')
        now[0] = sessions.session_seconds+1
        with self.assertRaises(AuthenticationError):
            sessions.actor_for_session(grant.token.value)
        for _ in range(20): sessions.bootstrap()
        self.assertLessEqual(len(sessions.sessions), 16)
        with self.assertRaises(AuthenticationError): sessions.login('ignored', 'ignored')
