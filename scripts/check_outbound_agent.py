"""Real signed loopback coordinator and separate outbound-only agent process."""

from functools import partial
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic,sleep

import uvicorn
from adaptive_qa.auth_store import AuthStore
from adaptive_qa.project_store import ProjectStore
from adaptive_qa.organization_store import OrganizationStore
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
from adaptive_qa.organization_runs import OrganizationRunQueue
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.agent_registry import AgentRegistry
from adaptive_qa.agent_broker import AgentBroker
from adaptive_qa.agent_transport import create_agent_coordinator,AgentClient,AgentTransportError
from adaptive_qa.dashboard_evidence import validate_png
from adaptive_qa.browser_process import _terminate_process_tree
from check_dashboard_runs import QuietHandler


def main():
    hits = []
    class Canary(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self): hits.append('unexpected_proxy_contact'); self.send_response(500); self.end_headers()
        do_POST = do_GET
    fixture = ThreadingHTTPServer(('127.0.0.1',8000),partial(QuietHandler,directory='samples/web'))
    canary = ThreadingHTTPServer(('127.0.0.1',8001),Canary)
    threads = [Thread(target=server.serve_forever,daemon=True) for server in (fixture,canary)]
    for thread in threads: thread.start()
    try:
        with TemporaryDirectory(prefix='adaptive-outbound-pilot-') as temporary:
            root = Path(temporary)
            auth = AuthStore(root/'auth.sqlite')
            owner = auth.create_user('pilot@example.test','Disposable pilot password 123!')
            other = auth.create_user('other@example.test','Disposable other password 123!')
            projects = ProjectStore(root/'projects.sqlite')
            organizations = OrganizationStore(projects)
            scoped = OrganizationProjects(organizations)
            discovery = OrganizationDiscoveryQueue(scoped)
            runs = OrganizationRunQueue(discovery)
            organization = organizations.create(owner,'Controlled agent pilot')
            project = scoped.create(owner,organization,'Private local fixture')['project_id']
            settings = {'base_url':'http://127.0.0.1:8000/','allowed_hosts':['127.0.0.1'],
                        'allow_data_changes':False,'secret_references':{}}
            scoped.save_configuration(owner,organization,project,settings)
            job = discovery.submit(owner,organization,project)['job_id']
            assert process_discovery_once(discovery)['status']=='completed'
            run = runs.submit(owner,organization,project,job,('LOGIN-001','SEARCH-001'))
            registry = AgentRegistry(scoped)
            grant = registry.issue(owner,organization,project)
            broker = AgentBroker(registry,runs)
            other_org = organizations.create(other,'Other organization')
            other_project = scoped.create(other,other_org,'Other fixture')['project_id']
            scoped.save_configuration(other,other_org,other_project,settings)
            other_grant = registry.issue(other,other_org,other_project)
            app = create_agent_coordinator(broker,port=8871)
            audited = []
            async def audit(scope,receive,send):
                if scope['type']=='http':
                    headers = b'\n'.join(k+b':'+v for k,v in scope['headers'])
                    assert grant.token.value.encode() not in headers
                    assert not any(k.lower() in (b'authorization',b'cookie',b'origin') for k,_ in scope['headers'])
                    audited.append(scope['path'])
                await app(scope,receive,send)
            server = uvicorn.Server(uvicorn.Config(audit,host='127.0.0.1',port=8871,
                proxy_headers=False,access_log=False,log_level='critical',limit_concurrency=16,timeout_keep_alive=5))
            server_thread = Thread(target=server.run,daemon=True)
            server_thread.start()
            process = None
            try:
                deadline = monotonic()+10
                while not server.started:
                    if not server_thread.is_alive() or monotonic()>deadline: raise AssertionError('Coordinator did not start.')
                    sleep(.05)
                other_client = AgentClient('http://127.0.0.1:8871',other_grant.agent_id,other_grant.token)
                assert other_client.call('/agent/poll',{})=={'work':None}
                assert runs.get(owner,organization,project,run['run_id'])['status']=='queued'
                environment = dict(os.environ,ADAPTIVE_QA_AGENT_TOKEN=grant.token.value,
                    HTTP_PROXY='http://127.0.0.1:8001',HTTPS_PROXY='http://127.0.0.1:8001',ALL_PROXY='http://127.0.0.1:8001')
                flags = {'start_new_session':True} if os.name!='nt' else {
                    'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW}
                process = subprocess.Popen([sys.executable,'-m','adaptive_qa.agent_worker',
                    '--coordinator','http://127.0.0.1:8871','--agent-id',grant.agent_id],
                    env=environment,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,**flags)
                output,_ = process.communicate(timeout=160)
                assert grant.token.value.encode() not in output
                assert process.returncode==0 and json.loads(output)=={'status':'completed','cases_reported':2}
                saved = runs.get(owner,organization,project,run['run_id'])
                assert saved['status']=='completed' and len(saved['results'])==2
                for result in saved['results']:
                    assert result['status']=='passed' and result.get('evidence_id')
                    validate_png(runs.evidence(owner,organization,project,run['run_id'],result['evidence_id']))
                try:
                    AgentClient('http://127.0.0.1:8871',grant.agent_id,grant.token).call('/agent/poll',{})
                except AgentTransportError:
                    pass
                else:
                    raise AssertionError('Replayed sequence was accepted.')
                assert not hits and len(audited)>=6
                with projects._connection() as c:
                    assert c.execute("SELECT count(*) FROM dashboard_agent_leases WHERE status='active'").fetchone()[0]==0
                assert runs.admission.usage(owner,organization)['active_runs']==0
            finally:
                if process is not None and process.poll() is None: _terminate_process_tree(process)
                server.should_exit = True
                server_thread.join(timeout=10)
                assert not server_thread.is_alive()
    finally:
        for server in (fixture,canary): server.shutdown(); server.server_close()
        for thread in threads: thread.join(timeout=5)
    report = {'controlled_local_pilot':True,'separate_agent_process':True,'agent_service_listener':False,
              'authenticated_outbound_http':True,'request_and_response_signatures':True,
              'raw_token_not_transmitted_or_logged':True,'foreign_agent_cannot_claim':True,
              'replayed_sequence_denied':True,'real_passed_cases':2,'validated_pngs':2,
              'proxy_canary_contacts':len(hits),'active_leases_remaining':0,'active_capacity_released':True,
              'customer_network_or_public_backend':False}
    output = Path('artifacts/organizations/agent-pilot.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()
