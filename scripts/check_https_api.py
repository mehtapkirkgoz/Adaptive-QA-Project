"""Owned TLS UI/CLI proof. Test-only socket routing is never shipped in the wheel."""
import argparse
import base64
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time
from unittest.mock import patch

SITE = os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if SITE:
    sys.path.insert(0, str(Path(SITE).resolve(strict=True)))


def fixture_process(args, remaining):
    """Explicit verification entry point, not a production transport option."""
    if not args.fixture_ca or not args.fixture_port or not 1 <= args.fixture_port <= 65535:
        raise ValueError('An owned fixture CA and port are required.')
    if args.fixture_child:
        from adaptive_qa.egress import DestinationGuard
        from adaptive_qa.api_process import main
        trusted = ssl.create_default_context(cafile=args.fixture_ca)
        def connect(guard, target, **kwargs):
            if (guard.local_sample or target.hostname != 'api.fixture.test' or target.port != 443
                    or target.addresses != ('93.184.216.34',)):
                raise ValueError('Only this owned TLS harness may be reached.')
            return socket.create_connection(('127.0.0.1', args.fixture_port), timeout=2)
        sys.argv = [str(Path(__file__).resolve()), *remaining]
        with patch('adaptive_qa.egress.resolve_with_deadline', return_value=('93.184.216.34',)), \
                patch.object(DestinationGuard, 'connect', connect), \
                patch('adaptive_qa.api_transport.ssl.create_default_context', return_value=trusted):
            main()
    else:
        from adaptive_qa.__main__ import main
        original = subprocess.Popen
        def supervised(command, *positional, **options):
            if command[1:3] == ['-m', 'adaptive_qa.api_process']:
                command = [sys.executable, str(Path(__file__).resolve()), '--fixture-child',
                    '--fixture-port', str(args.fixture_port), '--fixture-ca', args.fixture_ca, *command[3:]]
            return original(command, *positional, **options)
        sys.argv = [str(Path(__file__).resolve()), *remaining]
        with patch('adaptive_qa.api_process.subprocess.Popen', supervised):
            main()


def certificate(root, name):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
        .not_valid_after(now+timedelta(hours=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]),False)
        .add_extension(x509.BasicConstraints(ca=True,path_length=None),True).sign(key,hashes.SHA256()))
    ca, private = root/(name+'.pem'), root/(name+'.key')
    ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    return ca, private


