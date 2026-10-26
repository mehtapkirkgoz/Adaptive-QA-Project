from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient
from adaptive_qa.browser_reviews import BrowserReviews, validate_review
from adaptive_qa.project_store import ProjectStore, ProjectActor, ProjectNotFound
from adaptive_qa.local_free import LOCAL_ACTOR, LocalFreeProjects, create_free_app


def example():
    return dict(name='Owned review', target='https://example.test/', period='2026-10-27',
                checks=[dict(id='A-1',name='Observed condition',status='failed',evidence='Expected label missing.')],
                notes=['Browser observations only.'])


class BrowserReviewTests(unittest.TestCase):
    def test_import_is_owned_idempotent_and_does_not_execute_or_change_configuration(self):
        with TemporaryDirectory() as temp:
            projects=ProjectStore(Path(temp)/'projects.sqlite')
            owner=ProjectActor('a'*32);other=ProjectActor('b'*32)
            pid=projects.create(owner,'Preserved project').project_id
            before=projects.configuration(owner,pid)
            store=BrowserReviews(projects)
            with patch('socket.getaddrinfo',side_effect=AssertionError('No target contact')):
                self.assertEqual(store.list(owner),[])
                identity=store.import_review(owner,pid,example())
                self.assertEqual(store.import_review(owner,pid,example()),identity)
                self.assertEqual(len(store.list(owner)),1)
                self.assertEqual(store.list(other),[])
                with self.assertRaises(ProjectNotFound):store.import_review(other,pid,example())
            self.assertEqual(projects.configuration(owner,pid),before)
            row=store.list(owner)[0]
            self.assertEqual(row['counts'],dict(passed=0,failed=1,blocked=0,not_run=0))
            self.assertEqual(row['source'],'browser_review');self.assertFalse(row['execution_authorized'])

    def test_validation_does_not_trust_precomputed_counts_or_execution_fields(self):
        for field,value in [('counts',{'passed':99}),('execution_authorized',True),('secret','canary')]:
            data=example();data[field]=value
            with self.assertRaises(ValueError):validate_review(data)
        for status in ('completed','error',None):
            data=example();data['checks'][0]['status']=status
            with self.assertRaises(ValueError):validate_review(data)
        data=example();data['checks']*=2
        with self.assertRaises(ValueError):validate_review(data)
        for url in ('https://user:secret@example.test/','https://example.test/?token=secret','http://example.test/'):
            data=example();data['target']=url
            with self.assertRaises(ValueError):validate_review(data)
        data=example();data['checks'][0]['evidence']='x'*3001
        with self.assertRaises(ValueError):validate_review(data)

    def test_http_is_authenticated_read_only_and_reload_does_not_import(self):
        with TemporaryDirectory() as temp:
            path=Path(temp)/'projects.sqlite'
            projects=LocalFreeProjects(path);pid=projects.create(LOCAL_ACTOR,'Local').project_id
            reviews=BrowserReviews(projects);reviews.import_review(LOCAL_ACTOR,pid,example())
            with TestClient(create_free_app(path,port=8896),base_url='http://127.0.0.1:8896') as client:
                self.assertEqual(client.get('/api/browser-reviews').status_code,401)
                client.get('/api/auth/me')
                for _ in range(2):
                    response=client.get('/api/browser-reviews');self.assertEqual(response.status_code,200)
                    self.assertEqual(len(response.json()['reviews']),1)
                response=client.post('/api/browser-reviews',json=example(),headers={'Origin':'http://127.0.0.1:8896'})
                self.assertEqual(response.status_code,405)
            self.assertEqual(len(reviews.list(LOCAL_ACTOR)),1)
