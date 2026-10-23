"""One outbound-only controlled pilot job; no listener or arbitrary commands."""

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic

from adaptive_qa.agent_broker import PILOT_CASES
from adaptive_qa.agent_transport import AgentClient
from adaptive_qa.browser_process import run_isolated_sample_test,_terminate_process_tree
from adaptive_qa.dashboard_evidence import import_screenshot
from adaptive_qa.models import TestResult,TestStatus
from adaptive_qa.project_store import _id
from adaptive_qa.secrets import SecretReference


def run_once(client):
    response = client.call('/agent/poll',{})
    if set(response)!={'work'}:
        raise ValueError('Invalid coordinator response.')
    work = response['work']
    if work is None:
        return {'status':'idle','cases_reported':0}
    if not isinstance(work,dict) or set(work)!={'lease_id','run_id','case_ids','configuration','lease_seconds'}:
        raise ValueError('Invalid coordinator work.')
    _id(work['lease_id']); _id(work['run_id'])
    cases = work['case_ids']
    if (not isinstance(cases,list) or not 1<=len(cases)<=2
            or any(not isinstance(case,str) for case in cases) or len(set(cases))!=len(cases)
            or not set(cases)<=PILOT_CASES or type(work['lease_seconds']) is not int or work['lease_seconds']!=120):
        raise ValueError('Unsupported agent case selection.')
    if (not isinstance(work['configuration'],dict) or work['configuration'].get('allow_data_changes') is not False
            or work['configuration'] not in (
        {'base_url':'http://127.0.0.1:8000/','allowed_hosts':['127.0.0.1'],'allow_data_changes':False},
        {'base_url':'http://127.0.0.1:8000','allowed_hosts':['127.0.0.1'],'allow_data_changes':False})):
        raise ValueError('Unsupported agent target/policy.')
    lease = work['lease_id']
    deadline,reported = monotonic()+110,0
    def cancelled():
        if monotonic()>=deadline:
            return True
        status = client.call('/agent/check',{'lease_id':lease})
        if set(status)!={'cancel_requested'} or type(status['cancel_requested']) is not bool:
            raise ValueError('Invalid coordinator cancellation response.')
        return status['cancel_requested']
    with TemporaryDirectory(prefix='adaptive-outbound-evidence-') as temporary:
        root = Path(temporary).resolve(strict=True)
        for case in cases:
            if cancelled():
                break
            result = run_isolated_sample_test(case,timeout_seconds=min(30,deadline-monotonic()),
                should_cancel=cancelled,site='root',evidence_directory=root)
            if not isinstance(result,TestResult) or result.case_id!=case:
                raise ValueError('Invalid isolated agent outcome.')
            if result.status==TestStatus.CANCELLED or cancelled():
                break
            png = import_screenshot(result.evidence_paths,root=root)
            if png is not None and len(png)>256*1024:
                png = None # Optional evidence is omitted, never truncated or fabricated.
            accepted = client.call('/agent/result',{'lease_id':lease,'case_id':case,
                'status':result.status.value,'duration_seconds':result.duration_seconds,
                'png_base64':None if png is None else base64.b64encode(png).decode('ascii')})
            if accepted!={'accepted':True}:
                break
            reported+=1
    terminal = client.call('/agent/finish',{'lease_id':lease,'failed':reported!=len(cases)})
    if set(terminal)!={'status'} or terminal['status'] not in ('completed','cancelled','error'):
        raise ValueError('Invalid coordinator terminal response.')
    return {'status':terminal['status'],'cases_reported':reported}


def main():
    parser = argparse.ArgumentParser(description='Run one controlled outbound-only local agent job.')
    parser.add_argument('--coordinator',required=True)
    parser.add_argument('--agent-id',required=True)
    parser.add_argument('--token-environment',default='ADAPTIVE_QA_AGENT_TOKEN')
    parser.add_argument('--sequence-start',type=int,default=1)
    parser.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args()
    # Validate references/destination before spawning, without exposing the credential.
    token = SecretReference(args.token_environment).resolve()
    client = AgentClient(args.coordinator,args.agent_id,token,sequence_start=args.sequence_start)
    if args.child:
        os.environ.pop(args.token_environment,None) # Browser descendants do not inherit the agent bearer.
        report = run_once(client)
        print(json.dumps(report))
        return 0 if report['status'] in ('completed','idle') else 2
    flags = {'start_new_session':True} if os.name!='nt' else {
        'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW}
    process = subprocess.Popen([sys.executable,'-m','adaptive_qa.agent_worker','--child',
        '--coordinator',args.coordinator,'--agent-id',args.agent_id,'--token-environment',args.token_environment,
        '--sequence-start',str(args.sequence_start)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,**flags)
    try:
        output,_ = process.communicate(timeout=150)
        if process.returncode!=0 or len(output)>1024:
            raise ValueError('Agent process did not complete.')
        report = json.loads(output)
        if set(report)!={'status','cases_reported'} or report['status'] not in ('completed','idle'):
            raise ValueError('Invalid agent completion report.')
        print(json.dumps(report))
        return 0
    finally:
        if process.poll() is None:
            _terminate_process_tree(process)


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({'status':'error','message':'Controlled agent execution stopped.'}))
        raise SystemExit(2)
