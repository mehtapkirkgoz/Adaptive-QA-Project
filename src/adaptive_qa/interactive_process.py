"""Supervise fixed DOM verification probes; no product admission or external submissions."""
import argparse
from contextlib import nullcontext
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from adaptive_qa.browser_process import _terminate_process_tree
from adaptive_qa.config import ProjectConfig
from adaptive_qa.egress import DestinationGuard,EgressProxy,chromium_proxy_options
from adaptive_qa.form_configuration import decode_form_mappings
from adaptive_qa.interactive_contracts import InteractiveFormContract,FormOperation
from adaptive_qa.interactive_fixtures import FIXTURES,fixture_document
from adaptive_qa.interactive_probe import InteractiveProbeResult,probe_controlled_form
from adaptive_qa.models import TestStatus
from adaptive_qa.secrets import SecretReference

MESSAGES = {TestStatus.PASSED:'Controlled form transition verified.',
    TestStatus.FAILED:'Expected controlled form transition was not observed.',
    TestStatus.BLOCKED:'Controlled form preconditions were not satisfied.',
    TestStatus.ERROR:'Controlled form probe could not complete.'}


def _validate(contract,project,fixture_id,fingerprint):
    if not isinstance(contract,InteractiveFormContract) or fixture_id not in FIXTURES:
        raise ValueError('A fixed controlled probe contract is required.')
    contract.validate_project(project,current_fingerprint=fingerprint)
    if contract.operation!=FIXTURES[fixture_id] or project.base_url!='http://127.0.0.1:8000/interactive/'+fixture_id:
        raise ValueError('The fixed fixture binding does not match the contract.')
    if project.allowed_hosts!=('127.0.0.1',): raise ValueError('Only the fixed fixture host is supported.')


def _unique(pairs):
    data={}
    for key,value in pairs:
        if key in data:raise ValueError('Duplicate fields.')
        data[key]=value
    return data


def _decode(raw):
    data=json.loads(raw,object_pairs_hook=_unique)
    if not isinstance(data,dict) or set(data)!={'contract','project','fixture_id','current_fingerprint','fixture_source'}:raise ValueError()
    c,p=data['contract'],data['project']
    if (not isinstance(c,dict) or set(c)!=set(InteractiveFormContract.__dataclass_fields__)
            or not isinstance(p,dict) or set(p)!=set(ProjectConfig.__dataclass_fields__)
            or not isinstance(p['allowed_hosts'],list) or not isinstance(c['inputs'],list)):
        raise ValueError()
    references=[]
    for reference in c['inputs']:
        if not isinstance(reference,dict) or set(reference)!={'environment_variable'}:raise ValueError()
        references.append(SecretReference(**reference))
    completion=decode_form_mappings({'project_id':c['project_id'],'mappings':[c['completion']]}).mappings[0]
    contract=InteractiveFormContract(c['project_id'],c['configuration_fingerprint'],FormOperation(c['operation']),tuple(references),completion,c['timeout_seconds'])
    project=ProjectConfig(**{**p,'allowed_hosts':tuple(p['allowed_hosts'])})
    if data['fixture_source'] not in ('memory','owned_http','owned_submission'):raise ValueError()
    _validate(contract,project,data['fixture_id'],data['current_fingerprint'])
    if data['fixture_source']=='owned_submission':_submission_binding(contract,project,data['fixture_id'],data['current_fingerprint'])
    return contract,project,data['fixture_id'],data['current_fingerprint'],data['fixture_source']


def _read_result(path):
    if path.resolve()!=path or not path.is_file() or path.stat().st_nlink!=1:raise ValueError()
    with path.open('rb') as stream:raw=stream.read(4097)
    if len(raw)>4096:raise ValueError()
    data=json.loads(raw,object_pairs_hook=_unique)
    if not isinstance(data,dict) or set(data)!={'status','message','attempted_submissions'}:raise ValueError()
    result=InteractiveProbeResult(TestStatus(data['status']),data['message'],data['attempted_submissions'])
    if result.status not in MESSAGES or result.message!=MESSAGES[result.status]:raise ValueError()
    if result.status in (TestStatus.PASSED,TestStatus.FAILED) and result.attempted_submissions!=1:raise ValueError()
    return result


