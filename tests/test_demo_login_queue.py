import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient

from adaptive_qa.demo_login_contract import DemoLoginScenario
from adaptive_qa.demo_login_review import review_demo_login
from adaptive_qa.interactive_queue import OwnedInteractiveQueue, process_owned_interactive_once
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.local_free import LOCAL_ACTOR, LocalFreeProjects, create_free_app
from adaptive_qa.models import TestStatus
from adaptive_qa.project_store import ProjectActor, ProjectNotFound


class DemoLoginQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'projects.sqlite'
        self.projects=LocalFreeProjects(self.path)
        self.pid=self.projects.create(LOCAL_ACTOR,'Existing owner project').project_id
        self.settings=dict(base_url='https://example.com/',allowed_hosts=['example.com'],
                           allow_data_changes=False,secret_references={})
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
        self.queue=OwnedInteractiveQueue(self.projects)

    def review(self,scenario=DemoLoginScenario.ACCEPTED,actor=LOCAL_ACTOR,consent=True):
        return review_demo_login(self.projects,actor,self.pid,scenario=scenario,authorized_demo=consent)

    def test_explicit_demo_consent_does_not_grant_writes_to_saved_site(self):
        before=self.projects.configuration(LOCAL_ACTOR,self.pid)
        with patch('socket.getaddrinfo',side_effect=AssertionError('No target access')):
            review=self.review()
            self.assertFalse(review.public()['execution_authorized'])
            for consent in (False,1,'true',None):
                with self.assertRaises(ValueError):self.review(consent=consent)
            with self.assertRaises(ProjectNotFound):self.review(actor=ProjectActor('b'*32))
            with self.assertRaises(ValueError):
                self.queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint='0'*64)
            job=self.queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint())
        self.assertEqual(job['scope'],'authorized_login_demo')
        self.assertEqual(self.projects.configuration(LOCAL_ACTOR,self.pid),before)
        self.assertFalse(before['allow_data_changes'])

    def test_all_scenarios_dispatch_only_the_demo_worker_and_sanitize_results(self):
        for scenario in DemoLoginScenario:
            review=self.review(scenario)
            job=self.queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint())
            with patch('adaptive_qa.demo_login_process.run_isolated_demo_login',
                return_value=InteractiveProbeResult(TestStatus.PASSED,'private-cookie-canary',1)) as child:
                self.assertEqual(process_owned_interactive_once(self.queue)['status'],'completed')
                self.assertEqual(child.call_args.args[0],review.plan)
            result=self.queue.get(LOCAL_ACTOR,self.pid,job['job_id'])
            self.assertEqual(result['result'],dict(status='passed',attempted_submissions=1))
            self.assertNotIn('private-cookie-canary',json.dumps(result))

    def test_changed_settings_invalidate_review_and_queued_dispatch(self):
        review=self.review()
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,base_url='https://example.com/new'))
        with self.assertRaises(ValueError):self.queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint())
        review=self.review();job=self.queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint())
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
        with patch('adaptive_qa.demo_login_process.run_isolated_demo_login') as child:
            self.assertIsNone(process_owned_interactive_once(self.queue));child.assert_not_called()
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,job['job_id'])['status'],'error')

    def test_shared_pending_limit_and_selective_claim_preserve_other_work(self):
        review=self.review()
        jobs=[self.queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint()) for _ in range(5)]
        with self.assertRaises(ValueError):self.queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint())
        work=self.queue.claim_next(job_id=jobs[-1]['job_id'])
        self.assertEqual(work.job_id,jobs[-1]['job_id'])
        self.assertEqual(self.queue.get(LOCAL_ACTOR,self.pid,jobs[0]['job_id'])['status'],'queued')
        self.queue.cancel(LOCAL_ACTOR,self.pid,work.job_id)
        self.assertTrue(self.queue.cancellation_requested(work))
        self.queue.finish(work,InteractiveProbeResult(TestStatus.CANCELLED,'cancelled',None))

    def test_paid_demo_admission_and_claim_retain_license_enforcement(self):
        from test_local_licensed import LocalLicensedTests
        from adaptive_qa.local_licensed import LicensedLocalProjects
        from adaptive_qa.licensing import LicenseError
        fixture=LocalLicensedTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        paid=LicensedLocalProjects(self.path,fixture.licenses)
        queue=OwnedInteractiveQueue(paid)
        review=review_demo_login(paid,LOCAL_ACTOR,self.pid,
            scenario=DemoLoginScenario.ACCEPTED,authorized_demo=True)
        with self.assertRaises(LicenseError):queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint())
        fixture.install(2)
        job=queue.submit_demo(LOCAL_ACTOR,review,confirmed_fingerprint=review.fingerprint())
        fixture.now=200
        self.assertIsNone(queue.claim_next())
        self.assertEqual(queue.cancel(LOCAL_ACTOR,self.pid,job['job_id'])['status'],'cancelled')

    def test_http_guards_review_without_target_contact_and_no_custom_url(self):
        with TestClient(create_free_app(self.path),base_url='http://127.0.0.1:8766') as client:
            client.get('/api/auth/me')
            headers={'Origin':'http://127.0.0.1:8766','X-CSRF-Token':client.cookies['adaptive_csrf']}
            base='/api/projects/'+self.pid+'/interactive/demo-login'
            body=dict(scenario='accepted_login',authorized_demo=True)
            with patch('socket.getaddrinfo',side_effect=AssertionError('No target access')):
                self.assertEqual(client.post(base+'/review',json=body).status_code,403)
                self.assertEqual(client.post(base+'/review',json=body,headers={'Origin':headers['Origin']}).status_code,401)
                self.assertEqual(client.post(base+'/review',json=body,headers=dict(headers,Origin='https://foreign.test')).status_code,403)
                self.assertEqual(client.post(base+'/review',json=dict(body,url='https://other.test'),headers=headers).status_code,400)
                self.assertEqual(client.post(base+'/review',json=dict(body,authorized_demo=False),headers=headers).status_code,400)
                review=client.post(base+'/review',json=body,headers=headers)
                self.assertEqual(review.status_code,200)
                self.assertEqual(client.post(base+'/jobs',json=dict(body,confirmed_contract_fingerprint='0'*64),headers=headers).status_code,400)
            self.assertEqual(self.queue.list(LOCAL_ACTOR,self.pid),())


if __name__=='__main__':unittest.main()
