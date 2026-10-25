"""Real one-button browser -> managed discovery -> supervised checks on an owned fixture."""
import argparse
import base64
from dataclasses import asdict
from functools import partial
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time

INSTALLED_SITE = os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if INSTALLED_SITE:
    sys.path.insert(0, str(Path(INSTALLED_SITE).resolve(strict=True)))
import adaptive_qa
if INSTALLED_SITE:
    assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(INSTALLED_SITE).resolve())
from check_dashboard_runs import QuietHandler
from playwright.sync_api import sync_playwright, expect
import uvicorn
from adaptive_qa.local_free import create_free_app


def main(licensed=False):
    origin = 'http://127.0.0.1:8892'
    artifact = Path('artifacts/site-check'); artifact.mkdir(parents=True, exist_ok=True)
    label = 'installed-licensed' if INSTALLED_SITE else 'licensed' if licensed else 'free'
    with TemporaryDirectory(prefix='adaptive-site-check-') as temporary:
        workspace = Path(temporary)
        if licensed:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from adaptive_qa.auth_store import AuthStore
            from adaptive_qa.license_store import LicenseStore
            from adaptive_qa.licensing import LicenseClaims, license_message
            from adaptive_qa.local_licensed import create_licensed_app
            key = Ed25519PrivateKey.generate()
            licenses = LicenseStore(workspace/'license.sqlite', {'fixture': key.public_key().public_bytes_raw()})
            now = int(time.time())
            payload = asdict(LicenseClaims('a'*32,'b'*32,now-10,now-10,now+3600,3,1))
            signature = base64.urlsafe_b64encode(key.sign(license_message('fixture',payload))).rstrip(b'=').decode()
            licenses.install(json.dumps(dict(key_id='fixture',payload=payload,signature=signature)).encode())
            auth = AuthStore(workspace/'auth.sqlite'); owner = auth.create_user('owner@example.test','owned browser fixture password')
            app = create_licensed_app(workspace/'projects.sqlite',auth,owner,licenses,port=8892,
                ui_directory=os.environ.get('ADAPTIVE_QA_VERIFY_UI','frontend/dist'))
        else:
            app = create_free_app(workspace/'projects.sqlite',port=8892,
                ui_directory=os.environ.get('ADAPTIVE_QA_VERIFY_UI','frontend/dist'))
        server = uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8892,log_level='critical',access_log=False))
        thread = Thread(target=server.run,daemon=True); thread.start()
        class QualityFixture(QuietHandler):
            def do_GET(self):
                if self.path != '/quality.html': return super().do_GET()
                raw=b'<html><head><title>Owned quality fixture</title></head><body><p id="duplicate">One</p><p id="duplicate">Two</p></body></html>'
                self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        fixture = ThreadingHTTPServer(('127.0.0.1',8000),partial(QualityFixture,
            directory=str(Path(__file__).resolve().parents[1]/'samples/web')))
        fixture_thread = Thread(target=fixture.serve_forever,daemon=True); fixture_thread.start()
        errors, external, admissions = [], [], []
        try:
            deadline = time.monotonic()+10
            while not server.started:
                if not thread.is_alive() or time.monotonic()>deadline: raise RuntimeError('Owned dashboard did not start.')
                time.sleep(.05)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={'width':1440,'height':1000})
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    page.on('request',lambda r:external.append(r.url) if not r.url.startswith(origin+'/') else None)
                    page.on('request',lambda r:admissions.append(r.url) if r.method=='POST' and r.url==origin+'/api/site-checks' else None)
                    page.goto(origin+'/')
                    if licensed:
                        page.get_by_label('Email',exact=True).fill('owner@example.test')
                        page.get_by_label('Password',exact=True).fill('owned browser fixture password')
                        page.get_by_role('button',name='Sign in',exact=True).click()
                    expect(page.get_by_role('heading',name='Siteni test et.',exact=True)).to_be_visible()
                    expect(page.get_by_label('Allowed hosts',exact=True)).to_have_count(0)
                    expect(page.get_by_role('button',name='+ Create project',exact=True)).to_have_count(0)
                    page.screenshot(path=str(artifact/(label+'-start.png')),full_page=True)
                    page.get_by_label('Test edilecek site adresi',exact=True).fill('http://127.0.0.1:8000/')
                    page.get_by_role('button',name='Test et',exact=True).click()
                    expect(page.get_by_role('heading',name='Kontrol tamamlandı',exact=True)).to_be_visible(timeout=160000)
                    checks = page.evaluate("async () => (await (await fetch('/api/site-checks')).json()).checks")
                    assert len(checks)==1,checks
                    check = checks[0]
                    assert check['status']=='completed' and 1<=len(check['results'])<=10
                    assert all(r['status']=='passed' for r in check['results']),check
                    assert check['requested']==len(check['results']) and check['inspected_pages']>0
                    expect(page.get_by_role('heading',name='Geçen testler · '+str(len(check['results'])),exact=True)).to_be_visible()
                    assert len(admissions)==1
                    page.reload()
                    expect(page.get_by_role('heading',name='Kontrol tamamlandı',exact=True)).to_be_visible()
                    assert len(admissions)==1,'Reload must not repeat target execution'
                    page.get_by_label('Test edilecek site adresi',exact=True).fill('http://127.0.0.1:8000/quality.html')
                    page.get_by_role('button',name='Test et',exact=True).click()
                    expect(page.get_by_role('heading',name='Başarısız testler · 2',exact=True)).to_be_visible(timeout=160000)
                    expect(page.get_by_role('heading',name='Kontrol tamamlandı',exact=True)).to_be_visible()
                    negative=page.evaluate("async () => (await (await fetch('/api/site-checks')).json()).checks[0]")
                    assert {r['case_id'] for r in negative['results'] if r['status']=='failed'}=={'DOC-002','DOC-003'},negative
                    page.screenshot(path=str(artifact/(label+'-failed.png')),full_page=True)
                    page.get_by_label('Test edilecek site adresi',exact=True).fill('http://127.0.0.1:8000/')
                    page.get_by_role('button',name='Test et',exact=True).click()
                    page.get_by_role('button',name='Durdur',exact=True).click()
                    expect(page.get_by_role('heading',name='Kontrol durduruldu',exact=True)).to_be_visible(timeout=15000)
                    assert len(admissions)==3
                    # Reopen recorded successful results without re-executing them.
                    page.get_by_role('button',name='http://127.0.0.1:8000/ Kontrol tamamlandı',exact=True).click()
                    expect(page.get_by_role('heading',name='Geçen testler · '+str(len(check['results'])),exact=True)).to_be_visible()
                    page.set_viewport_size({'width':390,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'
                    page.screenshot(path=str(artifact/(label+'-mobile.png')),full_page=True)
                    page.get_by_role('button',name='Gelişmiş ayarlar',exact=True).click()
                    expect(page.get_by_role('heading',name='Your projects',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Kolay site kontrolü',exact=True).click()
                    expect(page.get_by_role('heading',name='Kontrol durduruldu',exact=True)).to_be_visible()
                    assert len(admissions)==3
                    assert not external and not errors,(external,errors)
                    report=dict(licensed=licensed,installed_wheel=bool(INSTALLED_SITE),one_click_admissions=1,
                        explicit_check_requests=3,failed_checks_shown_separately=True,cancellation_verified=True,managed_workers=True,manual_worker_commands=0,recorded_results=len(check['results']),
                        inspected_pages=check['inspected_pages'],all_recorded_passed=True,reload_did_not_replay=True,
                        advanced_controls_preserved=True,mobile_overflow=False,ui_external_requests=0,page_errors=[],
                        target_scope='owned_controlled_loopback_fixture',customer_deployment_verified=False)
                    (artifact/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
                    print(json.dumps(report))
                finally: browser.close()
        finally:
            server.should_exit=True;thread.join(10);fixture.shutdown();fixture.server_close();fixture_thread.join(5)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--licensed',action='store_true')
    main(parser.parse_args().licensed)
