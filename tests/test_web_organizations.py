"""Real authenticated ASGI requests enforce organization roles and boundaries."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from fastapi.testclient import TestClient

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.project_store import ProjectStore
from adaptive_qa.organization_store import OrganizationStore
from adaptive_qa.organization_policy import OrganizationQuota, OrganizationRole as Role
from adaptive_qa.web_app import create_app, CSRF_COOKIE


class WebOrganizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthStore(root/'auth.sqlite')
        self.projects = ProjectStore(root/'projects.sqlite')
        self.alice = self.auth.create_user('alice@example.test', 'Local Alice password 123!')
        self.bob = self.auth.create_user('bob@example.test', 'Local Bob password 123!')
        self.organizations = OrganizationStore(self.projects)
        self.org = self.organizations.create(self.alice, 'One', quota=OrganizationQuota(1, 2, 1, 5))
        self.second = self.organizations.create(self.bob, 'Two')
        self.client = TestClient(create_app(self.auth, projects=self.projects), base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close)
        self.path = f'/api/organizations/{self.org}/projects'
        self.login('alice')

    def login(self, name):
        self.client.cookies.clear()
        self.headers = {'origin': 'http://127.0.0.1:8765', 'content-type': 'application/json'}
        password = f'Local {name.title()} password 123!'
        response = self.client.post('/api/auth/login', headers=self.headers,
                                    json={'email': name+'@example.test', 'password': password})
        self.assertEqual(response.status_code, 200)
        self.headers['x-csrf-token'] = self.client.cookies[CSRF_COOKIE]

    def test_list_create_project_configuration_and_quota_without_execution(self):
        listed = self.client.get('/api/organizations').json()['organizations']
        self.assertEqual([x['organization_id'] for x in listed], [self.org])
        response = self.client.post(self.path, headers=self.headers, json={'name': 'Shared'})
        self.assertEqual(response.status_code, 201)
        project = response.json()
        target = self.path+'/'+project['project_id']
        settings = {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                    'allow_data_changes': False, 'secret_references': {}}
        saved = self.client.put(target+'/configuration', headers=self.headers, json=settings)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.get(target+'/configuration').json(), saved.json())
        self.assertEqual(self.client.post(self.path, headers=self.headers, json={'name': 'Overflow'}).status_code, 409)
        self.assertEqual(self.client.get('/api/projects').json()['projects'], [])
        with self.projects._connection() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM dashboard_test_runs').fetchone()[0], 0)
        self.assertEqual(self.client.post(target+'/runs', headers=self.headers, json={}).status_code, 404)

    def test_anonymous_other_organization_and_revoked_member_cannot_read(self):
        project = self.client.post(self.path, headers=self.headers, json={'name': 'Shared'}).json()
        target = self.path+'/'+project['project_id']
        self.login('bob')
        self.assertEqual(self.client.get(target).status_code, 404)
        self.organizations.set_member(self.alice, self.org, self.bob.user_id, Role.VIEWER)
        self.assertEqual(self.client.get(target).status_code, 200)
        self.assertEqual(self.client.patch(target, headers=self.headers, json={'name': 'Forbidden'}).status_code, 404)
        self.organizations.remove_member(self.alice, self.org, self.bob.user_id)
        self.assertEqual(self.client.get(target).status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/organizations').status_code, 401)
        self.assertEqual(self.client.get(target).status_code, 401)

    def test_mutations_require_csrf_origin_and_exact_fields(self):
        headers = dict(self.headers)
        del headers['x-csrf-token']
        self.assertEqual(self.client.post(self.path, headers=headers, json={'name': 'No CSRF'}).status_code, 401)
        headers = dict(self.headers, origin='http://untrusted.test')
        self.assertEqual(self.client.post(self.path, headers=headers, json={'name': 'No origin'}).status_code, 403)
        self.assertEqual(self.client.post('/api/organizations', headers=self.headers,
                         json={'name': 'Injected', 'role': 'owner'}).status_code, 400)
        result = self.client.post('/api/organizations', headers=self.headers, json={'name': 'New'})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()['role'], 'owner')
        self.assertNotIn(self.second, [x['organization_id'] for x in self.client.get('/api/organizations').json()['organizations']])

    def test_scoped_discovery_is_queued_without_execution_and_viewer_cannot_dispatch(self):
        project = self.client.post(self.path, headers=self.headers, json={'name': 'Shared'}).json()
        base = self.path+'/'+project['project_id']
        settings = {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                    'allow_data_changes': False, 'secret_references': {}}
        self.assertEqual(self.client.put(base+'/configuration', headers=self.headers, json=settings).status_code, 200)
        response = self.client.post(base+'/discovery', headers=self.headers, json={})
        self.assertEqual(response.status_code, 202)
        job = response.json()
        self.assertEqual(job['status'], 'queued')
        self.assertNotIn('claim_token', job)
        self.assertNotIn('report', job)
        self.login('bob')
        self.assertEqual(self.client.get(base+'/discovery').status_code, 404)
        self.organizations.set_member(self.alice, self.org, self.bob.user_id, Role.VIEWER)
        self.assertEqual(self.client.get(base+'/discovery').status_code, 200)
        self.assertEqual(self.client.post(base+'/discovery', headers=self.headers, json={}).status_code, 404)
        self.assertEqual(self.client.post(base+'/discovery/'+job['job_id']+'/cancel', headers=self.headers, json={}).status_code, 404)
        self.login('alice')
        cancelled = self.client.post(base+'/discovery/'+job['job_id']+'/cancel', headers=self.headers, json={})
        self.assertEqual(cancelled.json()['status'], 'cancelled')
