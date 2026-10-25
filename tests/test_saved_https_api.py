"""Explicit HTTPS settings, guarded admission and recovery never infer authority."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient
from adaptive_qa.api_queue import LocalApiQueue, process_local_api_once
from adaptive_qa.local_backup import create_local_backup, restore_local_backup
from adaptive_qa.local_free import create_free_app, LocalFreeProjects, LOCAL_ACTOR
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.project_store import ProjectActor, ProjectNotFound
from adaptive_qa.saved_api_review import review_saved_api


class SavedHttpsApiTests(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/'workspace';self.root.mkdir()
        self.projects=LocalFreeProjects(self.root/'projects.sqlite')
        self.pid=self.projects.create(LOCAL_ACTOR,'Explicit HTTPS target').project_id
        self.binding=dict(profile='public_https',path='/service/ready',expected_status=200,
                          json_field='ready',expected_boolean=True)
        self.settings=dict(base_url='https://api.example.test',allowed_hosts=['api.example.test'],
                           allow_data_changes=False,secret_references={},local_api_binding=self.binding)

    def test_save_review_are_offline_and_profile_must_be_explicit(self):
        with patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')), \
                patch('adaptive_qa.secrets.SecretReference.resolve',side_effect=AssertionError('No secrets')):
            self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
            public=review_saved_api(self.projects,LOCAL_ACTOR,self.pid)
        self.assertEqual(public['execution_profile'],'public_https')
        self.assertEqual(public['scope'],'public_https_read_only')
        self.assertFalse(public['execution_authorized'])
        binding={key:value for key,value in self.binding.items() if key!='profile'}
        for bad in (binding,dict(self.binding,profile='controlled_local'),dict(self.binding,verify_tls=False),
                    dict(self.binding,path='//other.test'),dict(self.binding,path='/ready?token=value')):
            with self.assertRaises(ValueError):
                self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_api_binding=bad))
        self.assertEqual(self.projects.configuration(LOCAL_ACTOR,self.pid)['local_api_binding'],self.binding)

    def test_http_review_confirmation_and_cancellation_are_scoped_and_nonexecuting(self):
        app=create_free_app(self.projects.database,port=8889)
        with TestClient(app,base_url='http://127.0.0.1:8889') as client, \
                patch('socket.getaddrinfo',side_effect=AssertionError('No target DNS')), \
                patch('adaptive_qa.api_process.run_isolated_api_case') as child:
            client.get('/api/auth/me')
            headers={'origin':'http://127.0.0.1:8889','x-csrf-token':client.cookies['adaptive_csrf']}
            base=f'/api/projects/{self.pid}'
            initial=client.get(base+'/configuration').json()
            self.assertIn('public_https',initial['api_binding_profiles'])
            self.assertEqual(client.put(base+'/configuration',headers=headers,json=self.settings).status_code,200)
            review=client.post(base+'/local-api/review',headers=headers,json={}).json()
            body=dict(confirmed_contract_fingerprint=review['contract_fingerprint'])
            self.assertEqual(client.post(base+'/local-api/jobs',headers={'origin':headers['origin']},json=body).status_code,401)
            self.assertEqual(client.post(base+'/local-api/jobs',headers=dict(headers,origin='https://foreign.test'),json=body).status_code,403)
            response=client.post(base+'/local-api/jobs',headers=headers,json=body)
            self.assertEqual(response.status_code,202,response.text)
            job=response.json()
            self.assertEqual(job['scope'],'explicit_saved_api')
            self.assertEqual(client.post(base+'/local-api/jobs/'+job['job_id']+'/cancel',headers=headers,json={}).json()['status'],'cancelled')
            self.assertEqual(len(client.get(base+'/local-api/jobs').json()['jobs']),1)
            child.assert_not_called()

    def test_worker_retains_public_profile_and_stale_settings_do_not_dispatch(self):
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
        queue=LocalApiQueue(self.projects)
        digest=review_saved_api(self.projects,LOCAL_ACTOR,self.pid)['contract_fingerprint']
        job=queue.submit(LOCAL_ACTOR,self.pid,digest)
        with self.assertRaises(ProjectNotFound):queue.get(ProjectActor('b'*32),self.pid,job['job_id'])
        with patch('adaptive_qa.api_queue.run_reviewed_local_api',return_value=TestResult('LOCAL-API-READ',TestStatus.PASSED,0,'private response')) as execute:
            self.assertEqual(process_local_api_once(queue)['status'],'completed')
        self.assertEqual(execute.call_args.args[0].profile,'public_https')
        self.assertEqual(queue.get(LOCAL_ACTOR,self.pid,job['job_id'])['result'],{'status':'passed'})
        queue.submit(LOCAL_ACTOR,self.pid,digest)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,dict(self.settings,local_api_binding=dict(self.binding,path='/changed')))
        with patch('adaptive_qa.api_queue.run_reviewed_local_api') as execute:
            self.assertIsNone(process_local_api_once(queue));execute.assert_not_called()
        with self.assertRaises(ValueError):queue.submit(LOCAL_ACTOR,self.pid,digest)

    def test_offline_restore_preserves_profile_and_cancels_queued_work(self):
        from adaptive_qa.dashboard_runs import DashboardRunQueue
        DashboardRunQueue(self.projects)
        self.projects.save_configuration(LOCAL_ACTOR,self.pid,self.settings)
        queue=LocalApiQueue(self.projects)
        job=queue.submit(LOCAL_ACTOR,self.pid,review_saved_api(self.projects,LOCAL_ACTOR,self.pid)['contract_fingerprint'])
        snapshot=self.root.parent/'snapshot';restored=self.root.parent/'restored'
        create_local_backup(self.root,snapshot,maintenance_confirmed=True)
        restore_local_backup(snapshot,restored,maintenance_confirmed=True)
        projects=LocalFreeProjects(restored/'projects.sqlite')
        self.assertEqual(projects.configuration(LOCAL_ACTOR,self.pid)['local_api_binding'],self.binding)
        self.assertEqual(LocalApiQueue(projects).get(LOCAL_ACTOR,self.pid,job['job_id'])['status'],'cancelled')


if __name__=='__main__':unittest.main()
