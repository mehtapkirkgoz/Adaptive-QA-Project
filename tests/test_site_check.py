"""One-click orchestration must retain the existing execution and ownership boundaries."""
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient
from adaptive_qa.local_free import LocalFreeProjects, LOCAL_ACTOR, create_free_app
from adaptive_qa.project_store import ProjectActor, ProjectNotFound
from adaptive_qa.site_check import SiteChecks, SiteCheckBusy
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.discovery import PageSnapshot, FormSnapshot, FieldSnapshot
from adaptive_qa.models import TestResult, TestStatus


class SiteCheckTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.projects = LocalFreeProjects(Path(temp.name)/'workspace'/'projects.sqlite')
        self.service = SiteChecks(self.projects, free=True)
        self.addCleanup(self.service.shutdown)
        self.url = 'https://example.test/'

    def discovery(self, *args, **kwargs):
        return {'pages': [asdict(PageSnapshot(self.url, collection_complete=True))], 'limitations': []}

    def test_bare_https_root_admits_discovered_slash_document_checks(self):
        result=lambda case,*a,**k:TestResult(case,TestStatus.PASSED,.01,'Expected condition satisfied.')
        with patch('adaptive_qa.dashboard_worker.discover_configured_target',side_effect=self.discovery), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test',side_effect=result) as run:
            check=self.service.submit(LOCAL_ACTOR,self.url.rstrip('/'));self.service.thread.join(5)
        outcome=self.service.get(LOCAL_ACTOR,check['check_id'])
        self.assertEqual(outcome['status'],'completed',outcome)
        self.assertEqual({r['case_id'] for r in outcome['results']},
                         {'DOC-001','DOC-002','DOC-003','DOC-004','DOC-005'})
        self.assertTrue(all(call.args[1].base_url==self.url for call in run.call_args_list))

    def test_one_click_executes_only_eligible_checks_and_preserves_unrelated_queue(self):
        p = self.projects.create(LOCAL_ACTOR, 'Existing project')
        self.projects.save_configuration(LOCAL_ACTOR, p.project_id, dict(base_url=self.url,
            allowed_hosts=['example.test'], allow_data_changes=False, secret_references={}))
        unrelated = DashboardDiscoveryQueue(self.projects).submit(LOCAL_ACTOR, p.project_id)
        def result(case, *args, **kwargs):
            return TestResult(case, TestStatus.PASSED, .01, 'Expected contract satisfied.')
        with patch('adaptive_qa.dashboard_worker.discover_configured_target', side_effect=self.discovery), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test', side_effect=result):
            check = self.service.submit(LOCAL_ACTOR, self.url)
            self.service.thread.join(5)
        outcome = self.service.get(LOCAL_ACTOR, check['check_id'])
        self.assertEqual(outcome['status'], 'completed', outcome)
        self.assertGreater(len(outcome['results']), 0)
        self.assertLessEqual(outcome['requested'], 10)
        self.assertTrue(all(r['status']=='passed' for r in outcome['results']))
        self.assertFalse({'FORM-001','FORM-002'} & {r['case_id'] for r in outcome['results']})
        self.assertEqual(DashboardDiscoveryQueue(self.projects).get(LOCAL_ACTOR,p.project_id,unrelated['job_id'])['status'],'queued')
        self.assertEqual(len(self.projects.list(LOCAL_ACTOR)),1)
        with self.assertRaises(ProjectNotFound):
            self.service.get(ProjectActor('a'*32), check['check_id'])

    def test_access_failures_are_explicit_and_do_not_start_tests_or_store_raw_text(self):
        for supplied,expected in (('dns_resolution_failed','dns_resolution_failed'),
                ('private-value','inspection_unavailable')):
            payload=dict(pages=[],limitations=[],diagnostic_code=supplied,raw_error='private-canary')
            with patch('adaptive_qa.dashboard_worker.discover_configured_target',return_value=payload), \
                    patch('adaptive_qa.site_check.process_run_once') as runner:
                check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
            outcome=self.service.get(LOCAL_ACTOR,check['check_id'])
            self.assertEqual(outcome['status'],'error');self.assertEqual(outcome['diagnostic_code'],expected)
            self.assertNotIn('results',outcome);runner.assert_not_called()
        self.assertNotIn(b'private-canary',self.projects.database.read_bytes())
        self.assertNotIn(b'private-value',self.projects.database.read_bytes())

    def test_native_email_probes_selected_only_for_observed_saved_page(self):
        def discovery(*args, **kwargs):
            page=PageSnapshot(self.url, forms=(FormSnapshot(fields=(FieldSnapshot('email'),)),), collection_complete=True)
            return {'pages':[asdict(page)],'limitations':[]}
        def result(case,*args,**kwargs):
            return TestResult(case,TestStatus.PASSED,.01,'Expected contract satisfied.')
        with patch('adaptive_qa.dashboard_worker.discover_configured_target',side_effect=discovery), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test',side_effect=result), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_form_test',side_effect=result) as native:
            check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
        outcome=self.service.get(LOCAL_ACTOR,check['check_id'])
        self.assertEqual(outcome['status'],'completed',outcome)
        self.assertEqual({r['case_id'] for r in outcome['results']} & {'FORM-001','FORM-002'},{'FORM-001','FORM-002'})
        self.assertEqual(native.call_count,2)

    def test_number_bounds_selected_without_losing_base_document_checks(self):
        def discovery(*args,**kwargs):
            fields=(FieldSnapshot('email'),FieldSnapshot('password'),FieldSnapshot('number',native_minimum=True,native_maximum=True))
            page=PageSnapshot(self.url,forms=(FormSnapshot(fields=fields,buttons=('Sign in',)),
                FormSnapshot(role='search',fields=(FieldSnapshot('search'),),buttons=('Search',))),collection_complete=True)
            return {'pages':[asdict(page)],'limitations':[]}
        result=lambda case,*args,**kwargs:TestResult(case,TestStatus.PASSED,.01,'Expected contract satisfied.')
        with patch('adaptive_qa.dashboard_worker.discover_configured_target',side_effect=discovery), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test',side_effect=result), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_form_test',side_effect=result):
            check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
        outcome=self.service.get(LOCAL_ACTOR,check['check_id'])
        cases={item['case_id'] for item in outcome['results']}
        self.assertEqual(outcome['status'],'completed',outcome)
        self.assertEqual(len(cases),10)
        self.assertTrue({'FORM-008','FORM-009','DOC-001','DOC-002','DOC-003','DOC-004','DOC-005'}<=cases)

    def test_ambiguous_email_discovery_does_not_auto_admit_native_probes(self):
        def discovery(*args, **kwargs):
            page=PageSnapshot(self.url, forms=(FormSnapshot(fields=(FieldSnapshot('email'),FieldSnapshot('email'))),), collection_complete=True)
            return {'pages':[asdict(page)],'limitations':[]}
        with patch('adaptive_qa.dashboard_worker.discover_configured_target',side_effect=discovery), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test',
                      side_effect=lambda case,*a,**k:TestResult(case,TestStatus.PASSED,.01,'Expected contract satisfied.')), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_form_test') as native:
            check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
        self.assertEqual(self.service.get(LOCAL_ACTOR,check['check_id'])['status'],'completed')
        native.assert_not_called()

    def test_cancel_during_discovery_prevents_test_admission_and_duplicate_threads(self):
        entered, release = Event(), Event()
        def discovery(*args, **kwargs):
            entered.set(); release.wait(3)
            return self.discovery()
        with patch('adaptive_qa.dashboard_worker.discover_configured_target', side_effect=discovery), \
                patch('adaptive_qa.site_check.process_run_once') as run:
            check = self.service.submit(LOCAL_ACTOR, self.url)
            self.assertTrue(entered.wait(2))
            with self.assertRaises(SiteCheckBusy): self.service.submit(LOCAL_ACTOR,self.url)
            self.service.cancel(LOCAL_ACTOR,check['check_id'])
            release.set(); self.service.thread.join(5)
            self.assertEqual(self.service.get(LOCAL_ACTOR,check['check_id'])['status'],'cancelled')
            run.assert_not_called()

    def test_private_invalid_urls_never_create_project_or_target_work(self):
        with patch('socket.getaddrinfo',side_effect=AssertionError('No DNS during admission')), \
                patch('adaptive_qa.site_check.process_discovery_once') as worker:
            for url in ('http://example.test/','https://127.0.0.1/','https://10.0.0.1/',
                        'https://localhost/','https://example.test/?key=private','https://example.test:8443/'):
                with self.assertRaises(ValueError): self.service.submit(LOCAL_ACTOR,url)
            worker.assert_not_called()
        self.assertEqual(self.projects.list(LOCAL_ACTOR),())

    def test_all_execution_errors_are_not_presented_as_completed_success(self):
        with patch('adaptive_qa.dashboard_worker.discover_configured_target',side_effect=self.discovery), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test',
                      side_effect=lambda case,*a,**k:TestResult(case,TestStatus.ERROR,.01,'private diagnostic')):
            check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
        public=self.service.get(LOCAL_ACTOR,check['check_id'])
        self.assertEqual(public['status'],'execution_error')
        self.assertEqual(public['outcome_counts']['passed'],0)
        self.assertEqual(public['outcome_counts']['failed'],0)
        self.assertEqual(public['outcome_counts']['error'],5)
        self.assertEqual(public['diagnostic_code'],'no_reliable_test_outcomes')
        # Display classification must never alter the owner's original records.
        persisted=self.service.runs.get(LOCAL_ACTOR,public['project_id'],public['run_id'])
        self.assertEqual(persisted['status'],'completed')
        self.assertNotIn('private diagnostic',str(public))

    def test_partial_execution_uses_safe_diagnostics_and_remains_distinct_from_failures(self):
        def result(case,*args,**kwargs):
            if case=='DOC-001': return TestResult(case,TestStatus.PASSED,.01,'The source HTML structure check passed; scripts and assets were not evaluated.')
            return TestResult(case,TestStatus.ERROR,.01,'The bound HTML document could not be loaded.')
        with patch('adaptive_qa.dashboard_worker.discover_configured_target',side_effect=self.discovery), \
                patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test',side_effect=result):
            check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
        public=self.service.get(LOCAL_ACTOR,check['check_id'])
        self.assertEqual(public['status'],'partial')
        self.assertEqual(public['outcome_counts']['passed'],1)
        self.assertEqual(public['outcome_counts']['error'],4)
        self.assertEqual(public['outcome_counts']['failed'],0)
        self.assertEqual(public['results'][0]['reason_code'],'source_html_passed')
        self.assertTrue(all(r['reason_code']=='html_document_not_loaded' for r in public['results'][1:]))

    def test_restore_cancels_managed_state_without_replaying_children(self):
        from adaptive_qa.local_backup import create_local_backup, restore_local_backup
        with patch('adaptive_qa.dashboard_worker.discover_configured_target', side_effect=RuntimeError()):
            check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
        self.service._update(check['check_id'],status='testing')
        root=self.projects.database.parent
        create_local_backup(root,root.parent/(root.name+'-backup'),maintenance_confirmed=True)
        restored=root.parent/(root.name+'-restored')
        restore_local_backup(root.parent/(root.name+'-backup'),restored,maintenance_confirmed=True)
        other=SiteChecks(LocalFreeProjects(restored/'projects.sqlite'),free=True)
        with patch('adaptive_qa.site_check.process_discovery_once') as worker:
            self.assertEqual(other.get(LOCAL_ACTOR,check['check_id'])['status'],'cancelled')
            worker.assert_not_called()

    def test_advanced_configuration_is_not_discarded_and_failure_is_not_a_pass(self):
        p=self.projects.create(LOCAL_ACTOR,'Advanced')
        settings=dict(base_url=self.url,allowed_hosts=['example.test'],allow_data_changes=True,secret_references={})
        self.projects.save_configuration(LOCAL_ACTOR,p.project_id,settings)
        with self.assertRaises(ValueError): self.service.submit(LOCAL_ACTOR,self.url)
        self.assertTrue(self.projects.configuration(LOCAL_ACTOR,p.project_id)['allow_data_changes'])
        self.projects.save_configuration(LOCAL_ACTOR,p.project_id,dict(settings,allow_data_changes=False))
        with patch('adaptive_qa.dashboard_worker.discover_configured_target',side_effect=RuntimeError('private-canary')):
            check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
        outcome=self.service.get(LOCAL_ACTOR,check['check_id'])
        self.assertEqual(outcome['status'],'error')
        self.assertNotIn('private-canary',str(outcome))

    def test_restart_history_never_replays_and_http_is_csrf_protected(self):
        with patch('adaptive_qa.dashboard_worker.discover_configured_target', side_effect=RuntimeError()):
            check=self.service.submit(LOCAL_ACTOR,self.url);self.service.thread.join(5)
        self.service._update(check['check_id'], status='discovering')
        restarted=SiteChecks(self.projects,free=True)
        with patch('adaptive_qa.site_check.process_discovery_once') as worker:
            self.assertEqual(restarted.get(LOCAL_ACTOR,check['check_id'])['status'],'interrupted')
            worker.assert_not_called()
        app=create_free_app(self.projects.database,port=8889)
        with TestClient(app,base_url='http://127.0.0.1:8889') as client:
            self.assertEqual(client.post('/api/site-checks',headers={'origin':'http://127.0.0.1:8889'},json={'url':self.url}).status_code,401)
            self.assertTrue(client.get('/api/auth/me').json()['simple_site_checks'])
            self.assertEqual(client.post('/api/site-checks',headers={'origin':'http://127.0.0.1:8889'},json={'url':self.url}).status_code,401)
            headers={'origin':'http://127.0.0.1:8889','x-csrf-token':client.cookies['adaptive_csrf']}
            self.assertEqual(client.post('/api/site-checks',headers=dict(headers,origin='https://foreign.test'),json={'url':self.url}).status_code,403)
            self.assertEqual(client.get('/api/site-checks').json()['checks'][0]['status'],'interrupted')
