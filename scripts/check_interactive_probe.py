"""Controlled DOM transitions only: all document loads fulfilled and all other traffic denied."""
from dataclasses import replace
import json
import os
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy,ProjectElementMappings
from adaptive_qa.interactive_contracts import InteractiveFormContract,FormOperation
from adaptive_qa.interactive_probe import probe_controlled_form
from adaptive_qa.secrets import SecretReference


def main():
    origin = 'http://127.0.0.1:8000/interactive'
    project = ProjectConfig('a'*32,'Controlled DOM',origin,('127.0.0.1',),True)
    login = '<label>Username<input name="user"></label><label>Password<input name="password" type="password"></label><button>Sign in</button>'
    search = '<label>Search products<input name="query" type="search"></label><button>Search</button>'
    def document(controls,*,action=origin,visible=False,canary=False,no_result=False):
        script = "window.submits=0;document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.submits++;const f=e.target;const good=f.elements.user ? f.elements.user.value==='fixture-user' && f.elements.password.value==='fixture-password' : f.elements.query.value==='fixture-query';document.querySelector('[data-testid='+ (good?'result':'negative') +']').hidden=false;});"
        if canary: script += "document.querySelector('input').addEventListener('input',()=>fetch('https://example.invalid/canary'));"
        if no_result: script = "window.submits=0;document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.submits++;});"
        return '<meta charset="utf-8"><form method="get" action="'+action+'">'+controls+'</form><div data-testid="result" '+('' if visible else 'hidden')+'>Complete</div><div data-testid="negative" hidden>Rejected</div><script>'+script+'</script>'
    def contract(kind=FormOperation.LOGIN,negative=False):
        references = (SecretReference('PROBE_USER'),SecretReference('PROBE_PASSWORD')) if kind==FormOperation.LOGIN else (SecretReference('PROBE_QUERY'),)
        key = ('login.rejected' if negative else 'login.accepted') if kind==FormOperation.LOGIN else ('search.empty' if negative else 'search.results')
        return InteractiveFormContract(project.project_id,'b'*64,kind,references,
            ElementMapping(key,(LocatorSpec(LocatorStrategy.TEST_ID,'negative' if negative else 'result'),)),5)
    cases = [
        ('login-success',document(login),contract(),'passed',2,1,{}),
        ('login-rejection',document(login),contract(negative=True),'passed',2,1,{'PROBE_PASSWORD':'invalid-fixture-password'}),
        ('turkish-login',document(login.replace('Username','Kullanıcı adı').replace('Password','Parola').replace('Sign in','Oturum aç')),contract(),'passed',2,1,{}),
        ('search-results',document(search),contract(FormOperation.SEARCH),'passed',1,1,{}),
        ('search-empty',document(search),contract(FormOperation.SEARCH,True),'passed',1,1,{'PROBE_QUERY':'empty-fixture-query'}),
        ('existing-marker',document(login,visible=True),contract(),'blocked',0,0,{}),
        ('wrong-action',document(login,action='https://example.invalid/submit'),contract(),'blocked',0,0,{}),
        ('post-method',document(login).replace('method="get"','method="post"'),contract(),'blocked',0,0,{}),
        ('button-action-override',document(login.replace('<button>','<button formaction="https://example.invalid/submit">')),contract(),'blocked',0,0,{}),
        ('ambiguous-submit',document(login+'<button>Sign in</button>'),contract(),'blocked',0,0,{}),
        ('unmasked-password',document(login.replace('type="password"','type="text"')),contract(),'blocked',0,0,{}),
        ('missing-control',document(login.replace('<label>Password<input name="password" type="password"></label>','')),contract(),'blocked',0,0,{}),
        ('no-transition',document(login,no_result=True),contract(),'failed',2,1,{}),
        ('input-shows-marker',document(login).replace("window.submits=0;","window.submits=0;document.querySelector('input').addEventListener('input',()=>document.querySelector('[data-testid=result]').hidden=false);"),contract(),'blocked',2,0,{}),
        ('input-changes-action',document(login).replace("window.submits=0;","window.submits=0;document.querySelector('input').addEventListener('input',()=>document.querySelector('form').action='https://example.invalid/changed');"),contract(),'blocked',2,0,{}),
        ('credential-canary',document(login,canary=True),contract(),'error',2,0,{}),
    ]
    reports=[]
    with patch.dict(os.environ,{'PROBE_USER':'fixture-user','PROBE_PASSWORD':'fixture-password','PROBE_QUERY':'fixture-query'}),sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            for name,html,definition,expected,expected_reads,expected_submits,overrides in cases:
                context=browser.new_context(service_workers='block',accept_downloads=False)
                try:
                    denied,reads=[0],[0]
                    page=context.new_page()
                    def route(request):
                        if request.request.url==origin and request.request.is_navigation_request() and request.request.method=='GET':
                            request.fulfill(status=200,content_type='text/html',body=html)
                        else:
                            denied[0]+=1;request.abort()
                    context.route('**/*',route)
                    context.route_web_socket('**/*',lambda connection:connection.close())
                    page.goto(origin)
                    original=SecretReference.resolve
                    def resolve(reference): reads[0]+=1;return original(reference)
                    with patch.dict(os.environ,overrides),patch.object(SecretReference,'resolve',new=resolve):
                        result=probe_controlled_form(page,definition,project,current_fingerprint='b'*64,network_clean=lambda:denied[0]==0)
                    submits=page.evaluate('window.submits')
                    assert (result.status.value,reads[0],submits)==(expected,expected_reads,expected_submits),(name,result,reads,submits)
                    assert result.attempted_submissions<=1
                    assert 'fixture-password' not in repr(result) and 'fixture-user' not in repr(result)
                    reports.append(dict(scenario=name,status=result.status.value,input_reference_reads=reads[0],submissions=submits,denied_network=denied[0]))
                finally:context.close()
        finally:browser.close()
    output=Path('artifacts/interactive-probe');output.mkdir(parents=True,exist_ok=True)
    report=dict(controlled_dom_only=True,network_submissions_enabled=False,catalog_execution_enabled=False,screenshots_captured=0,scenarios=reports)
    (output/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'scenarios':len(reports),'controlled_dom_only':True,'network_submissions_enabled':False}))


if __name__=='__main__':main()
