"""Real scoped API persistence/review remains non-executing and mutation guarded."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient
from adaptive_qa.local_free import LocalFreeProjects, LocalFreeSessions, LOCAL_ACTOR
from adaptive_qa.project_store import ProjectActor, ProjectNotFound
from adaptive_qa.saved_api_review import review_saved_api
from adaptive_qa.web_app import create_app, CSRF_COOKIE


class SavedApiReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'projects.sqlite'
        self.projects=LocalFreeProjects(self.path)
        self.pid=self.projects.create(LOCAL_ACTOR,'API owner').project_id
        self.binding=dict(path='/service/available',expected_status=200,json_field='available',expected_boolean=True)
        self.settings=dict(base_url='http://127.0.0.1:8000',allowed_hosts=['127.0.0.1'],
            allow_data_changes=False,secret_references={},local_api_binding=self.binding)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)

    def test_owned_offline_snapshot_persists_and_drift_changes_review(self):
        reopened=LocalFreeProjects(self.path)
        with patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')), \
             patch('adaptive_qa.secrets.SecretReference.resolve',side_effect=AssertionError('No values')):
            review=review_saved_api(reopened,LOCAL_ACTOR,self.pid)
        self.assertFalse(review['execution_authorized'])
        self.assertEqual(review['binding'],self.binding)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_api_binding=dict(self.binding,expected_boolean=False)))
        self.assertNotEqual(review['contract_fingerprint'],review_saved_api(self.projects,LOCAL_ACTOR,self.pid)['contract_fingerprint'])
        for actor,pid in ((ProjectActor('b'*32),self.pid),(LOCAL_ACTOR,'0'*32)):
            with self.assertRaises(ProjectNotFound):review_saved_api(self.projects,actor,pid)

    def test_invalid_metadata_preserves_previous_saved_configuration(self):
        for updates in ({'path':'//other'}, {'expected_status':True}, {'expected_boolean':1},
                        {'json_field':'nested.field'}, {'token':'private'}, {'path':'/api?q=value'}):
            with self.assertRaises(ValueError):
                self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_api_binding=dict(self.binding,**updates)))
        self.assertEqual(self.projects.configuration(LOCAL_ACTOR,self.pid)['local_api_binding'],self.binding)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_api_binding=None))
        self.assertNotIn('local_api_binding',self.projects.configuration(LOCAL_ACTOR,self.pid))
        with self.assertRaises(ValueError):review_saved_api(self.projects,LOCAL_ACTOR,self.pid)

    def test_http_review_requires_session_origin_csrf_and_exact_empty_body(self):
        with TestClient(create_app(LocalFreeSessions(self.path),projects=self.projects),base_url='http://127.0.0.1:8765') as client:
            client.get('/api/auth/me')
            headers={'origin':'http://127.0.0.1:8765','x-csrf-token':client.cookies[CSRF_COOKIE]}
            url=f'/api/projects/{self.pid}/local-api/review'
            with patch('adaptive_qa.api_process.run_isolated_api_case') as child:
                response=client.post(url,headers=headers,json={})
            self.assertEqual(response.status_code,200,response.text);child.assert_not_called()
            self.assertFalse(response.json()['execution_authorized'])
            self.assertEqual(client.post(url,headers=headers,json={'execute':True}).status_code,400)
            self.assertEqual(client.post(url,headers={'origin':headers['origin']},json={}).status_code,401)
            self.assertEqual(client.post(url,headers=dict(headers,origin='https://other.test'),json={}).status_code,403)
            self.assertEqual(client.post(url.replace(self.pid,'0'*32),headers=headers,json={}).status_code,404)
            self.assertEqual(client.get(f'/api/projects/{self.pid}/runs').json()['runs'],[])
