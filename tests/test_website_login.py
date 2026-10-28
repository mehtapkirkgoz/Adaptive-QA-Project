import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import time
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.discovery import PageSnapshot,FormSnapshot,FieldSnapshot
from adaptive_qa.website_login import login_candidate,review_website_login
from adaptive_qa.website_login_process import Document,Unsupported,execute,scoped_url,result_object
from adaptive_qa.local_free import LOCAL_ACTOR,LocalFreeProjects,create_free_app
from adaptive_qa.site_check import SiteChecks
from adaptive_qa.interactive_queue import OwnedInteractiveQueue
from adaptive_qa.project_store import ProjectActor,ProjectNotFound
from starlette.testclient import TestClient


URL='https://example.com/login'
FORM='<form method="post" action="/session"><input type="hidden" name="csrf" value="owned-token"><input type="email" name="email" required><input type="password" name="password" required><button>Sign in</button></form>'


class WebsiteLoginTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'projects.sqlite'
        self.projects=LocalFreeProjects(self.path)
        self.pid=self.projects.create(LOCAL_ACTOR,'Owned site').project_id
        self.settings=dict(base_url=URL,allowed_hosts=['example.com'],allow_data_changes=False,secret_references={})
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
        self.before=self.projects.configuration(LOCAL_ACTOR,self.pid)
        SiteChecks(self.projects,free=True)
        self.check='a'*32
        with self.projects._connection() as c:
            c.execute('INSERT INTO dashboard_site_checks (check_id,owner_id,project_id,server_id,status,url,summary_json) VALUES (?,?,?,?,?,?,?)',
                (self.check,LOCAL_ACTOR.user_id,self.pid,'fixture','completed',URL,json.dumps(dict(login=dict(status='found',candidate=dict(document_url=URL,identifier_kind='email'))))))
        self.queue=OwnedInteractiveQueue(self.projects)

    def review(self): return review_website_login(self.projects,LOCAL_ACTOR,self.pid,self.check)

    def test_discovery_requires_one_inspected_non_registration_form(self):
        project=ProjectConfig('site','site',URL,('example.com',))
        form=FormSnapshot('login',fields=(FieldSnapshot('email'),FieldSnapshot('password')),buttons=('Sign in',))
        page=PageSnapshot(URL,(form,))
        result=login_candidate([page],project,'public_https')
        self.assertEqual(result['candidate']['identifier_kind'],'email')
        self.assertEqual(login_candidate([PageSnapshot(URL)],project,'public_https')['status'],'not_found')
        self.assertEqual(login_candidate([page,PageSnapshot('https://example.com/other',(form,))],project,'public_https')['status'],'ambiguous')
        register=FormSnapshot('register',fields=form.fields,buttons=('Sign up',))
        self.assertEqual(login_candidate([PageSnapshot(URL,(register,))],project,'public_https')['status'],'not_found')

    def test_native_form_parser_retains_csrf_only_in_memory(self):
        endpoint,user,password,hidden,kind=Document(FORM).login(URL)
        self.assertEqual((endpoint,kind),('https://example.com/session','email'))
        self.assertEqual(hidden,[('csrf','owned-token')])
        for html in (FORM+FORM,FORM.replace('/session','https://foreign.example/steal'),
                     FORM.replace('method="post"','method="get"'),FORM.replace('type="password"','type="password" autocomplete="new-password"'),
                     FORM.replace('<button>','<button formaction="https://foreign.example">'),
                     '<iframe src="/challenge"></iframe>'+FORM):
            with self.subTest(html=html), self.assertRaises(Unsupported):Document(html).login(URL)
        for url in ('http://example.com/login','https://foreign.example/login','https://example.com/login?token=x','https://example.com:444/login','https://x:secret@example.com/login'):
            with self.assertRaises(Unsupported):scoped_url(url,URL)

    def test_owned_flow_never_calls_200_alone_success_or_retries(self):
        class Fixture:
            def __init__(self,url):self.attempted=0;self.cookies=[];self.session=False;self.closed=False
            def read(self,url):
                if url.endswith('/logout'):self.session=False;return URL,200,Document(FORM)
                return url,200,Document('<a href="/logout">Logout</a>' if self.session else FORM)
            def request(self,method,url,body):
                self.attempted+=1;self.session=True;self.cookies=['owned'];return 303,'https://example.com/secure',''
            def close(self):self.closed=True
        created=[]
        def factory(url):
            instance=Fixture(url);created.append(instance);return instance
        result=execute(URL,'email','qa@example.test','private-secret',factory)
        self.assertTrue(all(r['status']=='passed' for r in result['cases']))
        self.assertEqual(created[0].attempted,1);self.assertTrue(created[0].closed)
        self.assertNotIn('private-secret',json.dumps(result));self.assertNotIn('owned-token',json.dumps(result))
        class Uncertain(Fixture):
            def request(self,*args):self.attempted+=1;return 200,None,'<h1>Welcome</h1>'
        result=execute(URL,'email','qa@example.test','private-secret',Uncertain)
        self.assertEqual(next(r for r in result['cases'] if r['case_id']=='LOGIN-ACCOUNT')['status'],'not_run')

    def test_review_ownership_consent_staleness_and_no_credentials_in_queue(self):
        with patch('socket.getaddrinfo',side_effect=AssertionError('No network during admission')):
            review=self.review()
            with self.assertRaises(ProjectNotFound):review_website_login(self.projects,ProjectActor('b'*32),self.pid,self.check)
            for consent in (False,1,'true'):
                with self.assertRaises(ValueError):self.queue.submit_website_login(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint(),authorized=consent)
            job=self.queue.submit_website_login(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint(),authorized=True)
        self.assertEqual(job['scope'],'website_login')
        work=self.queue.claim_next(job_id=job['job_id']);self.assertEqual(work.review,review)
        rows=[dict(case_id=c,status='passed',reason_code='standard_form') for c in __import__('adaptive_qa.website_login_process',fromlist=['CASE_NAMES']).CASE_NAMES]
        self.queue.finish(work,result_object(dict(cases=rows,attempted_submissions=1)))
        self.assertEqual(len(self.queue.get(LOCAL_ACTOR,self.pid,job['job_id'])['result']['cases']),5)
        self.assertEqual(self.projects.configuration(LOCAL_ACTOR,self.pid),self.before)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,base_url='https://example.com/changed'))
        with self.assertRaises(ValueError):self.review()

    def test_http_origin_csrf_and_credentials_not_echoed_or_saved(self):
        with TestClient(create_free_app(self.path),base_url='http://127.0.0.1:8766') as client:
            client.get('/api/auth/me')
            headers={'Origin':'http://127.0.0.1:8766','X-CSRF-Token':client.cookies['adaptive_csrf']}
            base=f'/api/projects/{self.pid}/interactive/website-login'
            self.assertEqual(client.post(base+'/review',json={'check_id':self.check}).status_code,403)
            review=client.post(base+'/review',headers=headers,json={'check_id':self.check}).json()
            with patch('adaptive_qa.website_login_process.run_login',return_value=result_object(dict(cases=[dict(case_id=c,status='not_run',reason_code='unsupported_form') for c in __import__('adaptive_qa.website_login_process',fromlist=['CASE_NAMES']).CASE_NAMES],attempted_submissions=0))) as child:
                response=client.post(base+'/jobs',headers=headers,json=dict(check_id=self.check,identifier='secret-user',password='secret-password',authorized=True,confirmed_contract_fingerprint=review['contract_fingerprint']))
                self.assertEqual(response.status_code,202,response.text)
                deadline=time.monotonic()+5
                while self.queue.get(LOCAL_ACTOR,self.pid,response.json()['job_id'])['status'] in ('queued','running','cancel_requested'):
                    self.assertLess(time.monotonic(),deadline)
                    time.sleep(.02)
                child.assert_called_once()
            self.assertNotIn('secret-',response.text)
        self.assertNotIn(b'secret-user',self.path.read_bytes());self.assertNotIn(b'secret-password',self.path.read_bytes())

    def test_shared_capacity_and_configuration_cancellation_are_retained(self):
        review=self.review()
        jobs=[self.queue.submit_website_login(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint(),authorized=True) for _ in range(5)]
        with self.assertRaises(ValueError):self.queue.submit_website_login(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint(),authorized=True)
        work=self.queue.claim_next(job_id=jobs[-1]['job_id'])
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,base_url='https://example.com/changed'))
        self.assertTrue(self.queue.cancellation_requested(work))
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,jobs[-1]['job_id'])['status'],'cancel_requested')
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,jobs[0]['job_id'])['status'],'queued')

    def test_paid_license_gate_cannot_be_bypassed_by_login_consent(self):
        from test_local_licensed import LocalLicensedTests
        from adaptive_qa.local_licensed import LicensedLocalProjects
        from adaptive_qa.licensing import LicenseError
        fixture=LocalLicensedTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        paid=LicensedLocalProjects(self.path,fixture.licenses);queue=OwnedInteractiveQueue(paid)
        review=review_website_login(paid,LOCAL_ACTOR,self.pid,self.check)
        with self.assertRaises(LicenseError):queue.submit_website_login(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint(),authorized=True)
        fixture.install(2)
        job=queue.submit_website_login(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint(),authorized=True)
        fixture.now=200
        self.assertIsNone(queue.claim_next(job_id=job['job_id']))


if __name__=='__main__':unittest.main()