def main(licensed=False):
    import adaptive_qa
    import uvicorn
    from playwright.sync_api import sync_playwright, expect
    from adaptive_qa.local_free import create_free_app
    if SITE:
        assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(SITE).resolve())
    origin='http://127.0.0.1:8889';contacts=[];errors=[];external=[];secret_headers=[]
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            contacts.append(self.path)
            if any(self.headers.get(name) for name in ('Authorization','Cookie','Proxy-Authorization')):secret_headers.append(True)
            status=404 if self.path=='/missing' else 302 if self.path=='/redirect' else 200
            raw=b'owned service ready' if self.path=='/plain' else b'{"ready":false}' if self.path=='/missing' else b'{"ready":true}'
            self.send_response(status)
            if status==302:self.send_header('Location','https://127.0.0.1/private')
            self.send_header('Content-Type','text/plain' if self.path=='/plain' else 'application/json');self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw)
    with TemporaryDirectory(prefix='adaptive-https-ui-') as temporary:
        root=Path(temporary);workspace=root/'workspace';workspace.mkdir()
        ca,key=certificate(root,'api.fixture.test');untrusted,_=certificate(root,'untrusted.fixture.test')
        fixture=ThreadingHTTPServer(('127.0.0.1',0),Fixture)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(ca,key)
        fixture.socket=tls.wrap_socket(fixture.socket,server_side=True)
        fixture_thread=Thread(target=fixture.serve_forever,daemon=True);fixture_thread.start()
        ui=os.environ.get('ADAPTIVE_QA_VERIFY_UI','frontend/dist')
        trust=root/'publisher-public.json'
        if licensed:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from adaptive_qa.auth_store import AuthStore
            from adaptive_qa.licensing import LicenseClaims, license_message
            from adaptive_qa.license_store import LicenseStore
            from adaptive_qa.local_licensed import create_licensed_app
            signer=Ed25519PrivateKey.generate();public=signer.public_key().public_bytes_raw()
            licenses=LicenseStore(workspace/'license.sqlite',{'fixture':public})
            now=int(time.time());payload=asdict(LicenseClaims('a'*32,'b'*32,now-10,now-10,now+3600,3,1))
            signature=base64.urlsafe_b64encode(signer.sign(license_message('fixture',payload))).rstrip(b'=').decode()
            licenses.install(json.dumps(dict(key_id='fixture',payload=payload,signature=signature)).encode())
            trust.write_text(json.dumps({'fixture':public.hex()}),encoding='utf-8')
            auth=AuthStore(workspace/'auth.sqlite');administrator=auth.create_user('tls-owner@example.test','owned TLS fixture password')
            app=create_licensed_app(workspace/'projects.sqlite',auth,administrator,licenses,port=8889,ui_directory=ui)
        else:app=create_free_app(workspace/'projects.sqlite',port=8889,ui_directory=ui)
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8889,log_level='critical',access_log=False))
        thread=Thread(target=server.run,daemon=True);thread.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:
                if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('Owned HTTPS proof dashboard did not start.')
                time.sleep(.05)
            def worker(authority=ca):
                command=['local','api-once','--workspace',str(workspace),'--trusted-keys',str(trust)] if licensed else ['dashboard','free-api-once','--database',str(workspace/'projects.sqlite')]
                result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--fixture-worker',
                    '--fixture-port',str(fixture.server_port),'--fixture-ca',str(authority),*command],
                    capture_output=True,check=True,timeout=45)
                return json.loads(result.stdout)
            with sync_playwright() as p:
                browser=p.chromium.launch()
                try:
                    page=browser.new_page(viewport=dict(width=1440,height=1000))
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.on('request',lambda request:external.append(request.url) if not request.url.startswith(origin+'/') else None)
                    page.goto(origin+'/')
                    if licensed:
                        page.get_by_label('Email',exact=True).fill('tls-owner@example.test')
                        page.get_by_label('Password',exact=True).fill('owned TLS fixture password')
                        page.get_by_role('button',name='Sign in',exact=True).click()
                    page.get_by_label('New project name',exact=True).fill('Owned HTTPS contract')
                    page.get_by_role('button',name='+ Create project',exact=True).click()
                    page.get_by_role('button',name='Owned HTTPS contract Project configuration').click()
                    page.get_by_label('Target URL',exact=True).fill('https://api.fixture.test')
                    page.get_by_label('Allowed hosts',exact=True).fill('api.fixture.test')
                    editor=page.get_by_role('region',name='Explicit local API binding')
                    editor.get_by_role('checkbox',name='Configure explicit API response').check()
                    expect(editor.get_by_label('API destination profile',exact=True)).to_have_value('public_https')
                    editor.get_by_label('API response assertion',exact=True).select_option('json_boolean')
                    def save(path,status=200,expected='true'):
                        editor.get_by_label('GET endpoint path',exact=True).fill(path)
                        editor.get_by_label('Expected API HTTP status',exact=True).fill(str(status))
                        editor.get_by_label('Expected API boolean',exact=True).select_option(expected)
                        page.get_by_role('button',name='Save configuration',exact=True).click()
                        expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    def queue():
                        panel=page.get_by_role('region',name='Explicit API execution')
                        panel.get_by_role('button',name='Review saved API binding',exact=True).click()
                        expect(panel.get_by_role('button',name='Queue one API request',exact=True)).to_be_disabled()
                        panel.get_by_role('checkbox',name='I authorize one GET request to my configured public HTTPS API.').check()
                        panel.get_by_role('button',name='Queue one API request',exact=True).click()
                        expect(panel.get_by_role('button',name='Cancel API job',exact=True)).to_be_visible()
                        return panel
                    save('/ready');assert not contacts
                    panel=page.get_by_role('region',name='Explicit API execution')
                    expect(panel.get_by_text('https://api.fixture.test/ready',exact=True)).to_be_visible()
                    panel.get_by_role('button',name='Review saved API binding',exact=True).click()
                    expect(panel.get_by_label('API review confirmation')).to_be_visible()
                    editor.get_by_label('GET endpoint path',exact=True).fill('/unsaved')
                    expect(panel.get_by_label('API review confirmation')).to_have_count(0)
                    editor.get_by_label('GET endpoint path',exact=True).fill('/ready')
                    panel=queue();assert not contacts
                    assert worker()['status']=='completed'
                    expect(panel.get_by_text('API result: passed',exact=True)).to_have_count(1,timeout=10000)
                    save('/missing',404,'false');panel=queue();assert worker()['status']=='completed'
                    expect(panel.get_by_text('API result: passed',exact=True)).to_have_count(2,timeout=10000)
                    save('/redirect');panel=queue();assert worker()['status']=='completed'
                    expect(panel.get_by_text('API result: failed',exact=True)).to_be_visible(timeout=10000)
                    expect(panel.get_by_text('HTTP status did not match the saved expectation.',exact=True)).to_be_visible()
                    assert contacts==['/ready','/missing','/redirect']
                    save('/ready');panel=queue();assert worker(untrusted)['status']=='completed'
                    expect(panel.get_by_text('API result: error',exact=True)).to_be_visible(timeout=10000)
                    expect(panel.get_by_text('TLS certificate verification failed.',exact=True)).to_be_visible()
                    assert contacts==['/ready','/missing','/redirect']
                    panel=queue();panel.get_by_role('button',name='Cancel API job',exact=True).click()
                    expect(panel.get_by_text('cancelled',exact=True)).to_be_visible()
                    assert worker() is None
                    editor.get_by_label('API response assertion',exact=True).select_option('status_only')
                    editor.get_by_label('GET endpoint path',exact=True).fill('/plain')
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    panel=queue();assert worker()['status']=='completed'
                    expect(panel.get_by_text('API result: passed',exact=True)).to_have_count(3,timeout=10000)
                    assert contacts==['/ready','/missing','/redirect','/plain']
                    page.set_viewport_size(dict(width=390,height=900))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    output=Path('artifacts/https-api');output.mkdir(parents=True,exist_ok=True)
                    panel.screenshot(path=str(output/('licensed-mobile.png' if licensed else 'free-mobile.png')))
                    page.set_viewport_size(dict(width=1440,height=1000))
                    editor.get_by_role('checkbox',name='Configure explicit API response').uncheck()
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    def old_capabilities(route):
                        response=route.fetch();data=response.json();data.pop('api_binding_profiles',None)
                        route.fulfill(response=response,json=data)
                    page.route('**/configuration',old_capabilities)
                    page.reload()
                    page.get_by_role('button',name='Owned HTTPS contract Project configuration').click()
                    expect(editor.get_by_role('checkbox',name='Configure explicit API response')).to_be_disabled()
                    page.unroute('**/configuration',old_capabilities)
                    assert not external and not errors and not secret_headers
                finally:browser.close()
        finally:
            server.should_exit=True;thread.join(timeout=10)
            fixture.shutdown();fixture.server_close();fixture_thread.join(timeout=5)
            assert not thread.is_alive()
    report=dict(licensed=licensed,installed_wheel=bool(SITE),explicitly_confirmed_jobs=6,
        passed_status_contracts=3,status_only_non_json_passed=True,redirect_failed_without_follow=True,untrusted_tls_failed_before_http=True,
        cancelled_without_retry=True,unsaved_confirmation_cleared=True,older_backend_capability_fail_closed=True,
        actual_fixture_http_requests=len(contacts),ui_external_requests=len(external),
        page_errors=errors,secret_headers_sent=bool(secret_headers),test_socket_override='owned_fixture_only',customer_network_verified=False)
    output=Path('artifacts/https-api');output.mkdir(parents=True,exist_ok=True)
    (output/('licensed.json' if licensed else 'free.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--fixture-child',action='store_true');parser.add_argument('--fixture-worker',action='store_true')
    parser.add_argument('--fixture-port',type=int);parser.add_argument('--fixture-ca');parser.add_argument('--licensed',action='store_true')
    args,remaining=parser.parse_known_args()
    if args.fixture_child or args.fixture_worker:fixture_process(args,remaining)
    else:
        if remaining:raise ValueError('Unknown verification arguments.')
        main(args.licensed)
