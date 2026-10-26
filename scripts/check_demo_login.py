"""Exact-demo supervised browser proof on owned TLS mirrors; never contacts the public demo."""
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread, Event
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]
INSTALLED = os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if INSTALLED: sys.path.insert(0, str(Path(INSTALLED).resolve(strict=True)))
import adaptive_qa
if INSTALLED: assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(INSTALLED).resolve())
from adaptive_qa.demo_login_contract import DemoLoginPlan, DemoLoginScenario
from adaptive_qa.demo_login_process import run_isolated_demo_login
from adaptive_qa.models import TestStatus


def main(ui=False):
    state = dict(mode='normal', posts=0, documents=0, bad=0, flash='', session=False)
    records = []
    slow_done=Event();slow_done.set()
    with TemporaryDirectory(prefix='owned-demo-login-') as temporary:
        root = Path(temporary)
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'the-internet.herokuapp.com')])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
            .not_valid_after(now+timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('the-internet.herokuapp.com')]), False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), True).sign(key, hashes.SHA256()))
        ca, private = root/'ca.pem', root/'key.pem'
        ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                             serialization.NoEncryption()))
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def reply(self, status=200, body='', location=None, cookie=None):
                raw = body.encode()
                self.send_response(status); self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                if location: self.send_header('Location', location)
                if cookie: self.send_header('Set-Cookie', cookie)
                try:self.end_headers();self.wfile.write(raw)
                except OSError: pass
            def do_GET(self):
                state['documents'] += 1
                if self.path == '/login':
                    if state['mode']=='oversize':self.reply(body='x'*65537);return
                    if state['mode'] == 'missing-input':
                        self.reply(body='<h1>No form</h1>'); return
                    self.reply(body='<html><div id="flash">'+state['flash']+'</div>'
                        '<form id="login" method="post" action="/authenticate"><input name="username">'
                        '<input name="password" type="password"><button type="submit">Login</button></form></html>')
                elif self.path == '/secure':
                    if state['session'] and self.headers.get('Cookie') == 'session=owned-session':
                        marker = '' if state['mode'] == 'missing-marker' else '<div id="flash">You logged into a secure area!</div>'
                        self.reply(body='<html><h2>Secure Area</h2>'+marker+'<a href="/logout">Logout</a></html>')
                    else:
                        state['flash'] = 'You must login to view the secure area!'
                        self.reply(302, location='/login')
                elif self.path == '/logout':
                    state['flash'] = 'You logged out of the secure area!'
                    if state['mode'] != 'broken-logout': state['session'] = False
                    self.reply(302, location='/login', cookie=None if state['mode'] == 'broken-logout' else
                               'session=; Max-Age=0; Path=/; Secure; HttpOnly')
                else:
                    state['bad'] += 1; self.reply(404)
            def do_POST(self):
                state['posts'] += 1
                if self.path != '/authenticate': state['bad'] += 1; self.reply(404); return
                body = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
                if state['mode'] == 'slow':
                    slow_done.clear()
                    import time; time.sleep(4)
                valid = body == {'username': ['tomsmith'], 'password': ['SuperSecretPassword!']}
                state['session'] = valid
                state['flash'] = 'You logged into a secure area!' if valid else 'Your password is invalid!'
                if state['mode'] == 'foreign-redirect': self.reply(302, location='https://other.example/secure'); return
                if state['mode'] == 'wrong-status': self.reply(200, body='<h2>Secure Area</h2>'); return
                self.reply(302, location='/secure' if valid else '/login',
                    cookie='session=owned-session; Path=/; Secure; HttpOnly; SameSite=Lax' if valid and state['mode'] != 'no-cookie' else None)
                slow_done.set()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(ca, private)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        original = subprocess.Popen
        ui_server = ui_thread = browser = playwright = None
        try:
            cases = [('accepted', 'normal', DemoLoginScenario.ACCEPTED, TestStatus.PASSED),
                     ('rejected', 'normal', DemoLoginScenario.REJECTED, TestStatus.PASSED),
                     ('logout', 'normal', DemoLoginScenario.LOGOUT, TestStatus.PASSED),
                     ('foreign', 'foreign-redirect', DemoLoginScenario.ACCEPTED, TestStatus.ERROR),
                     ('status', 'wrong-status', DemoLoginScenario.ACCEPTED, TestStatus.ERROR),
                     ('marker', 'missing-marker', DemoLoginScenario.ACCEPTED, TestStatus.FAILED),
                     ('cookie', 'no-cookie', DemoLoginScenario.ACCEPTED, TestStatus.ERROR),
                     ('logout-not-cleared', 'broken-logout', DemoLoginScenario.LOGOUT, TestStatus.ERROR),
                     ('missing', 'missing-input', DemoLoginScenario.ACCEPTED, TestStatus.BLOCKED),
                     ('untrusted', 'untrusted', DemoLoginScenario.ACCEPTED, TestStatus.ERROR),
                     ('cancelled', 'normal', DemoLoginScenario.ACCEPTED, TestStatus.CANCELLED),
                     ('deadline', 'slow', DemoLoginScenario.ACCEPTED, TestStatus.ERROR),
                     ('duplicate', 'duplicate', DemoLoginScenario.ACCEPTED, TestStatus.ERROR),
                     ('private-dns', 'private-dns', DemoLoginScenario.ACCEPTED, TestStatus.ERROR),
                     ('oversize', 'oversize', DemoLoginScenario.ACCEPTED, TestStatus.ERROR)]
            if ui:
                import time
                import uvicorn
                from playwright.sync_api import sync_playwright, expect
                from adaptive_qa.local_free import LocalFreeProjects, LOCAL_ACTOR, create_free_app
                projects=LocalFreeProjects(root/'projects.sqlite')
                pid=projects.create(LOCAL_ACTOR,'Preserved local site').project_id
                projects.save_configuration(LOCAL_ACTOR,pid,dict(base_url='https://example.com/',
                    allowed_hosts=['example.com'],allow_data_changes=False,secret_references={}))
                before_settings=projects.configuration(LOCAL_ACTOR,pid)
                app=create_free_app(projects.database,port=8896,
                    ui_directory=os.environ.get('ADAPTIVE_QA_VERIFY_UI',str(ROOT/'frontend/dist')))
                ui_server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8896,log_level='error'))
                ui_thread=Thread(target=ui_server.run,daemon=True);ui_thread.start()
                deadline=time.monotonic()+10
                while not ui_server.started:
                    assert time.monotonic()<deadline;time.sleep(.05)
                playwright=sync_playwright().start();browser=playwright.chromium.launch()
                page=browser.new_page(viewport={'width':1440,'height':1100})
                errors=[];external=[];admissions=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:external.append(request.url) if not request.url.startswith('http://127.0.0.1:8896/') else None)
                page.on('request',lambda request:admissions.append(request.url) if request.method=='POST' and request.url.endswith('/demo-login/jobs') else None)
                page.goto('http://127.0.0.1:8896/')
                panel=page.get_by_role('region',name='Public login demo')
                expect(panel.get_by_role('heading',name='Try a real login test')).to_be_visible()
                cases=cases[:3]+[('cancel-active','slow',DemoLoginScenario.ACCEPTED,TestStatus.CANCELLED)]
            for label, mode, scenario, expected in cases:
                state.update(mode=mode, flash='', session=False)
                before = state['posts']; roots = []
                wrapper = f'''
import socket,ssl,sys
from pathlib import Path
import adaptive_qa
import adaptive_qa.egress as egress
import adaptive_qa.demo_login_process as worker
assert {not bool(INSTALLED)!r} or Path(adaptive_qa.__file__).resolve().is_relative_to(Path({INSTALLED or ''!r}).resolve())
egress.resolve_with_deadline=lambda *args,**kwargs: ({'127.0.0.1' if mode=='private-dns' else '93.184.216.34'!r},)
def owned(guard,target,**kwargs):
    assert not guard.local_sample and target.hostname=='the-internet.herokuapp.com'
    assert target.port==443 and target.addresses==('93.184.216.34',)
    return socket.create_connection(('127.0.0.1',{server.server_port}),timeout=2)
egress.DestinationGuard.connect=owned
original=ssl.create_default_context
if {mode != 'untrusted'!r}: ssl.create_default_context=lambda:original(cafile={str(ca)!r})
if {mode=='duplicate'!r}:
    from adaptive_qa.demo_login_transport import DemoLoginTransport
    request=DemoLoginTransport.request
    def duplicate(self,method,url,body=None):
        response=request(self,method,url,body)
        if method=='POST':
            try:request(self,method,url,body)
            except ValueError:pass
            else:raise AssertionError('Duplicate POST was accepted')
        return response
    DemoLoginTransport.request=duplicate
sys.argv=['owned-demo-proof']+sys.argv[1:]
worker.main()
'''
                def spawn(command, **options):
                    if 'adaptive_qa.demo_login_process' not in command: return original(command, **options)
                    source = Path(command[command.index('--input')+1]); roots.append(source.parent)
                    assert 'password' not in source.read_text() and 'SSLKEYLOGFILE' not in options['env']
                    return original([sys.executable, '-c', wrapper, *command[3:]], **options)
                with patch('adaptive_qa.public_submission_process.subprocess.Popen', side_effect=spawn):
                    if ui:
                        panel.get_by_label('Demo scenario',exact=True).select_option(scenario.value)
                        panel.get_by_role('checkbox').check()
                        panel.get_by_role('button',name='Review demo test',exact=True).click()
                        expect(panel.get_by_role('button',name='Run demo test',exact=True)).to_be_visible()
                        if label=='accepted':
                            panel.get_by_label('Demo scenario',exact=True).select_option('rejected_login')
                            expect(panel.get_by_role('button',name='Run demo test',exact=True)).to_have_count(0)
                            panel.get_by_label('Demo scenario',exact=True).select_option(scenario.value)
                            panel.get_by_role('button',name='Review demo test',exact=True).click()
                            expect(panel.get_by_role('button',name='Run demo test',exact=True)).to_be_visible()
                        assert state['posts']==before,'Review contacted the target'
                        panel.get_by_role('button',name='Run demo test',exact=True).click()
                        if label=='cancel-active':
                            deadline=time.monotonic()+20
                            while state['posts']==before:
                                assert time.monotonic()<deadline;page.wait_for_timeout(50)
                            panel.get_by_role('button',name='Stop demo test',exact=True).click()
                            expect(panel.get_by_text('Stopped',exact=True)).to_have_count(1,timeout=15000)
                        else:
                            expect(panel.get_by_text('Passed',exact=True)).to_have_count(len(records)+1,timeout=45000)
                        data=page.evaluate("async (pid)=>(await (await fetch('/api/projects/'+pid+'/interactive/jobs')).json()).jobs",pid)
                        job=next(item for item in data if item['scope']=='authorized_login_demo')
                        from adaptive_qa.interactive_probe import InteractiveProbeResult
                        result=InteractiveProbeResult(TestStatus(job['result']['status']),'sanitized',job['result']['attempted_submissions'])
                    else:
                        result = run_isolated_demo_login(DemoLoginPlan(scenario), timeout_seconds=2 if mode=='slow' else 30,
                                                        should_cancel=(lambda: True) if label=='cancelled' else None)
                assert result.status == expected, (label, result, {k:state[k] for k in ('posts','documents','bad','session')})
                if mode=='slow':assert slow_done.wait(6),'Owned slow fixture did not finish'
                assert all(not directory.exists() for directory in roots), (label, 'profile retained')
                posts = state['posts']-before
                assert posts <= 1 and not state['bad'], (label, posts, state['bad'])
                if expected == TestStatus.PASSED: assert posts == 1
                if label in ('missing', 'untrusted', 'cancelled', 'private-dns', 'oversize'): assert posts == 0
                if label=='duplicate':assert posts==1
                records.append(dict(scenario=label, status=result.status.value, owned_posts=posts,
                                    private_profile_removed=True))
            if ui:
                assert projects.configuration(LOCAL_ACTOR,pid)==before_settings
                assert len(admissions)==4 and not external and not errors
                saved_posts=state['posts'];page.reload()
                panel=page.get_by_role('region',name='Public login demo')
                expect(panel.get_by_text('Passed',exact=True)).to_have_count(3)
                expect(panel.get_by_text('Stopped',exact=True)).to_have_count(1)
                assert state['posts']==saved_posts and len(admissions)==4
                output=Path('artifacts/demo-login');output.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(output/'desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Mobile overflow'
                page.screenshot(path=str(output/'mobile.png'),full_page=True)
        finally:
            if browser is not None:browser.close()
            if playwright is not None:playwright.stop()
            if ui_server is not None:ui_server.should_exit=True;ui_thread.join(timeout=20)
            server.shutdown(); server.server_close(); thread.join(timeout=5)
    report = dict(scenarios=records, installed_wheel=bool(INSTALLED), supervised_child_package_verified=bool(INSTALLED),
                  owned_tls_only=True, external_demo_contacted=False, customer_targets_contacted=False,
                  production_tls_override_exposed=False, raw_credentials_or_cookies_saved=False,
                  screenshots_or_traces=False, private_profiles_removed=True, ui_to_managed_worker=ui,
                  saved_target_unchanged=ui,reload_did_not_replay=ui,
                  active_post_cancelled=ui,changed_scenario_invalidates_confirmation=ui,
                  panel_screenshots=2 if ui else 0)
    output = Path('artifacts/demo-login'); output.mkdir(parents=True, exist_ok=True)
    (output/('ui.json' if ui else 'browser.json')).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--ui',action='store_true')
    main(parser.parse_args().ui)
