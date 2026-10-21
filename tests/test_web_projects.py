"""Authenticated HTTP ownership and mutation boundaries with real SQLite stores."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from starlette.testclient import TestClient

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.project_store import ProjectStore
from adaptive_qa.web_app import create_app, CSRF_COOKIE


class WebProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.auth = AuthStore(self.path / 'auth.sqlite')
        self.projects = ProjectStore(self.path / 'projects.sqlite')
        self.alice = self.auth.create_user('alice@example.test', 'Local Alice password 123!')
        self.bob = self.auth.create_user('bob@example.test', 'Local Bob password 123!')
        app = create_app(self.auth, projects=self.projects)
        self.client = TestClient(app, base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close)
        self.headers = {'origin': 'http://127.0.0.1:8765', 'content-type': 'application/json'}
        self.client.post('/api/auth/login', headers=self.headers,
            json={'email': 'alice@example.test', 'password': 'Local Alice password 123!'})
        self.headers['x-csrf-token'] = self.client.cookies[CSRF_COOKIE]

    def test_create_list_get_rename_and_reopen(self):
        response = self.client.post('/api/projects', headers=self.headers, json={'name': 'Checkout'})
        self.assertEqual(response.status_code, 201)
        project = response.json()
        self.assertEqual(set(project), {'project_id', 'name'})
        path = '/api/projects/' + project['project_id']
        self.assertEqual(self.client.get(path).json(), project)
        self.assertEqual(self.client.get('/api/projects').json()['projects'], [project])
        renamed = self.client.patch(path, headers=self.headers, json={'name': 'Cart'})
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(ProjectStore(self.path / 'projects.sqlite').get(self.alice, project['project_id']).name, 'Cart')

    def test_cross_owner_reads_and_updates_match_missing_records(self):
        other = self.projects.create(self.bob, 'Private project')
        for method in ('get', 'patch'):
            responses = []
            for project_id in (other.project_id, '0' * 32):
                options = {'headers': self.headers, 'json': {'name': 'Changed'}} if method == 'patch' else {}
                responses.append(getattr(self.client, method)('/api/projects/' + project_id, **options))
            self.assertTrue(all(r.status_code == 404 for r in responses))
            self.assertEqual(responses[0].json(), responses[1].json())
        self.assertEqual(self.projects.get(self.bob, other.project_id).name, 'Private project')
        self.assertEqual(self.client.get('/api/projects').json()['projects'], [])

    def test_owner_fields_and_owner_headers_cannot_override_session(self):
        response = self.client.post('/api/projects', headers=self.headers,
            json={'name': 'Forged', 'owner_id': self.bob.user_id})
        self.assertEqual(response.status_code, 400)
        headers = dict(self.headers, **{'x-owner-id': self.bob.user_id})
        created = self.client.post('/api/projects', headers=headers, json={'name': 'Session owned'}).json()
        self.assertEqual(self.projects.get(self.alice, created['project_id']).owner_id, self.alice.user_id)

    def test_mutations_require_csrf_and_anonymous_requests_fail(self):
        response = self.client.post('/api/projects', headers={k: v for k, v in self.headers.items() if k != 'x-csrf-token'}, json={'name': 'Denied'})
        self.assertEqual(response.status_code, 401)
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/projects').status_code, 401)
        self.assertEqual(self.client.post('/api/projects', headers=self.headers, json={'name': 'Denied'}).status_code, 401)
        self.assertEqual(self.projects.list(self.alice), ())

    def test_bounded_pagination_is_stable_and_owner_filtered(self):
        first = self.projects.create(self.alice, 'First')
        self.projects.create(self.bob, 'Other')
        self.projects.create(self.alice, 'Second')
        result = self.client.get('/api/projects?limit=1&offset=1')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['projects'][0]['project_id'], first.project_id)
        for query in ('limit=0', 'limit=101', 'offset=-1', 'offset=100001', 'limit=1&limit=2', 'owner_id=private', 'limit=NaN'):
            response = self.client.get('/api/projects?' + query)
            self.assertEqual(response.status_code, 400, query)
            self.assertNotIn('private', response.text)

    def test_invalid_names_and_json_are_masked(self):
        for body in ('{"name":"private","name":"duplicate"}', '{"name":NaN}',
                     '{"name":""}', '{"name":[]}', '{"name":"private","unexpected":true}'):
            response = self.client.post('/api/projects', headers=self.headers, content=body)
            self.assertEqual(response.status_code, 400)
            self.assertNotIn('private', response.text)
            self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.projects.list(self.alice), ())

    def settings(self):
        project = self.projects.create(self.alice, 'Configured project')
        path = '/api/projects/' + project.project_id + '/configuration'
        data = {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                'allow_data_changes': False, 'secret_references': {}}
        return project, path, data

    def test_settings_can_save_read_and_remove_scoped_references(self):
        project, path, data = self.settings()
        empty = self.client.get(path).json()
        self.assertFalse(empty['configured'])
        name = empty['available_secret_references']['api_token']
        data['secret_references'] = {'api_token': name}
        result = self.client.put(path, headers=self.headers, json=data)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['secret_references']['api_token']['value'], '[REDACTED]')
        self.assertEqual(self.client.get(path).json(), result.json())
        data['secret_references'] = {}
        self.assertEqual(self.client.put(path, headers=self.headers, json=data).json()['secret_references'], {})

    def test_settings_cannot_be_read_or_changed_by_another_owner(self):
        project, _, data = self.settings()
        other = self.projects.create(self.bob, 'Private')
        for pid in (other.project_id, '0' * 32):
            path = '/api/projects/' + pid + '/configuration'
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(self.client.put(path, headers=self.headers, json=data).status_code, 404)
        self.assertFalse(self.projects.configuration(self.bob, other.project_id)['configured'])

    def test_settings_requires_csrf_and_masks_invalid_configuration(self):
        _, path, data = self.settings()
        headers = {k: v for k, v in self.headers.items() if k != 'x-csrf-token'}
        self.assertEqual(self.client.put(path, headers=headers, json=data).status_code, 401)
        for changes in ({'base_url': 'http://private:password@127.0.0.1:8000/'},
                        {'secret_references': {'api_token': 'PRIVATE_TOKEN'}},
                        {'owner_id': self.bob.user_id}):
            response = self.client.put(path, headers=self.headers, json=dict(data, **changes))
            self.assertEqual(response.status_code, 400)
            self.assertNotIn('private', response.text)
            self.assertNotIn('PRIVATE_TOKEN', response.text)
        self.assertFalse(self.client.get(path).json()['configured'])
