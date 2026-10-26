"""Exact-demo supervised browser proof on owned TLS mirrors; never contacts the public demo."""
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
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


def main():
    state = dict(mode='normal', posts=0, documents=0, bad=0, flash='', session=False)
    records = []
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
                self.end_headers()
                try: self.wfile.write(raw)
                except OSError: pass
            def do_GET(self):
                state['documents'] += 1
                if self.path == '/login':
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
                    import time; time.sleep(4)
                valid = body == {'username': ['tomsmith'], 'password': ['SuperSecretPassword!']}
                state['session'] = valid
                state['flash'] = 'You logged into a secure area!' if valid else 'Your password is invalid!'
                if state['mode'] == 'foreign-redirect': self.reply(302, location='https://other.example/secure'); return
                if state['mode'] == 'wrong-status': self.reply(200, body='<h2>Secure Area</h2>'); return
                self.reply(302, location='/secure' if valid else '/login',
                    cookie='session=owned-session; Path=/; Secure; HttpOnly; SameSite=Lax' if valid and state['mode'] != 'no-cookie' else None)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(ca, private)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        original = subprocess.Popen
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
                     ('deadline', 'slow', DemoLoginScenario.ACCEPTED, TestStatus.ERROR)]
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
egress.resolve_with_deadline=lambda *args,**kwargs: ('93.184.216.34',)
def owned(guard,target,**kwargs):
    assert not guard.local_sample and target.hostname=='the-internet.herokuapp.com'
    assert target.port==443 and target.addresses==('93.184.216.34',)
    return socket.create_connection(('127.0.0.1',{server.server_port}),timeout=2)
egress.DestinationGuard.connect=owned
original=ssl.create_default_context
if {mode != 'untrusted'!r}: ssl.create_default_context=lambda:original(cafile={str(ca)!r})
sys.argv=['owned-demo-proof']+sys.argv[1:]
worker.main()
'''
                def spawn(command, **options):
                    if 'adaptive_qa.demo_login_process' not in command: return original(command, **options)
                    source = Path(command[command.index('--input')+1]); roots.append(source.parent)
                    assert 'password' not in source.read_text() and 'SSLKEYLOGFILE' not in options['env']
                    return original([sys.executable, '-c', wrapper, *command[3:]], **options)
                with patch('adaptive_qa.public_submission_process.subprocess.Popen', side_effect=spawn):
                    result = run_isolated_demo_login(DemoLoginPlan(scenario), timeout_seconds=2 if mode=='slow' else 30,
                                                    should_cancel=(lambda: True) if label=='cancelled' else None)
                assert result.status == expected, (label, result, {k:state[k] for k in ('posts','documents','bad','session')})
                assert all(not directory.exists() for directory in roots), (label, 'profile retained')
                posts = state['posts']-before
                assert posts <= 1 and not state['bad'], (label, posts, state['bad'])
                if expected == TestStatus.PASSED: assert posts == 1
                if label in ('missing', 'untrusted', 'cancelled'): assert posts == 0
                records.append(dict(scenario=label, status=result.status.value, owned_posts=posts,
                                    private_profile_removed=True))
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)
    report = dict(scenarios=records, installed_wheel=bool(INSTALLED), supervised_child_package_verified=bool(INSTALLED),
                  owned_tls_only=True, external_demo_contacted=False, customer_targets_contacted=False,
                  production_tls_override_exposed=False, raw_credentials_or_cookies_saved=False,
                  screenshots_or_traces=False, private_profiles_removed=True)
    output = Path('artifacts/demo-login'); output.mkdir(parents=True, exist_ok=True)
    (output/'browser.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
