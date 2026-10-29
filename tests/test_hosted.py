import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.hosted import HostedOrigin,HostedProjects,create_hosted_app,hosted_route
from adaptive_qa.project_store import ProjectActor
from adaptive_qa.site_check import SiteChecks


class HostedTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.ui=self.root/'ui';self.ui.mkdir();(self.ui/'assets').mkdir()
        (self.ui/'index.html').write_text('<!doctype html><title>Owned fixture</title>')
        self.auth=AuthStore(self.root/'auth.sqlite')
        self.alice=self.auth.create_user('alice@example.test','fixture-password-123')
        self.bob=self.auth.create_user('bob@example.test','other-password-123')

    def client(self):return TestClient(create_hosted_app(self.root,'https://qa.example.test',ui_directory=self.ui),base_url='https://qa.example.test')

    def login(self,client,email='alice@example.test',password='fixture-password-123'):
        return client.post('/api/auth/login',json=dict(email=email,password=password),headers={'Origin':'https://qa.example.test'})

    def test_origin_and_unsupported_profiles_fail_closed(self):
        for origin in ('http://qa.example.test','https://qa.example.test/','https://user:pass@qa.example.test','https://qa.example.test?x=1','https://QA.example.test','https://qa.example.test:444'):
            with self.subTest(origin=origin),self.assertRaises(ValueError):HostedOrigin(origin)
        self.assertFalse(hosted_route('POST','/api/projects/abc/local-database/jobs'))
        self.assertFalse(hosted_route('POST','/api/organizations'))
        self.assertFalse(hosted_route('POST','/api/projects/'+'a'*32+'/interactive/demo-login/jobs'))

    def test_https_session_cookie_csrf_and_exact_origin(self):
        with self.client() as client:
            self.assertEqual(client.get('/api/auth/me').status_code,401)
            self.assertEqual(client.get('/api/runtime').json()['test_data_location'],'server')
            self.assertEqual(client.get('/api/runtime',headers={'Host':'evil.example'}).status_code,400)
            self.assertEqual(client.get('/api/runtime',headers={'X-Forwarded-Host':'qa.example.test'}).status_code,400)
            response=self.login(client);self.assertEqual(response.status_code,200)
            cookies=response.headers.get_list('set-cookie');self.assertEqual(len(cookies),2)
            self.assertTrue(all('Secure' in value and 'SameSite=strict' in value for value in cookies))
            self.assertIn('HttpOnly',next(c for c in cookies if c.startswith('adaptive_session=')))
            self.assertEqual(client.get('/api/auth/me').json()['edition'],'hosted')
            self.assertEqual(client.post('/api/auth/logout',json={},headers={'Origin':'https://evil.example'}).status_code,403)
            headers={'Origin':'https://qa.example.test','X-CSRF-Token':client.cookies['adaptive_csrf']}
            self.assertEqual(client.post('/api/auth/logout',json={},headers=headers).status_code,200)
            self.assertEqual(client.get('/api/auth/me').status_code,401)

    def test_real_accounts_own_separate_projects_and_history(self):
        with self.auth._connection() as c:users={r['email']:ProjectActor(r['user_id']) for r in c.execute('SELECT * FROM dashboard_users')}
        projects=HostedProjects(self.root/'projects.sqlite')
        alice=projects.create(users['alice@example.test'],'Alice private project')
        bob=projects.create(users['bob@example.test'],'Bob private project')
        with self.client() as client:
            self.login(client)
            rows=client.get('/api/projects').json()['projects'];self.assertEqual([r['project_id'] for r in rows],[alice.project_id])
            self.assertEqual(client.get(f'/api/projects/{bob.project_id}/configuration').status_code,404)
            self.assertEqual(client.get('/api/site-checks').json()['checks'],[])
            for route in (f'/api/projects/{alice.project_id}/local-database/jobs',f'/api/projects/{alice.project_id}/interactive/demo-login/jobs','/api/organizations'):
                self.assertEqual(client.post(route,json={},headers={'Origin':'https://qa.example.test','X-CSRF-Token':client.cookies['adaptive_csrf']}).status_code,404)
            self.assertNotIn('Bob',json.dumps(rows))

    def test_server_never_admits_controlled_local_target_or_free_identity(self):
        projects=HostedProjects(self.root/'projects.sqlite');checks=SiteChecks(projects,free=True)
        with self.auth._connection() as c:user=ProjectActor(c.execute('SELECT user_id FROM dashboard_users LIMIT 1').fetchone()[0])
        with patch('socket.getaddrinfo',side_effect=AssertionError('No target contact')):
            with self.assertRaises(ValueError):checks.submit(user,'http://127.0.0.1:8000/')
        self.assertEqual(projects.list(user),())
        (self.root/'preview-process.json').write_text('{}')
        with self.assertRaises(ValueError):create_hosted_app(self.root,'https://qa.example.test',ui_directory=self.ui)

    def test_browser_sandbox_flag_changes_no_local_defaults(self):
        from adaptive_qa.egress import chromium_proxy_options
        import os
        with patch.dict(os.environ,{'ADAPTIVE_QA_HOSTED_SANDBOX':'1'}):self.assertIs(chromium_proxy_options('http://127.0.0.1:1234')['chromium_sandbox'],True)
        with patch.dict(os.environ,{'ADAPTIVE_QA_HOSTED_SANDBOX':''}):self.assertNotIn('chromium_sandbox',chromium_proxy_options('http://127.0.0.1:1234'))


if __name__=='__main__':unittest.main()
