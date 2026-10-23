"""Owned loopback browser proof for local license import and preserved workspace."""
import base64
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from playwright.sync_api import sync_playwright, expect
import uvicorn
from adaptive_qa.auth_store import AuthStore
from adaptive_qa.license_store import LicenseStore
from adaptive_qa.licensing import LicenseClaims, license_message
from adaptive_qa.local_free import LOCAL_ACTOR, LocalFreeProjects
from adaptive_qa.local_licensed import create_licensed_app


def main():
    origin = 'http://127.0.0.1:8882'
    with TemporaryDirectory(prefix='adaptive-license-ui-') as temporary:
        root = Path(temporary)
        private = Ed25519PrivateKey.generate()
        licenses = LicenseStore(root/'license.sqlite', {'test':private.public_key().public_bytes_raw()})
        now = int(time.time())
        payload = asdict(LicenseClaims('a'*32,'b'*32,now-10,now-10,now+3600,3,1))
        signature = base64.urlsafe_b64encode(private.sign(license_message('test',payload))).rstrip(b'=').decode()
        document = json.dumps(dict(key_id='test',payload=payload,signature=signature))
        auth = AuthStore(root/'auth.sqlite')
        administrator = auth.create_user('owner@example.test','local browser password')
        LocalFreeProjects(root/'projects.sqlite').create(LOCAL_ACTOR,'Preserved free site')
        server = uvicorn.Server(uvicorn.Config(create_licensed_app(root/'projects.sqlite',auth,administrator,licenses,
            port=8882,ui_directory='frontend/dist'),host='127.0.0.1',port=8882,log_level='critical',access_log=False))
        thread = Thread(target=server.run,daemon=True); thread.start()
        errors, external = [], []
        try:
            deadline = time.monotonic()+10
            while not server.started:
                if not thread.is_alive() or time.monotonic()>deadline: raise RuntimeError('Owned server did not start.')
                time.sleep(.05)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    page = browser.new_page(viewport={'width':1440,'height':1000})
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.on('request',lambda request:external.append(request.url) if not request.url.startswith(origin+'/') else None)
                    page.goto(origin+'/')
                    page.get_by_label('Email',exact=True).fill('owner@example.test')
                    page.get_by_label('Password',exact=True).fill('local browser password')
                    page.get_by_role('button',name='Sign in',exact=True).click()
                    panel = page.get_by_role('region',name='Local license')
                    expect(panel).to_contain_text('License: absent')
                    expect(page.get_by_role('button',name='Organizations',exact=True)).to_have_count(0)
                    expect(page.get_by_role('button',name='Preserved free site Project configuration')).to_be_visible()
                    panel.get_by_label('Signed license document',exact=True).fill(document)
                    panel.get_by_role('button',name='Install license',exact=True).click()
                    expect(panel).to_contain_text('Verified license installed.')
                    expect(panel).to_contain_text('Project limit: 3')
                    panel.get_by_label('Signed license document',exact=True).fill('{}')
                    panel.get_by_role('button',name='Install license',exact=True).click()
                    expect(panel).to_contain_text('The previous license was preserved.')
                    expect(panel).to_contain_text('License: valid')
                    page.reload()
                    expect(page.get_by_role('region',name='Local license')).to_contain_text('License: valid')
                    assert not errors and not external
                finally: browser.close()
        finally:
            server.should_exit=True; thread.join(timeout=10)
            assert not thread.is_alive()
    output = Path('artifacts/local-license'); output.mkdir(parents=True,exist_ok=True)
    report = dict(local_only=True,upgrade_preserved=True,valid_import=True,invalid_import_preserved=True,
        authenticated_reload=True,page_errors=errors,external_requests=len(external))
    (output/'ui.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__': main()
