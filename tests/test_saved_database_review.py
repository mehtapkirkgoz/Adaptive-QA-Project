"""Saved DB metadata is scoped, non-resolving and HTTP configuration guarded."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient
from adaptive_qa.local_free import LocalFreeProjects,LocalFreeSessions,LOCAL_ACTOR
from adaptive_qa.project_settings import reference_name
from adaptive_qa.project_store import ProjectActor,ProjectNotFound
from adaptive_qa.saved_database_review import review_saved_database
from adaptive_qa.secrets import SecretReference
from adaptive_qa.web_app import create_app,CSRF_COOKIE


class SavedDatabaseReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'projects.sqlite';self.projects=LocalFreeProjects(self.path)
        self.pid=self.projects.create(LOCAL_ACTOR,'Owned saved DB').project_id
        self.reference=reference_name(LOCAL_ACTOR.user_id,self.pid,'database_path')
        self.settings=dict(base_url='http://127.0.0.1:8000',allowed_hosts=['127.0.0.1'],allow_data_changes=False,
            secret_references={'database_path':self.reference},local_database_binding=dict(table='inventory',expected_count=3))
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)

    def test_saved_review_is_non_resolving_scoped_and_tracks_full_settings(self):
        reopened=LocalFreeProjects(self.path)
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No target paths')), \
             patch('subprocess.Popen',side_effect=AssertionError('No child')):
            review=review_saved_database(reopened,LOCAL_ACTOR,self.pid)
        self.assertFalse(review['execution_authorized'])
        self.assertNotIn(self.reference,str(review))
        self.assertEqual(review['binding'],dict(table='inventory',expected_count=3))
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,allow_data_changes=True))
        self.assertNotEqual(review['contract_fingerprint'],review_saved_database(self.projects,LOCAL_ACTOR,self.pid)['contract_fingerprint'])
        for actor,pid in ((ProjectActor('b'*32),self.pid),(LOCAL_ACTOR,'0'*32)):
            with self.assertRaises(ProjectNotFound):review_saved_database(self.projects,actor,pid)

    def test_invalid_replacement_removal_and_reference_revocation(self):
        for changes in ({'table':'inventory; DELETE FROM inventory'},{'table':'sqlite_master'},
                        {'expected_count':True},{'expected_count':-1},{'path':'private.sqlite'}):
            with self.assertRaises(ValueError):
                self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,
                    local_database_binding=dict(self.settings['local_database_binding'],**changes)))
        self.assertEqual(self.projects.configuration(LOCAL_ACTOR,self.pid)['local_database_binding'],self.settings['local_database_binding'])
        with self.assertRaises(ValueError):
            self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,
                secret_references={'database_path':reference_name('b'*32,self.pid,'database_path')}))
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,secret_references={}))
        with self.assertRaises(ValueError):review_saved_database(self.projects,LOCAL_ACTOR,self.pid)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_database_binding=None))
        self.assertNotIn('local_database_binding',self.projects.configuration(LOCAL_ACTOR,self.pid))
        with self.assertRaises(ValueError):review_saved_database(self.projects,LOCAL_ACTOR,self.pid)

    def test_http_save_review_csrf_origin_and_no_execution_route(self):
        with TestClient(create_app(LocalFreeSessions(self.path),projects=self.projects),base_url='http://127.0.0.1:8765') as client:
            client.get('/api/auth/me')
            headers={'origin':'http://127.0.0.1:8765','x-csrf-token':client.cookies[CSRF_COOKIE]}
            base=f'/api/projects/{self.pid}'
            response=client.put(base+'/configuration',headers=headers,json=self.settings)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['local_database_binding'],self.settings['local_database_binding'])
            with patch.object(SecretReference,'resolve',side_effect=AssertionError('No target paths')):
                response=client.post(base+'/local-database/review',headers=headers,json={})
            self.assertEqual(response.status_code,200,response.text)
            self.assertFalse(response.json()['execution_authorized'])
            self.assertEqual(client.post(base+'/local-database/review',headers=headers,json={'path':'private.sqlite'}).status_code,400)
            self.assertEqual(client.post(base+'/local-database/review',headers={'origin':headers['origin']},json={}).status_code,401)
            self.assertEqual(client.post(base+'/local-database/review',headers=dict(headers,origin='https://other.test'),json={}).status_code,403)
            self.assertEqual(client.post(base.replace(self.pid,'0'*32)+'/local-database/review',headers=headers,json={}).status_code,404)
            self.assertEqual(client.post(base+'/local-database/jobs',headers=headers,json={}).status_code,404)
            self.assertEqual(client.get(base+'/runs').json()['runs'],[])
