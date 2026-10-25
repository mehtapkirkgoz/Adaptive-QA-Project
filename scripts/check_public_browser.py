"""Real supervised browser/TLS proof against an owned server; no Internet target."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import serialization

ROOT=Path(__file__).resolve().parents[1]
INSTALLED=os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if INSTALLED:sys.path.insert(0,str(Path(INSTALLED).resolve(strict=True)))
import adaptive_qa
if INSTALLED:
    assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(INSTALLED).resolve())
    child=subprocess.check_output([sys.executable,'-c','import adaptive_qa;print(adaptive_qa.__file__)'],text=True).strip()
    assert Path(child).resolve().is_relative_to(Path(INSTALLED).resolve())
sys.path.insert(0,str(ROOT/'tests'))
import test_public_submission as tls_fixture
from check_public_form_probe import document
from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation,InteractiveFormContract
from adaptive_qa.local_form_binding import LocalBooleanResponse
from adaptive_qa.models import TestStatus
from adaptive_qa.project_settings import reference_name
from adaptive_qa.public_browser_process import run_isolated_public_browser
import adaptive_qa.public_browser_process as browser_module
from adaptive_qa.public_form_proposal import PublicFormProposal
from adaptive_qa.public_submission import ReviewedPublicForm
from adaptive_qa.secrets import SecretReference


def main(quick=False,queued=False):
    holder=unittest.TestCase()
    _,_,server=tls_fixture.PublicSubmissionTests.tls_harness(holder)
    cert=x509.load_pem_x509_certificate(Path(server['ca_path']).read_bytes())
    der=cert.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    pin=base64.b64encode(hashlib.sha256(der).digest()).decode()
    owner,pid='c'*32,'a'*32
    if queued:
        from tempfile import TemporaryDirectory
        from adaptive_qa.project_store import ProjectStore,ProjectActor
        from adaptive_qa.interactive_queue import OwnedInteractiveQueue,process_owned_interactive_once
        from adaptive_qa.public_form_review import review_saved_public_form
        from adaptive_qa.public_form_proposal import encode_public_proposal
        workspace=TemporaryDirectory(prefix='adaptive-owned-queue-proof-');holder.addCleanup(workspace.cleanup)
        projects=ProjectStore(Path(workspace.name)/'projects.sqlite');actor=ProjectActor(owner)
        pid=projects.create(actor,'Owned TLS queue proof').project_id
        queue=OwnedInteractiveQueue(projects)
    cases=(
        ('search-positive','normal',FormOperation.SEARCH,TestStatus.PASSED,1,1),
        ('login-positive','normal',FormOperation.LOGIN,TestStatus.PASSED,2,1),
        ('search-negative','negative',FormOperation.SEARCH,TestStatus.PASSED,1,1),
        ('same-origin-asset','asset',FormOperation.SEARCH,TestStatus.PASSED,1,1),
        ('preexisting','preexisting',FormOperation.SEARCH,TestStatus.BLOCKED,0,0),
        ('wrong-action','wrong-action',FormOperation.SEARCH,TestStatus.BLOCKED,0,0),
        ('marker-only','marker-only',FormOperation.SEARCH,TestStatus.FAILED,1,0),
        ('missing-marker','missing-marker',FormOperation.SEARCH,TestStatus.FAILED,1,1),
        ('contradictory-response','contradictory-response',FormOperation.SEARCH,TestStatus.FAILED,1,1),
        ('canary','canary',FormOperation.SEARCH,TestStatus.ERROR,1,0),
        ('changed-body','changed-body',FormOperation.SEARCH,TestStatus.ERROR,1,0),
        ('duplicate-post','duplicate-post',FormOperation.SEARCH,TestStatus.ERROR,1,1),
        ('private-dns','private',FormOperation.SEARCH,TestStatus.ERROR,0,0),
        ('untrusted-browser-tls','untrusted',FormOperation.SEARCH,TestStatus.ERROR,0,0),
        ('document-redirect','redirect',FormOperation.SEARCH,TestStatus.ERROR,0,0),
        ('missing-input','missing',FormOperation.SEARCH,TestStatus.BLOCKED,1,0),
        ('slow-tls','slow',FormOperation.SEARCH,TestStatus.ERROR,None,1),
    )
    if queued:cases=tuple(cases[index] for index in (0,1,2,11,15))
    if quick:cases=cases[:1]
    records=[]
    original_popen=subprocess.Popen
    original_reader=browser_module._read_result
    try:
        for name,mode,operation,expected,references_expected,posts_expected in cases:
            slots=('login_username','login_password') if operation==FormOperation.LOGIN else ('search_query',)
            refs=tuple(SecretReference(reference_name(owner,pid,slot)) for slot in slots)
            negative=mode=='negative'
            logical=('login.rejected' if negative else 'login.accepted') if operation==FormOperation.LOGIN else ('search.empty' if negative else 'search.results')
            form=InteractiveFormContract(pid,'b'*64,operation,refs,
                ElementMapping(logical,(LocatorSpec(LocatorStrategy.TEST_ID,'rejected' if negative else 'accepted'),)),30 if mode=='slow' else 5)
            key='authenticated' if operation==FormOperation.LOGIN else 'found'
            fields=('account','password') if operation==FormOperation.LOGIN else ('query',)
            proposal=PublicFormProposal(form,'https://qa.example.test/search','https://qa.example.test/search/execute',fields,
                LocalBooleanResponse(200,key,True),LocalBooleanResponse(404,key,False))
            review=ReviewedPublicForm(proposal,proposal.fingerprint())
            project=ProjectConfig(pid,'Owned supervised browser proof',proposal.document_url,('qa.example.test',),True)
            if queued:
                settings=dict(base_url=proposal.document_url,allowed_hosts=['qa.example.test'],allow_data_changes=True,
                    secret_references={slot:reference_name(owner,pid,slot) for slot in slots},
                    local_form_binding=dict(profile='public_https',operation=operation.value,
                        **json.loads(json.dumps(encode_public_proposal(proposal)))))
                projects.save_configuration(actor,pid,settings)
                saved=review_saved_public_form(projects,actor,pid,completion=form.completion,timeout_seconds=form.timeout_seconds)
                job=queue.submit_public(actor,saved,confirmed_fingerprint=saved.submission.fingerprint())
                assert job['scope']=='reviewed_public_https' and len(server['contacts'])==sum(r['owned_tls_posts'] for r in records)
            raw=document(operation,mode)
            assets={}
            if mode=='asset':
                script=raw.split('<script>',1)[1].split('</script>',1)[0]
                raw=raw.replace('<script>'+script+'</script>','<script src="/app.js"></script>')
                assets['/app.js']=('application/javascript',script.encode())
            response_negative=negative or mode=='contradictory-response'
            server.update(status=404 if response_negative else 200,body=json.dumps({key:not response_negative}).encode(),headers={},
                drop=False,slow=mode=='slow',document=raw.encode('utf-8'),assets=assets,
                document_status=302 if mode=='redirect' else 200,
                document_headers={'Location':'https://127.0.0.1/private'} if mode=='redirect' else {})
            before_posts=len(server['contacts']);before_documents=len(server.get('documents',[]))
            metrics=[];roots=[]
            wrapper=f'''import sys,socket,ssl,json
from pathlib import Path
import adaptive_qa.egress as egress
from adaptive_qa.egress import DestinationGuard
from adaptive_qa.secrets import SecretReference
import adaptive_qa.public_browser_process as worker
original_context=ssl.create_default_context
original_options=worker.chromium_proxy_options
original_resolve=SecretReference.resolve
reads=[0]
def resolve(host,port):return {('127.0.0.1',) if mode=='private' else ('93.184.216.34',)!r}
def connect(guard,target,**kwargs):
    assert not guard.local_sample and target.hostname=='qa.example.test' and target.port==443
    assert target.addresses==('93.184.216.34',)
    return socket.create_connection(('127.0.0.1',{server['port']}),timeout=2)
def options(url):
    result=original_options(url)
    assert not any('ignore-certificate' in arg for arg in result.get('args',[]))
    if {mode!='untrusted'!r}:
        result['args']=[*result['args'],'--ignore-certificate-errors-spki-list={pin}']
    return result
def secret(reference):
    reads[0]+=1
    return original_resolve(reference)
egress.resolve_with_deadline=resolve
DestinationGuard.connect=connect
ssl.create_default_context=lambda:original_context(cafile={server['ca_path']!r})
worker.chromium_proxy_options=options
SecretReference.resolve=secret
sys.argv=['owned-browser-proof']+sys.argv[1:]
source=Path(sys.argv[sys.argv.index('--input')+1])
worker.main()
(source.parent/'proof-metrics.json').write_text(json.dumps({{'input_references_attempted':reads[0]}}))
'''
            def spawn(command,**options):
                if 'adaptive_qa.public_browser_process' not in command:return original_popen(command,**options)
                assert 'OWNED_PUBLIC_BROWSER_CANARY' not in ' '.join(command)
                source=Path(command[command.index('--input')+1])
                assert 'OWNED_PUBLIC_BROWSER_CANARY' not in source.read_text(encoding='utf-8')
                assert 'SSLKEYLOGFILE' not in options['env']
                roots.append(source.parent)
                return original_popen([sys.executable,'-c',wrapper,*command[3:]],**options)
            def reader(path):
                metrics.append(json.loads((path.parent/'proof-metrics.json').read_text(encoding='utf-8')))
                return original_reader(path)
            with patch.dict(os.environ,{ref.environment_variable:'OWNED_PUBLIC_BROWSER_CANARY' for ref in refs}):
                if mode=='missing':os.environ.pop(refs[0].environment_variable)
                with patch('adaptive_qa.public_submission_process.subprocess.Popen',side_effect=spawn), \
                        patch.object(browser_module,'_read_result',side_effect=reader):
                    if queued:
                        captured=[]
                        def dispatch(*args,**kwargs):
                            outcome=run_isolated_public_browser(*args,**kwargs);captured.append(outcome);return outcome
                        with patch.object(browser_module,'run_isolated_public_browser',side_effect=dispatch):
                            finished=process_owned_interactive_once(queue)
                        assert finished['status']=='completed' and len(captured)==1
                        result=captured[0]
                        persisted=queue.get(actor,pid,job['job_id'])['result']
                        assert persisted==dict(status=result.status.value,attempted_submissions=result.attempted_submissions)
                        assert 'OWNED_PUBLIC_BROWSER_CANARY' not in projects.database.read_bytes().decode('utf-8',errors='ignore')
                    else:
                        result=run_isolated_public_browser(review,project,owner_id=owner,current_fingerprint='b'*64,
                            timeout_seconds=6 if mode=='slow' else 30)
            assert result.status==expected,(name,result)
            posts=len(server['contacts'])-before_posts
            documents=len(server.get('documents',[]))-before_documents
            assert posts==posts_expected,(name,posts,result)
            if references_expected is not None:
                assert len(metrics)==1,(name,result)
                assert metrics[0]['input_references_attempted']==references_expected,(name,metrics)
            else:assert result.attempted_submissions is None,(name,result)
            assert len(roots)==1 and all(not root.exists() for root in roots),(name,'Private profile was not removed')
            assert 'OWNED_PUBLIC_BROWSER_CANARY' not in repr(result)
            if expected==TestStatus.PASSED:assert result.attempted_submissions==1
            if mode=='duplicate-post':assert result.attempted_submissions==1
            if mode=='asset':assert '/app.js' in server['documents'][before_documents:]
            if mode in ('private','untrusted'):assert documents==0
            records.append(dict(scenario=name,status=result.status.value,attempted_submissions=result.attempted_submissions,
                input_references_attempted=metrics[0]['input_references_attempted'] if metrics else None,
                owned_tls_posts=posts,owned_tls_document_requests=documents,private_profile_removed=True))
    finally:holder.doCleanups()
    report=dict(scenarios=records,installed_wheel=bool(INSTALLED),supervised_child_package_verified=bool(INSTALLED),
        actual_owned_tls_documents=True,actual_owned_tls_posts=True,supervised_browser_worker=True,
        test_connector_only=True,browser_test_certificate_pin='ephemeral_owned_spki_only',
        production_tls_override_exposed=False,queue_or_ui_admission_enabled=False,
        public_customer_targets_contacted=False,raw_inputs_in_report=False,screenshots_or_traces_taken=False,
        private_profiles_removed=True,quick=quick,owned_fixture_queue_verified=queued)
    output=Path('artifacts/public-submission');output.mkdir(parents=True,exist_ok=True)
    (output/('browser-queue.json' if queued else 'browser-process-quick.json' if quick else 'browser-process.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(scenarios=len(records),statuses=[r['status'] for r in records],owned_posts=sum(r['owned_tls_posts'] for r in records))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--quick',action='store_true');parser.add_argument('--queue',action='store_true')
    args=parser.parse_args();main(args.quick,args.queue)
