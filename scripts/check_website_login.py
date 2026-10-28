"""Owned TLS and main-panel proof of one-shot saved-site login; no public contact."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import time
from unittest.mock import patch
from urllib.parse import parse_qs

site=os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if site:sys.path.insert(0,str(Path(site).resolve(strict=True)))
import adaptive_qa
if site:assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(site).resolve())
from adaptive_qa.website_login import SavedWebsiteLoginReview
from adaptive_qa.website_login_process import run_login
from adaptive_qa.models import TestStatus
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


def main(ui=False):
    state=dict(mode='normal',posts=0,documents=0,session=False,bad=0)
    form='<form method="post" action="/session"><input name="csrf" type="hidden" value="private-csrf"><input type="email" name="email" required><input type="password" name="password" required><button>Sign in</button></form>'
    records=[];output=Path('artifacts/website-login');output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='owned-website-login-') as temp:
        root=Path(temp);key=ec.generate_private_key(ec.SECP256R1());name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'example.com')])
        now=datetime.now(timezone.utc)
        cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('example.com')]),False)
            .add_extension(x509.BasicConstraints(ca=True,path_length=None),True).sign(key,hashes.SHA256()))
        ca=root/'ca.pem';private=root/'key.pem';ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,status=200,body='',location=None,cookie=None):
                raw=body.encode();self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
                if location:self.send_header('Location',location)
                if cookie:self.send_header('Set-Cookie',cookie)
                try:self.end_headers();self.wfile.write(raw)
                except OSError:pass
            def do_GET(self):
                state['documents']+=1
                if self.path=='/login':
                    body='<h1>Login</h1>'+form
                    if state['mode']=='missing':body='<h1>No login</h1>'
                    if state['mode']=='captcha':body='<div id="captcha"></div>'+body
                    if state['mode']=='email-change':body=body.replace('type="email" name="email"','type="text" name="username"')
                    self.reply(body=body)
                elif self.path=='/secure':
                    if state['session'] and self.headers.get('Cookie')=='session=private-session':self.reply(body='<h1>Account</h1><a href="/logout">Logout</a>')
                    else:self.reply(302,location='/login')
                elif self.path=='/logout':
                    if state['mode']!='broken-logout':state['session']=False
                    self.reply(302,location='/login',cookie=None if state['mode']=='broken-logout' else 'session=; Max-Age=0; Path=/; Secure; HttpOnly')
                else:state['bad']+=1;self.reply(404)
            def do_POST(self):
                state['posts']+=1
                if self.path!='/session':state['bad']+=1;self.reply(404);return
                data=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
                assert data=={'csrf':['private-csrf'],'email':['qa@example.test'],'password':['private-password']}
                if state['mode'] in ('slow','cancel-active'):
                    time.sleep(4);self.reply(503);return
                if state['mode']=='foreign':self.reply(303,location='https://foreign.example/steal');return
                if state['mode']=='false-200':self.reply(body='<h1>Welcome</h1>');return
                if state['mode']=='rejected':self.reply(body='<div role="alert">Invalid credentials</div>'+form);return
                state['session']=True
                self.reply(302 if state['mode']=='post-302' else 303,location='/secure',cookie=None if state['mode']=='no-cookie' else 'session=private-session; Secure; HttpOnly; Path=/')
        tls_server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(ca,private)
        tls_server.socket=context.wrap_socket(tls_server.socket,server_side=True)
        tls_thread=Thread(target=tls_server.serve_forever,daemon=True);tls_thread.start()
        original=subprocess.Popen;server=thread=browser=None
        try:
            if ui:
                from adaptive_qa.local_free import LocalFreeProjects,LOCAL_ACTOR,create_free_app
                from adaptive_qa.site_check import SiteChecks
                import uvicorn
                projects=LocalFreeProjects(root/'projects.sqlite');pid=projects.create(LOCAL_ACTOR,'Owned login fixture').project_id
                projects.save_configuration(LOCAL_ACTOR,pid,dict(base_url='https://example.com/login',allowed_hosts=['example.com'],allow_data_changes=False,secret_references={}))
                before=projects.configuration(LOCAL_ACTOR,pid);SiteChecks(projects,free=True)
                with projects._connection() as c:
                    c.execute('INSERT INTO dashboard_site_checks (check_id,owner_id,project_id,server_id,status,url,summary_json) VALUES (?,?,?,?,?,?,?)',
                        ('a'*32,LOCAL_ACTOR.user_id,pid,'fixture','completed','https://example.com/login',json.dumps(dict(inspected_pages=1,login=dict(status='found',candidate=dict(document_url='https://example.com/login',identifier_kind='email'))))))
                app=create_free_app(root/'projects.sqlite',port=8897,ui_directory=os.environ.get('ADAPTIVE_QA_VERIFY_UI','frontend/dist'))
                server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8897,access_log=False,log_level='critical'))
                thread=Thread(target=server.run,daemon=True);thread.start()
                deadline=time.monotonic()+10
                while not server.started:assert time.monotonic()<deadline;time.sleep(.05)
            scenarios=[('normal','passed'),('rejected','failed'),('foreign','blocked'),('false-200','blocked'),('missing','blocked'),('captcha','blocked'),
                ('email-change','blocked'),('post-302','passed'),('no-cookie','blocked'),('broken-logout','blocked'),('untrusted','error'),
                ('private-dns','error'),('slow','error'),('cancel','cancelled'),('cancel-active','cancelled'),('duplicate','passed')]
            if ui:scenarios=[('normal','passed')]
            for mode,wanted in scenarios:
                state.update(mode=mode,session=False);prior=state['posts']
                wrapper=f'''
import socket,ssl
from pathlib import Path
import adaptive_qa
import adaptive_qa.egress as egress
import adaptive_qa.website_login_process as worker
assert {not bool(site)!r} or Path(adaptive_qa.__file__).resolve().is_relative_to(Path({site or ''!r}).resolve())
egress.resolve_with_deadline=lambda *a,**k: ({'127.0.0.1' if mode=='private-dns' else '93.184.216.34'!r},)
def owned(guard,target,**kwargs):
    assert not guard.local_sample and target.hostname=='example.com' and target.port==443
    assert target.addresses==('93.184.216.34',)
    return socket.create_connection(('127.0.0.1',{tls_server.server_port}),timeout=2)
egress.DestinationGuard.connect=owned
original=ssl.create_default_context
if {mode!='untrusted'!r}:ssl.create_default_context=lambda:original(cafile={str(ca)!r})
if {mode=='duplicate'!r}:
    original_request=worker.Transport.request
    def request(self,method,url,body=None):
        result=original_request(self,method,url,body)
        if method=='POST':
            try:original_request(self,method,url,body)
            except ValueError:pass
            else:raise AssertionError('Duplicate contact')
        return result
    worker.Transport.request=request
worker.main()
'''
                def spawn(command,**options):
                    if command[1:]==['-m','adaptive_qa.website_login_process']:
                        assert 'private-password' not in str(command) and 'private-password' not in str(options.get('env',{}))
                        return original([sys.executable,'-c',wrapper],**options)
                    return original(command,**options)
                with patch('adaptive_qa.website_login_process.subprocess.Popen',side_effect=spawn):
                    if ui:
                        from playwright.sync_api import sync_playwright,expect
                        with sync_playwright() as pw:
                            browser=pw.chromium.launch();page=browser.new_page(viewport=dict(width=1280,height=900))
                            external=[];errors=[]
                            page.on('request',lambda r:external.append(r.url) if not r.url.startswith('http://127.0.0.1:8897/') else None)
                            page.on('pageerror',lambda e:errors.append(str(e)))
                            page.goto('http://127.0.0.1:8897/')
                            panel=page.get_by_role('region',name='Website login tests')
                            expect(panel.get_by_label('Test account password',exact=True)).to_have_count(0)
                            panel.get_by_role('button',name='Add a test account',exact=True).click()
                            expect(panel.get_by_label('Test account email',exact=True)).to_be_visible()
                            assert state['posts']==prior
                            panel.screenshot(path=str(output/'account-entry.png'))
                            panel.get_by_label('Test account email',exact=True).fill('qa@example.test')
                            panel.get_by_label('Test account password',exact=True).fill('private-password')
                            panel.get_by_role('checkbox').check()
                            panel.get_by_role('button',name='Run login tests',exact=True).click()
                            expect(panel.get_by_role('heading',name='Login checks passed',exact=True)).to_be_visible(timeout=20000)
                            assert panel.get_by_label('Test account password',exact=True).count()==0
                            panel.screenshot(path=str(output/'desktop.png'))
                            page.reload();expect(panel.get_by_role('heading',name='Login checks passed',exact=True)).to_be_visible()
                            page.set_viewport_size(dict(width=390,height=844));panel.scroll_into_view_if_needed()
                            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                            panel.screenshot(path=str(output/'mobile.png'))
                            assert not external and not errors,(external,errors)
                            assert not page.evaluate('JSON.stringify(localStorage)+JSON.stringify(sessionStorage)').find('private-password')>=0
                            browser.close();browser=None
                        assert projects.configuration(LOCAL_ACTOR,pid)==before
                        assert b'private-password' not in (root/'projects.sqlite').read_bytes()
                        assert b'qa@example.test' not in (root/'projects.sqlite').read_bytes()
                        actual='passed'
                    else:
                        review=SavedWebsiteLoginReview('b'*32,'c'*32,'a'*32,'d'*64,'https://example.com/login','email')
                        result=run_login(review,'qa@example.test','private-password',timeout_seconds=1.5 if mode=='slow' else 30,
                            should_cancel=lambda:mode=='cancel' or mode=='cancel-active' and state['posts']>prior)
                        actual=result.status.value
                        assert 'private-password' not in str(result) and 'private-csrf' not in str(result)
                assert actual==wanted,(mode,actual,wanted)
                posts=state['posts']-prior;assert posts<=1,(mode,posts)
                if mode in ('normal','duplicate'):assert posts==1
                records.append(dict(scenario=mode,status=actual,posts=posts))
            assert state['bad']==0
            result=dict(installed_wheel=bool(site),ui=ui,scenarios=records,external_targets=0,credential_files=0,automatic_retries=0,
                prior_settings_preserved=True,source='owned_tls_fixture')
            (output/(('installed-' if site else 'source-')+('ui' if ui else 'worker')+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(result))
        finally:
            if browser:browser.close()
            if server:server.should_exit=True;thread.join(15)
            tls_server.shutdown();tls_server.server_close();tls_thread.join(5)


if __name__=='__main__':main('--ui' in sys.argv)
