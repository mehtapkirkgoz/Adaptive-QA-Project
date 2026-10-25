"""Real local UI editor -> confirmed queue -> supervised worker on owned fixtures."""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic,sleep
from urllib.parse import urlencode
from unittest.mock import patch
import json
import os
import subprocess
import sys

import uvicorn
from playwright.sync_api import sync_playwright,expect
from check_owned_submission import server as fixture_server
from adaptive_qa.local_free import LocalFreeProjects,LOCAL_ACTOR,create_free_app
from adaptive_qa.interactive_queue import OwnedInteractiveQueue


def main():
    port=8894;origin=f'http://127.0.0.1:{port}';target='http://127.0.0.1:8000'
    contacts=dict(documents=0,posts=0,bad=0)
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path not in ('/work/signin','/docs/search'):contacts['bad']+=1;self.send_error(404);return
            login=self.path=='/work/signin';contacts['documents']+=1
            controls=('<label>Username<input name="account"></label><label>Password<input type="password" name="passcode"></label><button>Sign in</button>'
                if login else '<label>Search products<input name="term" type="search"></label><button>Search</button>')
            endpoint='/api/signin' if login else '/api/find';field='authenticated' if login else 'hasResults'
            document='<meta charset="utf-8"><form method="post" action="'+target+endpoint+'">'+controls+'</form>'
            document+='<div data-testid="ready" hidden>Ready</div><div data-testid="empty" hidden>No results</div>'
            document+="<script>const form=document.querySelector('form');form.addEventListener('submit',e=>{e.preventDefault();fetch(form.action,{method:'POST',body:new URLSearchParams(new FormData(form))}).then(r=>r.json()).then(d=>document.querySelector('[data-testid='+ (d."+field+"?'ready':'empty') +']').hidden=false).catch(()=>{});});</script>"
            raw=document.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_POST(self):
            contacts['posts']+=1
            login=self.path=='/api/signin'
            expected=urlencode({'account':'fixture-user','passcode':'fixture-code'} if login else {'term':'missing item'}).encode()
            raw=self.rfile.read(min(int(self.headers.get('Content-Length','0')),8193))
            if self.path not in ('/api/signin','/api/find') or raw!=expected:contacts['bad']+=1
            raw=b'{"authenticated":true}' if login else b'{"hasResults":false}'
            self.send_response(201 if login else 200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    output=Path('artifacts/dashboard');output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='reusable-ui-') as temporary,fixture_server(Fixture,8000):
        database=Path(temporary)/'projects.sqlite';projects=LocalFreeProjects(database)
        project=projects.create(LOCAL_ACTOR,'Reusable editor proof');queue=OwnedInteractiveQueue(projects)
        app=create_free_app(database,port=port,ui_directory=Path('frontend/dist'))
        service=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='critical',access_log=False,proxy_headers=False))
        thread=Thread(target=service.run,daemon=True);thread.start();errors=[];external=[];proofs=[]
        try:
            deadline=monotonic()+10
            while not service.started:
                if not thread.is_alive() or monotonic()>deadline:raise RuntimeError('Owned UI failed to start.')
                sleep(.05)
            with sync_playwright() as p:
                browser=p.chromium.launch()
                try:
                    page=browser.new_page(viewport=dict(width=1440,height=1100));page.set_default_timeout(10000)
                    page.on('pageerror',lambda error:errors.append(type(error).__name__))
                    def route(request):
                        if request.request.url.startswith(origin+'/'):request.continue_()
                        else:external.append('denied');request.abort()
                    page.route('**/*',route);page.goto(origin+'/#advanced')
                    page.get_by_role('button',name='Reusable editor proof').click()
                    editor=page.get_by_role('region',name='Reusable local form binding')
                    for login in (True,False):
                        before=dict(contacts)
                        page.get_by_label('Target URL',exact=True).fill(target+('/work/signin' if login else '/docs/search'))
                        page.get_by_label('Allowed hosts',exact=True).fill('127.0.0.1')
                        page.get_by_role('checkbox',name='Allow tests that change data').check()
                        if login:editor.get_by_role('checkbox',name='Configure reusable local form').check()
                        else:editor.get_by_label('Form operation',exact=True).select_option('search')
                        editor.get_by_label('POST endpoint URL',exact=True).fill(target+('/api/signin' if login else '/api/find'))
                        if login:
                            editor.get_by_label('Username field name',exact=True).fill('account')
                            editor.get_by_label('Password field name',exact=True).fill('passcode')
                            editor.get_by_label('accepted HTTP status',exact=True).fill('201')
                            editor.get_by_label('rejected HTTP status',exact=True).fill('403')
                            page.get_by_role('checkbox',name='login username').check();page.get_by_role('checkbox',name='login password').check()
                        else:
                            editor.get_by_label('Query field name',exact=True).fill('term')
                            page.get_by_role('checkbox',name='search query').check()
                        page.get_by_role('button',name='Save configuration',exact=True).click()
                        expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                        saved=projects.configuration(LOCAL_ACTOR,project.project_id)
                        assert saved['local_form_binding']['operation']==('login' if login else 'search')
                        panel=page.get_by_role('region',name='Controlled interactive forms')
                        expect(panel).to_be_visible()
                        panel.get_by_text('Run queued jobs locally',exact=True).click()
                        expect(panel.get_by_text('python -m adaptive_qa dashboard free-worker-cycle',exact=False)).to_be_visible()
                        assert contacts==before,'Opening worker guidance contacted a target'
                        panel.get_by_text('Run queued jobs locally',exact=True).click()
                        if not login:panel.get_by_label('Expected form outcome',exact=True).select_option('rejected')
                        panel.get_by_label('Completion test ID',exact=True).fill('ready' if login else 'empty')
                        panel.get_by_role('button',name='Review interactive submission',exact=True).click()
                        confirmation=panel.get_by_label('Interactive review confirmation');expect(confirmation).to_be_visible()
                        if login:
                            editor.get_by_label('accepted JSON boolean field',exact=True).fill('changed')
                            expect(confirmation).to_have_count(0)
                            expect(panel.get_by_role('button',name='Review interactive submission',exact=True)).to_be_disabled()
                            editor.get_by_label('accepted JSON boolean field',exact=True).fill('authenticated')
                            panel.get_by_role('button',name='Review interactive submission',exact=True).click();expect(confirmation).to_be_visible()
                        assert contacts==before,'Saving/review contacted a target'
                        panel.get_by_role('checkbox',name='I authorize this one submission on my owned local fixture.').check()
                        panel.get_by_role('button',name='Queue one interactive submission',exact=True).click()
                        expect(panel.get_by_role('button',name='Cancel interactive job',exact=True)).to_be_visible()
                        values={'login_username':'fixture-user','login_password':'fixture-code'} if login else {'search_query':'missing item'}
                        environment={saved['secret_references'][slot]['environment_variable']:value for slot,value in values.items()}
                        with patch.dict(os.environ,environment):
                            worker=subprocess.run([sys.executable,'-m','adaptive_qa','dashboard',
                                'free-worker-cycle','--database',str(database)],
                                capture_output=True,timeout=90,check=True)
                        cycle=json.loads(worker.stdout)
                        assert cycle['discovery'] is None and cycle['run'] is None
                        assert cycle['interactive']['status']=='completed'
                        assert queue.list(LOCAL_ACTOR,project.project_id)[0]['result']==dict(status='passed',attempted_submissions=1)
                        expect(panel.get_by_text('queued',exact=True)).to_have_count(0,timeout=10000)
                        expect(panel.get_by_text('Result: passed; submissions: 1',exact=True).last).to_be_visible(timeout=10000)
                        assert contacts['documents']==before['documents']+1 and contacts['posts']==before['posts']+1
                        assert b'fixture-code' not in database.read_bytes()
                        proofs.append(dict(operation='login' if login else 'search',expected='positive' if login else 'negative',result='passed'))
                    page.set_viewport_size(dict(width=390,height=900));editor.scroll_into_view_if_needed()
                    editor.screenshot(path=str(output/'reusable-editor-mobile.png'))
                    panel.screenshot(path=str(output/'reusable-review-mobile.png'))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    assert page.locator('input[type=password]').count()==0
                    assert not errors and not external and contacts['bad']==0
                    editor.get_by_role('checkbox',name='Configure reusable local form').uncheck()
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    assert 'local_form_binding' not in projects.configuration(LOCAL_ACTOR,project.project_id)
                finally:browser.close()
        finally:service.should_exit=True;thread.join(timeout=10);assert not thread.is_alive()
    report=dict(owned_local_only=True,worker_entrypoint='dashboard free-worker-cycle',
        ui_saved_reviewed_confirmed_executed=proofs,contacts=contacts,
        edit_clears_confirmation=True,unsaved_review_blocked=True,removal_verified=True,
        ui_external_requests=0,page_errors=0,mobile_overflow=False,credential_values_entered_in_ui=False)
    (output/'reusable-editor.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
