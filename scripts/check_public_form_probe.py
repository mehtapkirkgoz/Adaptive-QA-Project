"""Owned in-memory documents plus actual owned TLS POSTs; no Internet document is loaded."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
INSTALLED = os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if INSTALLED:
    sys.path.insert(0, str(Path(INSTALLED).resolve(strict=True)))
import adaptive_qa
if INSTALLED:
    assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(INSTALLED).resolve())
sys.path.insert(0, str(ROOT/'tests'))
import test_public_submission as tls_fixture

from playwright.sync_api import sync_playwright
from adaptive_qa.config import ProjectConfig
from adaptive_qa.egress import DestinationGuard
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.local_form_binding import LocalBooleanResponse
from adaptive_qa.models import TestStatus
from adaptive_qa.owned_submission import CONTENT_TYPE
from adaptive_qa.project_settings import reference_name
from adaptive_qa.public_form_probe import probe_reviewed_public_form
from adaptive_qa.public_form_proposal import PublicFormProposal
from adaptive_qa.public_submission import ReviewedPublicForm, PublicSubmissionTransport
from adaptive_qa.secrets import SecretReference


def document(operation, mode):
    login = operation == FormOperation.LOGIN
    inputs = ('<label>Kullanıcı adı<input name="account"></label><label>Şifre<input type="password" name="password"></label>'
              if login else '<label>Search products<input type="search" name="query"></label>')
    button = 'Giriş yap' if login else 'Search'
    key = 'authenticated' if login else 'found'
    raw = f'''<html lang="en"><meta charset="utf-8"><title>Owned functional fixture</title><form id="operation" method="post"
        action="https://qa.example.test/search/execute">{inputs}<button>{button}</button></form>
        <p data-testid="accepted" hidden>Accepted</p><p data-testid="rejected" hidden>Rejected</p>
        <script>const form=document.getElementById('operation');
        const accepted=document.querySelector('[data-testid=accepted]');
        const rejected=document.querySelector('[data-testid=rejected]');
        form.addEventListener('submit',async event=>{{event.preventDefault();try{{
            const response=await fetch(form.action,{{method:'POST',headers:{{'Content-Type':'{CONTENT_TYPE}'}},body:new URLSearchParams(new FormData(form))}});
            const value=await response.json();
            if(value.{key}===true) accepted.hidden=false;
            if(value.{key}===false) rejected.hidden=false;
        }}catch{{}}}});</script></html>'''
    if mode == 'preexisting': raw = raw.replace('data-testid="accepted" hidden', 'data-testid="accepted"')
    if mode == 'wrong-action': raw = raw.replace('action="https://qa.example.test/search/execute"','action="https://other.example.test/submit"')
    if mode == 'wrong-fields': raw = raw.replace('name="query"','name="unknown"')
    if mode == 'unmasked': raw = raw.replace('type="password"','type="text"')
    if mode == 'ambiguous': raw = raw.replace('</button>', f'</button><button>{button}</button>', 1)
    if mode == 'missing-marker': raw = raw.replace('accepted.hidden=false', 'accepted.hidden=true')
    if mode == 'marker-only':
        raw = raw.replace("const response=await fetch", "accepted.hidden=false;return;const response=await fetch")
    if mode == 'input-marker':
        raw = raw.replace('</script>', "form.querySelector('input').addEventListener('input',()=>accepted.hidden=false);</script>")
    if mode == 'mutated-action':
        raw = raw.replace('</script>', "form.querySelector('input').addEventListener('input',()=>form.action='https://other.example.test/submit');</script>")
    if mode == 'canary':
        raw = raw.replace('</script>', "form.querySelector('input').addEventListener('input',()=>fetch('https://other.example.test/canary').catch(()=>{}));</script>")
    if mode == 'changed-body':
        raw = raw.replace('body:new URLSearchParams(new FormData(form))', "body:'query=changed'")
    if mode == 'duplicate-post':
        raw = raw.replace('const value=await response.json();',
            f"await fetch(form.action,{{method:'POST',headers:{{'Content-Type':'{CONTENT_TYPE}'}},body:new URLSearchParams(new FormData(form))}});const value=await response.json();")
    if mode == 'contradictory-response':
        raw = raw.replace(f'if(value.{key}===true) accepted.hidden=false;', f'if(value.{key}===false) accepted.hidden=false;')
    return raw


def main():
    fixture_owner = unittest.TestCase()
    trusted, connect, server = tls_fixture.PublicSubmissionTests.tls_harness(fixture_owner)
    records = []
    owner, pid = 'c'*32, 'a'*32
    cases = (
        ('search-positive', FormOperation.SEARCH, 'normal', TestStatus.PASSED, 1, 1),
        ('login-positive-turkish', FormOperation.LOGIN, 'normal', TestStatus.PASSED, 2, 1),
        ('search-negative', FormOperation.SEARCH, 'negative', TestStatus.PASSED, 1, 1),
        ('preexisting', FormOperation.SEARCH, 'preexisting', TestStatus.BLOCKED, 0, 0),
        ('wrong-action', FormOperation.SEARCH, 'wrong-action', TestStatus.BLOCKED, 0, 0),
        ('wrong-fields', FormOperation.SEARCH, 'wrong-fields', TestStatus.BLOCKED, 0, 0),
        ('unmasked', FormOperation.LOGIN, 'unmasked', TestStatus.BLOCKED, 0, 0),
        ('ambiguous', FormOperation.SEARCH, 'ambiguous', TestStatus.BLOCKED, 0, 0),
        ('input-marker', FormOperation.SEARCH, 'input-marker', TestStatus.BLOCKED, 1, 0),
        ('mutated-action', FormOperation.SEARCH, 'mutated-action', TestStatus.BLOCKED, 1, 0),
        ('canary', FormOperation.SEARCH, 'canary', TestStatus.ERROR, 1, 0),
        ('changed-body', FormOperation.SEARCH, 'changed-body', TestStatus.ERROR, 1, 0),
        ('marker-only', FormOperation.SEARCH, 'marker-only', TestStatus.FAILED, 1, 0),
        ('missing-marker', FormOperation.SEARCH, 'missing-marker', TestStatus.FAILED, 1, 1),
    )
    try:
        with patch('adaptive_qa.egress.resolve_with_deadline', return_value=('93.184.216.34',)), \
                patch.object(DestinationGuard, 'connect', connect), \
                patch('adaptive_qa.public_submission.ssl.create_default_context', return_value=trusted), \
                sync_playwright() as playwright:
            browser = playwright.chromium.launch(timeout=10000)
            try:
                for name, operation, mode, expected, expected_reads, expected_posts in cases:
                    slots = ('login_username','login_password') if operation == FormOperation.LOGIN else ('search_query',)
                    references = tuple(SecretReference(reference_name(owner,pid,slot)) for slot in slots)
                    negative = mode == 'negative'
                    completion = ('login.rejected' if negative else 'login.accepted') if operation == FormOperation.LOGIN else ('search.empty' if negative else 'search.results')
                    form = InteractiveFormContract(pid,'b'*64,operation,references,
                        ElementMapping(completion,(LocatorSpec(LocatorStrategy.TEST_ID,'rejected' if negative else 'accepted'),)),5)
                    field = 'authenticated' if operation == FormOperation.LOGIN else 'found'
                    fields = ('account','password') if operation == FormOperation.LOGIN else ('query',)
                    proposal = PublicFormProposal(form,'https://qa.example.test/search','https://qa.example.test/search/execute',fields,
                        LocalBooleanResponse(200,field,True),LocalBooleanResponse(404,field,False))
                    review = ReviewedPublicForm(proposal,proposal.fingerprint())
                    project = ProjectConfig(pid,'Owned browser/TLS fixture',proposal.document_url,('qa.example.test',),True)
                    transport = PublicSubmissionTransport(review,project,current_fingerprint='b'*64)
                    server.update(status=404 if negative else 200,body=json.dumps({field:not negative}).encode(),headers={},drop=False,slow=False)
                    before_posts = len(server['contacts'])
                    guard = dict(dirty=False,armed=False,expected=None,response=None,reads=0,documents=0)
                    context = browser.new_context(service_workers='block',accept_downloads=False)
                    context.route_web_socket('**/*', lambda websocket:websocket.close())
                    page = context.new_page()
                    def route_request(route):
                        request=route.request
                        if request.method=='GET' and request.url==proposal.document_url and guard['documents']==0:
                            guard['documents']+=1
                            route.fulfill(status=200,content_type='text/html',body=document(operation,mode))
                        elif (guard['armed'] and guard['response'] is None and request.method=='POST' and request.url==proposal.endpoint_url
                              and request.post_data_buffer==guard['expected']):
                            response=transport.submit(url=request.url,method=request.method,
                                content_type=request.headers.get('content-type',''),body=request.post_data_buffer)
                            guard['response']=response
                            if response.outcome not in ('accepted','rejected'):
                                guard['dirty']=True;route.abort();return
                            assertion=proposal.accepted if response.outcome=='accepted' else proposal.rejected
                            route.fulfill(status=assertion.status_code,content_type='application/json',
                                body=json.dumps({assertion.field_name:assertion.expected_value}))
                        else:
                            guard['dirty']=True;route.abort()
                    context.route('**/*',route_request)
                    def before_inputs():return transport.prepare_destination()
                    def before_submit(values):
                        guard['expected']=urlencode(tuple(zip(fields,values,strict=True))).encode('ascii')
                        guard['armed']=True
                    original=SecretReference.resolve
                    def resolve(reference):
                        guard['reads']+=1
                        return original(reference)
                    try:
                        loaded=page.goto(proposal.document_url)
                        assert loaded is not None and loaded.status==200 and 'text/html' in loaded.headers['content-type']
                        with patch.dict(os.environ,{ref.environment_variable:'OWNED_BROWSER_INPUT_CANARY' for ref in references}), \
                                patch.object(SecretReference,'resolve',resolve):
                            result=probe_reviewed_public_form(page,review,project,owner_id=owner,current_fingerprint='b'*64,
                                network_clean=lambda:not guard['dirty'],before_inputs=before_inputs,before_submit=before_submit,
                                submission_state=lambda:guard['response'])
                        assert result.status==expected,(name,result)
                        assert guard['reads']==expected_reads,(name,guard['reads'])
                        posts=len(server['contacts'])-before_posts
                        assert posts==expected_posts,(name,posts)
                        assert 'OWNED_BROWSER_INPUT_CANARY' not in repr(result)
                        records.append(dict(scenario=name,status=result.status.value,input_references_read=guard['reads'],owned_tls_posts=posts))
                    finally:context.close()
            finally:browser.close()
    finally:fixture_owner.doCleanups()
    report=dict(installed_wheel=bool(INSTALLED),scenarios=records,documents_fulfilled_in_memory=True,
        actual_posts_used_owned_tls=True,public_customer_targets_contacted=False,queue_or_ui_admission_enabled=False,
        supervised_browser_worker=False,screenshots_or_traces_taken=False,raw_inputs_in_report=False)
    output=Path('artifacts/public-submission');output.mkdir(parents=True,exist_ok=True)
    (output/'browser-probe.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(scenarios=len(records),statuses=[r['status'] for r in records],owned_tls_posts=sum(r['owned_tls_posts'] for r in records))))


if __name__=='__main__':main()
