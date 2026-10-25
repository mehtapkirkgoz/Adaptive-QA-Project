"""Explicit HTTPS review/admission retains local session and CSRF boundaries."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import test_saved_local_form as local_fixture
from adaptive_qa.local_free import LOCAL_ACTOR


class PublicFormWebTests(unittest.TestCase):
    def setUp(self):
        local_fixture.SavedLocalFormTests.setUp(self)
        self.binding=dict(self.binding,profile='public_https',document_url='https://qa.example.test/portal/access',
            endpoint_url='https://qa.example.test/auth/check')
        self.settings=dict(self.settings,base_url=self.binding['document_url'],allowed_hosts=['qa.example.test'],local_form_binding=self.binding)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)

    def review(self):return self.client.post(self.base+'/https/review',headers=self.headers,json=self.body)

    def test_review_is_non_executing_and_exact_confirmation_enqueues(self):
        with patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')):
            response=self.review();self.assertEqual(response.status_code,200,response.text)
            self.assertFalse(response.json()['execution_authorized'])
            self.assertEqual(self.queue.list(LOCAL_ACTOR,self.pid),())
            body=dict(self.body,confirmed_contract_fingerprint=response.json()['contract_fingerprint'])
            self.assertEqual(self.client.post(self.base+'/https/jobs',headers=self.headers,json=self.body).status_code,400)
            result=self.client.post(self.base+'/https/jobs',headers=self.headers,json=body)
            self.assertEqual(result.status_code,202,result.text)
            self.assertEqual(result.json()['scope'],'reviewed_public_https')

    def test_csrf_origin_missing_project_and_legacy_routes_fail_closed(self):
        for suffix in ('review','jobs'):
            body=dict(self.body,confirmed_contract_fingerprint='a'*64) if suffix=='jobs' else self.body
            for headers,status in (({k:v for k,v in self.headers.items() if k!='x-csrf-token'},401),(dict(self.headers,origin='https://other.example'),403)):
                self.assertEqual(self.client.post(self.base+'/https/'+suffix,headers=headers,json=body).status_code,status)
        self.assertEqual(self.client.post(self.base.replace(self.pid,'0'*32)+'/https/review',headers=self.headers,json=self.body).status_code,404)
        self.assertEqual(self.client.post(self.base+'/local/review',headers=self.headers,json=self.body).status_code,400)

    def test_stale_confirmation_permission_and_unrecognized_fields(self):
        digest=self.review().json()['contract_fingerprint']
        settings=deepcopy(self.settings);settings['local_form_binding']['endpoint_url']='https://qa.example.test/auth/changed'
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,settings)
        body=dict(self.body,confirmed_contract_fingerprint=digest)
        self.assertEqual(self.client.post(self.base+'/https/jobs',headers=self.headers,json=body).status_code,400)
        self.assertEqual(self.client.post(self.base+'/https/review',headers=self.headers,json=dict(self.body,password='canary')).status_code,400)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,allow_data_changes=False))
        self.assertEqual(self.review().status_code,400)
        self.assertEqual(self.queue.list(LOCAL_ACTOR,self.pid),())

    def test_shared_authenticated_app_has_no_https_submission_routes(self):
        from adaptive_qa.auth_store import AuthStore
        from adaptive_qa.web_app import create_app
        from starlette.testclient import TestClient
        app=create_app(AuthStore(self.database.with_name('shared-auth.sqlite')))
        with TestClient(app,base_url='http://127.0.0.1:8765') as client:
            for suffix in ('review','jobs'):
                self.assertEqual(client.post(self.base+'/https/'+suffix,headers=self.headers,json=self.body).status_code,404)
