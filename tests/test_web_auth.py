"""HTTP session boundaries against real credential/session persistence."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from starlette.testclient import TestClient

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.web_app import create_app, SESSION_COOKIE, CSRF_COOKIE


class WebAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = AuthStore(Path(self.temp.name) / 'auth.sqlite')
        self.actor = self.store.create_user('owner@example.test', 'Local test password 123!')
        self.client = TestClient(create_app(self.store), base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close)
        self.headers = {'origin': 'http://127.0.0.1:8765', 'content-type': 'application/json'}

    def login(self):
        return self.client.post('/api/auth/login', headers=self.headers,
            json={'email': 'owner@example.test', 'password': 'Local test password 123!'})

    def test_login_cookie_identity_and_revocation(self):
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        response = self.login()
        self.assertEqual(response.json(), {'user_id': self.actor.user_id})
        cookies = response.headers.get_list('set-cookie')
        self.assertIn('HttpOnly', cookies[0])
        self.assertNotIn('Domain=', cookies[0])
        self.assertTrue(all('SameSite=strict' in c and 'Path=/' in c for c in cookies))
        token = self.client.cookies[SESSION_COOKIE]
        self.assertNotIn(token, response.text)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 200)
        headers = dict(self.headers, **{'x-csrf-token': self.client.cookies[CSRF_COOKIE]})
        self.assertEqual(self.client.post('/api/auth/logout', headers=headers, json={}).status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me', headers={'cookie': f'{SESSION_COOKIE}={token}'}).status_code, 401)

    def test_missing_and_foreign_origins_cannot_login(self):
        for headers in ({'content-type': 'application/json'}, dict(self.headers, origin='https://other.test')):
            self.assertEqual(self.client.post('/api/auth/login', headers=headers, json={}).status_code, 403)

    def test_logout_requires_session_bound_csrf(self):
        self.login()
        self.assertEqual(self.client.post('/api/auth/logout', headers=self.headers, json={}).status_code, 401)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 200)

    def test_host_forwarding_query_and_media_boundaries(self):
        for headers in ({'host': 'other.test'}, {'x-forwarded-host': '127.0.0.1:8765'}):
            self.assertEqual(self.client.get('/api/auth/me', headers=headers).status_code, 400)
        self.assertEqual(self.client.get('/api/auth/me?token=private').status_code, 400)
        self.assertEqual(self.client.post('/api/auth/login', headers={'origin': self.headers['origin']}, content='{}').status_code, 415)

    def test_invalid_bodies_never_echo_credentials(self):
        for body in ('{"email":"private","email":"duplicate","password":"private"}',
                     '{"password":"private"}', 'null', '{"email":[],"password":"private"}'):
            response = self.client.post('/api/auth/login', headers=self.headers, content=body)
            self.assertEqual(response.status_code, 401)
            self.assertNotIn('private', response.text)
            self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.client.post('/api/auth/login', headers=self.headers,
                                         content='x' * 2049).status_code, 413)

    def test_global_admission_applies_across_identities(self):
        for _ in range(20):
            self.client.post('/api/auth/login', headers=self.headers, json={})
        self.assertEqual(self.login().status_code, 401)


if __name__ == '__main__':
    unittest.main()
