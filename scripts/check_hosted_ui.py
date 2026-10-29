"""Owned HTTPS-origin browser adapter for the authenticated server workspace."""
import json,os,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urlsplit
site=os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if site:sys.path.insert(0,str(Path(site).resolve(strict=True)))
import adaptive_qa
if site:assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(site).resolve())
from adaptive_qa.hosted import HostedSessions,HostedProjects,create_hosted_app
from adaptive_qa.project_store import ProjectActor
from adaptive_qa.site_check import SiteChecks
from playwright.sync_api import sync_playwright,expect
import uvicorn


def main():
    output=Path('artifacts/hosted');output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='owned-hosted-ui-') as directory:
        root=Path(directory);auth=HostedSessions(root/'auth.sqlite')
        for name in ('alice','bob'):auth.create_user(name+'@example.test','fixture-only-password')
        with auth._connection() as c:actors={r['email'].split('@')[0]:ProjectActor(r['user_id']) for r in c.execute('SELECT * FROM dashboard_users')}
        projects=HostedProjects(root/'projects.sqlite');SiteChecks(projects,free=True);ids={}
        for name in ('alice','bob'):
            pid=projects.create(actors[name],name+' private project').project_id;ids[name]=pid
            url='https://'+name+'.example.test/'
            projects.save_configuration(actors[name],pid,dict(base_url=url,allowed_hosts=[name+'.example.test'],allow_data_changes=False,secret_references={}))
            with projects._connection() as c:
                c.execute('INSERT INTO dashboard_site_checks (check_id,owner_id,project_id,server_id,status,url,summary_json) VALUES (?,?,?,?,?,?,?)',
                    (('a' if name=='alice' else 'b')*32,actors[name].user_id,pid,'owned-fixture','completed',url,
                    json.dumps(dict(inspected_pages=1,login=dict(status='found',candidate=dict(document_url=url,identifier_kind='email'))))))
        server=uvicorn.Server(uvicorn.Config(create_hosted_app(root,'https://qa.example.test',ui_directory=os.environ.get('ADAPTIVE_QA_VERIFY_UI','frontend/dist')),
            host='127.0.0.1',port=8899,access_log=False,log_level='critical'))
        thread=Thread(target=server.run,daemon=True);thread.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:assert time.monotonic()<deadline;time.sleep(.05)
            with sync_playwright() as pw:
                browser=pw.chromium.launch();page=browser.new_page(viewport=dict(width=1280,height=900));unexpected=[];errors=[];writes=[]
                def proxy(route):
                    request=route.request
                    if not request.url.startswith('https://qa.example.test/'):
                        unexpected.append(request.url);route.abort();return
                    if request.method!='GET':writes.append(urlsplit(request.url).path)
                    headers=request.all_headers();headers['host']='qa.example.test'
                    response=route.fetch(url='http://127.0.0.1:8899'+urlsplit(request.url).path,headers=headers)
                    route.fulfill(response=response)
                page.route('**/*',proxy);page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto('https://qa.example.test/')
                for name in ('alice','bob'):
                    page.get_by_label('Email',exact=True).fill(name+'@example.test')
                    page.get_by_label('Password',exact=True).fill('fixture-only-password')
                    page.get_by_role('button',name='Sign in',exact=True).click()
                    expect(page.get_by_text('SERVER',exact=True)).to_be_visible()
                    expect(page.get_by_text('https://'+name+'.example.test/',exact=True).first).to_be_visible()
                    assert page.get_by_text('https://'+('bob' if name=='alice' else 'alice')+'.example.test/',exact=True).count()==0
                    assert page.get_by_role('region',name='Public login demo').count()==0
                    assert page.get_by_text('Test options',exact=True).count()==0
                    assert all(c['secure'] for c in page.context.cookies() if c['name'] in ('adaptive_csrf','adaptive_session'))
                    if name=='alice':
                        panel=page.get_by_role('region',name='Website login tests')
                        panel.get_by_role('button',name='Add a test account',exact=True).click()
                        expect(panel.get_by_label('Test account email',exact=True)).to_be_visible()
                        panel.screenshot(path=str(output/'server-account.png'))
                        page.set_viewport_size(dict(width=390,height=844));assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                        panel.screenshot(path=str(output/'server-mobile.png'));page.set_viewport_size(dict(width=1280,height=900))
                        page.reload();expect(page.get_by_text('SERVER',exact=True)).to_be_visible()
                        assert page.get_by_label('Test account password',exact=True).count()==0
                        page.get_by_role('button',name='Sign out',exact=True).click()
                        expect(page.get_by_role('button',name='Sign in',exact=True)).to_be_visible()
                    else:
                        status=page.evaluate("async pid=>(await fetch('/api/projects/'+pid+'/configuration')).status",ids['alice'])
                        assert status==404
                assert not unexpected and not errors,(unexpected,errors)
                assert writes.count('/api/auth/login')==2 and writes.count('/api/auth/logout')==1 and all('site-checks' not in p and not p.endswith('/jobs') for p in writes)
                browser.close()
            result=dict(installed_wheel=bool(site),two_authenticated_accounts=True,owner_isolation=True,secure_cookies=True,
                real_backend=True,server_storage_disclosed=True,demo_and_local_tools_hidden=True,login_review_without_submission=True,
                reload_no_replay=True,mobile_overflow=False,external_requests=0,target_submissions=0,
                tls_termination_verified=False,scope='owned_https_origin_adapter')
            (output/('installed-ui.json' if site else 'source-ui.json')).write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(result))
        finally:server.should_exit=True;thread.join(15)


if __name__=='__main__':main()