def run_isolated_interactive_probe(contract,project,*,fixture_id,current_fingerprint,timeout_seconds=45,should_cancel=None,fixture_source='memory'):
    _validate(contract,project,fixture_id,current_fingerprint)
    if fixture_source not in ('memory','owned_http','owned_submission'):raise ValueError('Unknown controlled fixture source.')
    if fixture_source=='owned_submission':_submission_binding(contract,project,fixture_id,current_fingerprint)
    if (isinstance(timeout_seconds,bool) or not isinstance(timeout_seconds,(int,float))
            or not 0<timeout_seconds<=60 or not math.isfinite(timeout_seconds)
            or (should_cancel is not None and not callable(should_cancel))):
        raise ValueError('A bounded process deadline and trusted cancellation callback are required.')
    def outcome(status,message):return InteractiveProbeResult(status,message,None)
    started=perf_counter()
    try:
        if should_cancel is not None and should_cancel():return outcome(TestStatus.CANCELLED,'Controlled probe was cancelled.')
    except Exception:return outcome(TestStatus.ERROR,'Cancellation source failed.')
    payload=json.dumps(dict(contract=asdict(contract),project=asdict(project),fixture_id=fixture_id,current_fingerprint=current_fingerprint,fixture_source=fixture_source))
    if len(payload.encode())>16384:raise ValueError('Oversized controlled probe configuration.')
    with TemporaryDirectory(prefix='adaptive-interactive-') as temporary:
        # Windows runner TEMP may contain an 8.3 alias or a junction. Canonicalize
        # the directory we own before enforcing exact child transport paths.
        transport=Path(temporary).resolve(strict=True)
        source,output=transport/'input.json',transport/'result.json'
        source.write_text(payload,encoding='utf-8')
        options={'start_new_session':True} if os.name!='nt' else {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW}
        try:
            process=subprocess.Popen([sys.executable,'-m','adaptive_qa.interactive_process','--input',str(source),'--output',str(output)],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**options)
        except OSError:
            return outcome(TestStatus.ERROR,'Controlled probe child could not start.')
        try:
            while True:
                try:
                    if should_cancel is not None and should_cancel():return outcome(TestStatus.CANCELLED,'Controlled probe was cancelled.')
                except Exception:return outcome(TestStatus.ERROR,'Cancellation source failed.')
                remaining=timeout_seconds-(perf_counter()-started)
                if remaining<=0:return outcome(TestStatus.ERROR,'Controlled probe exceeded its process deadline.')
                try:process.wait(timeout=min(.2,remaining));break
                except subprocess.TimeoutExpired:continue
            if process.returncode!=0:return outcome(TestStatus.ERROR,'Controlled probe child exited unexpectedly.')
            try:return _read_result(output)
            except (OSError,ValueError,TypeError,KeyError,RecursionError):return outcome(TestStatus.ERROR,'Controlled probe returned an invalid result.')
        finally:
            if process.poll() is None:_terminate_process_tree(process)


def _submission_binding(contract,project,fixture_id,fingerprint):
    from adaptive_qa.owned_submission import OwnedSubmissionContract,ORIGIN
    fields=('user','password') if contract.operation==FormOperation.LOGIN else ('query',)
    binding=OwnedSubmissionContract(contract,fixture_id,project.base_url,ORIGIN+'/interactive-submit/'+fixture_id,fields)
    binding.validate_project(project,current_fingerprint=fingerprint)
    return binding


