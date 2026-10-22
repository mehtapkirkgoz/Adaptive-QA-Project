"""Authenticated HTTP ownership and mutation boundaries with real SQLite stores."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from starlette.testclient import TestClient

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.project_store import ProjectStore
from adaptive_qa.web_app import create_app, CSRF_COOKIE
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_worker import configuration_fingerprint
from unittest.mock import patch
from dataclasses import asdict
from adaptive_qa.discovery import PageSnapshot, FormSnapshot, FieldSnapshot
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.models import TestResult, TestStatus


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

    def test_plan_review_is_owner_scoped_and_requires_saved_settings(self):
        project, path, data = self.settings()
        plan_path = '/api/projects/' + project.project_id + '/plan'
        self.assertEqual(self.client.get(plan_path).status_code, 409)
        self.client.put(path, headers=self.headers, json=data)
        response = self.client.get(plan_path)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['execution_authorized'])
        self.assertEqual(response.json()['counts']['selected'], 0)
        other = self.projects.create(self.bob, 'Private plan')
        self.assertEqual(self.client.get('/api/projects/' + other.project_id + '/plan').status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(plan_path).status_code, 401)

    def discovery(self):
        project, path, data = self.settings()
        self.client.put(path, headers=self.headers, json=data)
        return project, '/api/projects/' + project.project_id + '/discovery', data

    def test_discovery_submission_only_queues_and_can_cancel_before_worker(self):
        project, path, _ = self.discovery()
        with patch('adaptive_qa.dashboard_worker.discover_local_sample', side_effect=AssertionError('HTTP must not execute')):
            response = self.client.post(path, headers=self.headers, json={})
        self.assertEqual(response.status_code, 202)
        job = response.json()
        self.assertEqual(job['status'], 'queued')
        self.assertEqual(self.client.get(path).json()['jobs'], [job])
        self.assertEqual(self.client.get(path + '/' + job['job_id']).json(), job)
        self.assertEqual(self.client.post(path + '/' + job['job_id'] + '/cancel', headers=self.headers, json={}).json()['status'], 'cancelled')
        self.assertIsNone(DashboardDiscoveryQueue(self.projects).claim_next())

    def test_discovery_other_owner_wrong_project_and_missing_jobs_share_denial(self):
        _, path, _ = self.discovery()
        job = self.client.post(path, headers=self.headers, json={}).json()
        other = self.projects.create(self.bob, 'Other owner')
        wrong = '/api/projects/' + other.project_id + '/discovery'
        self.assertEqual(self.client.get(wrong).status_code, 404)
        for base, jid in ((wrong, job['job_id']), (path, '0' * 32)):
            self.assertEqual(self.client.get(base + '/' + jid).status_code, 404)
            self.assertEqual(self.client.post(base + '/' + jid + '/cancel', headers=self.headers, json={}).status_code, 404)

    def test_discovery_report_marks_changed_policy_as_historical(self):
        project, path, data = self.discovery()
        self.client.post(path, headers=self.headers, json={})
        queue = DashboardDiscoveryQueue(self.projects)
        work = queue.claim_next()
        report = {'project_id': project.project_id, 'execution_authorized': False,
                  'configuration_fingerprint': configuration_fingerprint(work.configuration)}
        queue.finish(work, report=report)
        self.assertTrue(self.client.get(path + '/' + work.job_id).json()['configuration_current'])
        self.client.put('/api/projects/' + project.project_id + '/configuration', headers=self.headers,
                        json=dict(data, allow_data_changes=True))
        response = self.client.get(path + '/' + work.job_id)
        self.assertFalse(response.json()['configuration_current'])
        self.assertNotIn('report', self.client.get(path).json()['jobs'][0])

    def test_discovery_requires_session_csrf_and_exact_empty_body(self):
        _, path, _ = self.discovery()
        headers = {k: v for k, v in self.headers.items() if k != 'x-csrf-token'}
        self.assertEqual(self.client.post(path, headers=headers, json={}).status_code, 401)
        for body in ({'owner_id': self.bob.user_id}, {'target': 'http://example.test/'}, {'execute': True}):
            self.assertEqual(self.client.post(path, headers=self.headers, json=body).status_code, 400)
        self.assertEqual(self.client.get(path).json()['jobs'], [])
        self.client.cookies.clear()
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post(path, headers=self.headers, json={}).status_code, 401)

    def run_request(self):
        project, _, _ = self.discovery()
        queue = DashboardDiscoveryQueue(self.projects)
        job = queue.submit(self.alice, project.project_id)
        page = PageSnapshot('http://127.0.0.1:8000/', forms=(FormSnapshot(fields=(
            FieldSnapshot('email'), FieldSnapshot('password')), buttons=('Sign in',)),), collection_complete=True)
        with patch('adaptive_qa.dashboard_worker.discover_local_sample', return_value={'pages': [asdict(page)], 'limitations': []}):
            self.assertEqual(process_discovery_once(queue)['status'], 'completed')
        return project, '/api/projects/' + project.project_id + '/runs', {
            'discovery_job_id': job['job_id'], 'case_ids': ['LOGIN-001']}

    def test_run_submission_only_queues_and_queued_cancel_prevents_execution(self):
        project, path, body = self.run_request()
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test', side_effect=AssertionError('HTTP must not execute')):
            response = self.client.post(path, headers=self.headers, json=body)
        self.assertEqual(response.status_code, 202)
        run = response.json()
        self.assertEqual(run['status'], 'queued')
        self.assertEqual(run['results'], [])
        self.assertEqual(self.client.get(path).json()['runs'], [run])
        self.assertEqual(self.client.get(path + '/' + run['run_id']).json(), run)
        self.assertEqual(self.client.post(path + '/' + run['run_id'] + '/cancel', headers=self.headers, json={}).json()['status'], 'cancelled')
        self.assertIsNone(DashboardRunQueue(self.projects).claim_next())

    def test_run_other_owner_wrong_project_and_missing_run_are_denied(self):
        _, path, body = self.run_request()
        run = self.client.post(path, headers=self.headers, json=body).json()
        other = self.projects.create(self.bob, 'Private run')
        wrong = '/api/projects/' + other.project_id + '/runs'
        self.assertEqual(self.client.get(wrong).status_code, 404)
        self.assertEqual(self.client.post(wrong, headers=self.headers, json=body).status_code, 404)
        for base, rid in ((wrong, run['run_id']), (path, '0' * 32)):
            self.assertEqual(self.client.get(base + '/' + rid).status_code, 404)
            self.assertEqual(self.client.post(base + '/' + rid + '/cancel', headers=self.headers, json={}).status_code, 404)

    def test_run_mutations_require_csrf_session_and_exact_selection_body(self):
        _, path, body = self.run_request()
        headers = {k: v for k, v in self.headers.items() if k != 'x-csrf-token'}
        self.assertEqual(self.client.post(path, headers=headers, json=body).status_code, 401)
        for change in ({'execute': True}, {'owner_id': self.bob.user_id},
                       {'case_ids': 'LOGIN-001'}, {'case_ids': []}, {'case_ids': ['API-001']},
                       {'case_ids': ['LOGIN-001', 'LOGIN-001']}):
            self.assertEqual(self.client.post(path, headers=self.headers, json=dict(body, **change)).status_code, 400)
        self.assertEqual(self.client.get(path).json()['runs'], [])
        self.client.cookies.clear()
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post(path, headers=self.headers, json=body).status_code, 401)

    def test_run_results_are_owned_masked_and_stale_report_cannot_start_another_run(self):
        project, path, body = self.run_request()
        self.client.post(path, headers=self.headers, json=body)
        queue = DashboardRunQueue(self.projects)
        work = queue.claim_next()
        queue.record_result(work, TestResult('LOGIN-001', TestStatus.FAILED, .2, 'PRIVATE /disk/path'))
        queue.finish(work)
        response = self.client.get(path + '/' + work.run_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'completed')
        self.assertEqual(response.json()['results'][0]['status'], 'failed')
        self.assertNotIn('PRIVATE', response.text)
        self.assertNotIn('claim_token', response.text)
        config = self.projects.configuration(self.alice, project.project_id)
        self.projects.save_configuration(self.alice, project.project_id, {
            'base_url': config['base_url'], 'allowed_hosts': config['allowed_hosts'],
            'allow_data_changes': True, 'secret_references': {}})
        self.assertEqual(self.client.post(path, headers=self.headers, json=body).status_code, 400)

    def test_http_active_run_cancel_wins_over_completion(self):
        _, path, body = self.run_request()
        self.client.post(path, headers=self.headers, json=body)
        queue = DashboardRunQueue(self.projects)
        work = queue.claim_next()
        response = self.client.post(path + '/' + work.run_id + '/cancel', headers=self.headers, json={})
        self.assertEqual(response.json()['status'], 'cancel_requested')
        self.assertFalse(queue.record_result(work, TestResult('LOGIN-001', TestStatus.PASSED, .1, 'Late')))
        self.assertEqual(queue.finish(work), 'cancelled')
