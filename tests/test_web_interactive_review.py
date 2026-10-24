"""Authenticated local review endpoint is explicitly non-executing and scoped."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient
from adaptive_qa.local_free import LocalFreeProjects,LocalFreeSessions,LOCAL_ACTOR
from adaptive_qa.project_settings import reference_name
from adaptive_qa.secrets import SecretReference
from adaptive_qa.web_app import create_app,CSRF_COOKIE


class WebInteractiveReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        path=Path(self.temp.name)/'projects.sqlite'
        self.projects=LocalFreeProjects(path)
        project=self.projects.create(LOCAL_ACTOR,'Local review')
        self.pid=project.project_id
        self.settings=dict(base_url='http://127.0.0.1:8000/interactive/login-transition',allowed_hosts=['127.0.0.1'],
            allow_data_changes=True,secret_references={slot:reference_name(LOCAL_ACTOR.user_id,self.pid,slot)
                for slot in ('login_username','login_password')})
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
        self.client=TestClient(create_app(LocalFreeSessions(path),projects=self.projects),base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close)
        self.client.get('/api/auth/me')
        self.headers={'origin':'http://127.0.0.1:8765','content-type':'application/json','x-csrf-token':self.client.cookies[CSRF_COOKIE]}
        self.url='/api/projects/'+self.pid+'/interactive/review'
        self.body=dict(fixture_id='login-transition',completion=dict(logical_name='login.accepted',scope_test_id=None,
            locators=[dict(strategy='test_id',value='result',role=None)]))

    def test_review_returns_no_execution_authority_values_or_queued_runs(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')):
            response=self.client.post(self.url,headers=self.headers,json=self.body)
        self.assertEqual(response.status_code,200,response.text)
        self.assertFalse(response.json()['execution_authorized'])
        self.assertEqual(response.json()['scope'],'owned_fixture_only')
        self.assertNotIn('environment_variable',response.text)
        self.assertEqual(self.client.get('/api/projects/'+self.pid+'/runs').json()['runs'],[])
        self.assertFalse(self.client.get('/api/projects/'+self.pid+'/plan').json()['execution_authorized'])

    def test_session_and_csrf_are_required(self):
        headers={key:value for key,value in self.headers.items() if key!='x-csrf-token'}
        self.assertEqual(self.client.post(self.url,headers=headers,json=self.body).status_code,401)
        self.client.cookies.clear()
        self.assertEqual(self.client.post(self.url,headers=self.headers,json=self.body).status_code,401)

    def test_plaintext_refs_extra_authority_and_unknown_fixture_are_rejected(self):
        for changes in ({'password':'private'},{'inputs':['PATH']},{'execution_authorized':True},{'fixture_id':'busy'},{'timeout_seconds':True}):
            response=self.client.post(self.url,headers=self.headers,json=dict(self.body,**changes))
            self.assertEqual(response.status_code,400,response.text)
            self.assertNotIn('private',response.text)
        self.assertEqual(self.client.post(self.url.replace(self.pid,'0'*32),headers=self.headers,json=self.body).status_code,404)

    def test_policy_revocation_blocks_review_without_overwriting_settings(self):
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,allow_data_changes=False))
        response=self.client.post(self.url,headers=self.headers,json=self.body)
        self.assertEqual(response.status_code,400)
        self.assertFalse(self.projects.configuration(LOCAL_ACTOR,self.pid)['allow_data_changes'])