def _execute(contract,project,fixture_id,fingerprint,fixture_source):
    from playwright.sync_api import sync_playwright
    denied=[0];armed=[False];submission_results=[];expected_body=[None]
    binding=_submission_binding(contract,project,fixture_id,fingerprint) if fixture_source=='owned_submission' else None
    if binding is not None:
        from adaptive_qa.owned_submission import OwnedSubmissionTransport
        transport=OwnedSubmissionTransport(binding,project,current_fingerprint=fingerprint)
    guard=DestinationGuard(project,local_sample=True,max_requests=1)
    proxy_context=EgressProxy(guard) if fixture_source in ('owned_http','owned_submission') else nullcontext(None)
    with proxy_context as proxy,sync_playwright() as p:
        browser=p.chromium.launch(timeout=10000,**(chromium_proxy_options(proxy.url) if proxy else {}))
        try:
            context=browser.new_context(service_workers='block',accept_downloads=False)
            try:
                consumed=[False]
                def route(request):
                    if (not consumed[0] and request.request.url==project.base_url
                            and request.request.method=='GET' and request.request.is_navigation_request()):
                        consumed[0]=True
                        if fixture_source=='memory':
                            request.fulfill(status=200,content_type='text/html',body=fixture_document(fixture_id,project.base_url))
                        else:request.continue_()
                    elif (binding is not None and armed[0] and request.request.url==binding.endpoint_url
                            and request.request.post_data_buffer==expected_body[0]):
                        result=transport.submit(url=request.request.url,method=request.request.method,
                            content_type=request.request.headers.get('content-type'),body=request.request.post_data_buffer)
                        submission_results.append(result)
                        if result.outcome in ('accepted','rejected'):
                            request.fulfill(status=200 if result.outcome=='accepted' else 401,
                                content_type='application/json',body='{"outcome":"'+result.outcome+'"}')
                        else:denied[0]+=1;request.abort()
                    else:denied[0]+=1;request.abort()
                def websocket(connection):denied[0]+=1;connection.close()
                context.route('**/*',route);context.route_web_socket('**/*',websocket)
                page=context.new_page();page.set_default_timeout(3000)
                response=page.goto(project.base_url,wait_until='domcontentloaded',timeout=10000)
                if (response is None or response.status!=200 or page.url!=project.base_url
                        or 'text/html' not in response.headers.get('content-type','').lower()
                        or (fixture_source in ('owned_http','owned_submission') and guard.requests!=1)):raise ValueError()
                def arm(values):
                    from urllib.parse import urlencode
                    expected_body[0]=urlencode(tuple(zip(binding.field_names,values,strict=True))).encode('ascii')
                    armed[0]=True
                result=probe_controlled_form(page,contract,project,current_fingerprint=fingerprint,
                    network_clean=lambda:denied[0]==0 and guard.denied==0,submission=binding,
                    before_submit=arm if binding is not None else None)
                if binding is not None and result.attempted_submissions==1:
                    expected='rejected' if fixture_id in ('login-rejected','search-empty') else 'accepted'
                    if len(submission_results)!=1 or submission_results[0].outcome!=expected:
                        count=None if any(item.attempted_submissions is None for item in submission_results) else int(any(item.attempted_submissions==1 for item in submission_results))
                        return InteractiveProbeResult(TestStatus.ERROR,MESSAGES[TestStatus.ERROR],count)
                return result
            finally:context.close()
        finally:browser.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if (args.input.resolve()!=args.input or not args.input.is_file() or args.input.stat().st_nlink!=1
            or args.output.parent!=args.input.parent or args.output.exists() or args.output.is_symlink()):raise ValueError('Invalid private transport files.')
    with args.input.open('rb') as stream:raw=stream.read(16385)
    if len(raw)>16384:raise ValueError('Oversized controlled probe configuration.')
    contract,project,fixture_id,fingerprint,fixture_source=_decode(raw)
    try:result=_execute(contract,project,fixture_id,fingerprint,fixture_source)
    except Exception:result=InteractiveProbeResult(TestStatus.ERROR,MESSAGES[TestStatus.ERROR],None)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(asdict(result),stream)


if __name__=='__main__':main()
