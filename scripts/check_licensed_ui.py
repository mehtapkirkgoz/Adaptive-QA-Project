"""Owned loopback browser proof for local license import and preserved workspace."""
import base64
from contextlib import closing
import hashlib
import sqlite3
from functools import partial
from http.server import ThreadingHTTPServer
import subprocess
import sys
import os
from dataclasses import asdict
import json
from pathlib import Path
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
from adaptive_qa.local_backup import create_local_backup, restore_local_backup
UI_DIRECTORY = os.environ.get('ADAPTIVE_QA_VERIFY_UI', 'frontend/dist')
FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1]/'samples/web'

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from playwright.sync_api import sync_playwright, expect
import uvicorn
from adaptive_qa.auth_store import AuthStore
from adaptive_qa.license_store import LicenseStore
from adaptive_qa.licensing import LicenseClaims, license_message
from adaptive_qa.local_free import LOCAL_ACTOR, LocalFreeProjects
from adaptive_qa.local_licensed import create_licensed_app
from adaptive_qa.project_settings import reference_name


def main():
    origin = 'http://127.0.0.1:8882'
    api_contacts=[]
    class ApiFixture(QuietHandler):
        def do_GET(self):
            if self.path!='/paid/readiness':return super().do_GET()
            api_contacts.append('GET');raw=b'{"available":false}'
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    with TemporaryDirectory(prefix='adaptive-license-ui-') as temporary:
        root = Path(temporary)/'workspace'; root.mkdir()
        private = Ed25519PrivateKey.generate()
        licenses = LicenseStore(root/'license.sqlite', {'test':private.public_key().public_bytes_raw()})
        trust = root/'public-keys.json'
        trust.write_text(json.dumps({'test':private.public_key().public_bytes_raw().hex()}),encoding='utf-8')
        now = int(time.time())
        payload = asdict(LicenseClaims('a'*32,'b'*32,now-10,now-10,now+3600,3,1))
        signature = base64.urlsafe_b64encode(private.sign(license_message('test',payload))).rstrip(b'=').decode()
        document = json.dumps(dict(key_id='test',payload=payload,signature=signature))
        auth = AuthStore(root/'auth.sqlite')
        administrator = auth.create_user('owner@example.test','local browser password')
        LocalFreeProjects(root/'projects.sqlite').create(LOCAL_ACTOR,'Preserved free site')
        server = uvicorn.Server(uvicorn.Config(create_licensed_app(root/'projects.sqlite',auth,administrator,licenses,
            port=8882,ui_directory=UI_DIRECTORY),host='127.0.0.1',port=8882,log_level='critical',access_log=False))
        thread = Thread(target=server.run,daemon=True); thread.start()
        fixture = ThreadingHTTPServer(('127.0.0.1',8000),partial(ApiFixture,directory=str(FIXTURE_DIRECTORY)))
        fixture_thread = Thread(target=fixture.serve_forever,daemon=True); fixture_thread.start()
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
                    page.get_by_role('button',name='Preserved free site Project configuration').click()
                    page.get_by_label('Target URL',exact=True).fill('http://127.0.0.1:8000/')
                    page.get_by_label('Allowed hosts',exact=True).fill('127.0.0.1')
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    page.get_by_role('button',name='Queue local discovery',exact=True).click()
                    expect(page.get_by_text('queued',exact=True)).to_be_visible()
                    def worker(expected_queue,command='worker-cycle'):
                        prefix = [sys.executable,'-m','adaptive_qa']
                        if INSTALLED_SITE:
                            prefix = [sys.executable,'-I','-c',
                                'import sys; sys.path.insert(0,sys.argv.pop(1)); from adaptive_qa.__main__ import main; main()',INSTALLED_SITE]
                        result = subprocess.run([*prefix,'local',command,'--workspace',str(root),
                            '--trusted-keys',str(trust)],check=True,timeout=120,capture_output=True)
                        outcome = json.loads(result.stdout)
                        if command in ('api-once','database-once'):assert outcome['status']=='completed'
                        else:
                            assert outcome[expected_queue]['status']=='completed'
                            assert all(value is None for name,value in outcome.items() if name!=expected_queue)
                    worker('discovery')
                    page.get_by_role('button',name='Review discovery plan',exact=True).click()
                    runs = page.get_by_label('Test runs',exact=True)
                    runs.get_by_label('Select LOGIN-001',exact=True).check()
                    runs.get_by_role('button',name='Start selected tests',exact=True).click()
                    expect(runs.get_by_text('Run queued',exact=True)).to_be_visible()
                    worker('run')
                    expect(runs.locator('.run-outcome').filter(has_text='LOGIN-001')).to_contain_text('passed',timeout=10000)
                    editor=page.get_by_role('region',name='Explicit local API binding')
                    editor.get_by_role('checkbox',name='Configure explicit API response').check()
                    editor.get_by_label('GET endpoint path',exact=True).fill('/paid/readiness')
                    editor.get_by_label('API JSON boolean field',exact=True).fill('available')
                    editor.get_by_label('Expected API boolean',exact=True).select_option('false')
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    api_panel=page.get_by_role('region',name='Explicit API execution')
                    api_panel.get_by_role('button',name='Review saved API binding',exact=True).click()
                    expect(api_panel.get_by_label('API review confirmation')).to_be_visible()
                    assert api_contacts==[]
                    api_panel.get_by_role('checkbox',name='I authorize one GET request to my owned local API.').check()
                    api_panel.get_by_role('button',name='Queue one API request',exact=True).click()
                    expect(api_panel.get_by_role('button',name='Cancel API job',exact=True)).to_be_visible()
                    worker(None,'api-once')
                    expect(api_panel.get_by_text('API result: passed',exact=True)).to_be_visible(timeout=10000)
                    assert api_contacts==['GET']
                    project=LocalFreeProjects(root/'projects.sqlite').list(LOCAL_ACTOR)[0]
                    owned_root=root/'database-fixtures'/project.project_id
                    owned_root.mkdir(parents=True)
                    database_fixture=owned_root/'owned.sqlite'
                    with closing(sqlite3.connect(database_fixture)) as connection:
                        with connection:
                            connection.execute('CREATE TABLE inventory (id INTEGER)')
                    database_digest=hashlib.sha256(database_fixture.read_bytes()).hexdigest()
                    db_editor=page.get_by_role('region',name='Explicit local database binding')
                    db_editor.get_by_role('checkbox',name='Configure explicit database count').check()
                    page.get_by_role('checkbox',name='database path',exact=False).check()
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    db_panel=page.get_by_role('region',name='Explicit database execution')
                    db_panel.get_by_role('button',name='Review saved database count',exact=True).click()
                    expect(db_panel.get_by_role('button',name='Queue one database count',exact=True)).to_be_disabled()
                    db_panel.get_by_role('checkbox',name='I authorize one read-only count on my owned SQLite fixture.').check()
                    db_panel.get_by_role('button',name='Queue one database count',exact=True).click()
                    expect(db_panel.get_by_role('button',name='Cancel database job',exact=True)).to_be_visible()
                    reference=reference_name(LOCAL_ACTOR.user_id,project.project_id,'database_path')
                    previous=os.environ.get(reference)
                    try:
                        os.environ[reference]=str(database_fixture)
                        worker(None,'database-once')
                    finally:
                        if previous is None:os.environ.pop(reference,None)
                        else:os.environ[reference]=previous
                    expect(db_panel.get_by_text('database result: passed',exact=True)).to_be_visible(timeout=10000)
                    assert hashlib.sha256(database_fixture.read_bytes()).hexdigest()==database_digest
                    page.context.clear_cookies()
                    api_panel.get_by_role('button',name='Review saved API binding',exact=True).click()
                    expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
                    expect(page.get_by_role('button',name='Reopen workspace',exact=True)).to_have_count(0)
                    page.get_by_label('Email',exact=True).fill('owner@example.test')
                    page.get_by_label('Password',exact=True).fill('local browser password')
                    page.get_by_role('button',name='Sign in',exact=True).click()
                    expect(page.get_by_role('region',name='Local license')).to_contain_text('License: valid')
                    page.reload()
                    expect(page.get_by_role('region',name='Local license')).to_contain_text('License: valid')
                    server.should_exit=True; thread.join(timeout=10)
                    assert not thread.is_alive()
                    snapshot,recovered = Path(temporary)/'snapshot',Path(temporary)/'recovered'
                    create_local_backup(root,snapshot,maintenance_confirmed=True)
                    restore_local_backup(snapshot,recovered,maintenance_confirmed=True)
                    assert not (recovered/'database-fixtures').exists()
                    restored_auth = AuthStore(recovered/'auth.sqlite')
                    restored_licenses = LicenseStore(recovered/'license.sqlite',{'test':private.public_key().public_bytes_raw()})
                    restored_app = create_licensed_app(recovered/'projects.sqlite',restored_auth,administrator,restored_licenses,
                        port=8882,ui_directory=UI_DIRECTORY)
                    server = uvicorn.Server(uvicorn.Config(restored_app,host='127.0.0.1',port=8882,log_level='critical',access_log=False))
                    thread = Thread(target=server.run,daemon=True); thread.start()
                    deadline = time.monotonic()+10
                    while not server.started:
                        if not thread.is_alive() or time.monotonic()>deadline: raise RuntimeError('Recovery server did not start.')
                        time.sleep(.05)
                    page.reload()
                    expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
                    page.get_by_label('Email',exact=True).fill('owner@example.test')
                    page.get_by_label('Password',exact=True).fill('local browser password')
                    page.get_by_role('button',name='Sign in',exact=True).click()
                    expect(page.get_by_role('region',name='Local license')).to_contain_text('License: valid')
                    page.get_by_role('button',name='Preserved free site Project configuration').click()
                    expect(page.get_by_label('Test runs',exact=True).locator('.run-outcome').filter(has_text='LOGIN-001')).to_contain_text('passed')
                    expect(page.get_by_role('region',name='Explicit API execution').get_by_text('API result: passed',exact=True)).to_be_visible()
                    expect(page.get_by_role('region',name='Explicit database execution').get_by_text('database result: passed',exact=True)).to_be_visible()
                    expect(page.get_by_label('Expected database record count',exact=True)).to_have_value('0')
                    assert not errors and not external
                finally: browser.close()
        finally:
            server.should_exit=True; thread.join(timeout=10)
            fixture.shutdown(); fixture.server_close(); fixture_thread.join(timeout=5)
            assert not thread.is_alive()
    output = Path('artifacts/local-license'); output.mkdir(parents=True,exist_ok=True)
    report = dict(local_only=True,worker_entrypoint='local worker-cycle',api_worker_entrypoint='local api-once',
        api_ui_confirmed_result='passed',api_requests=len(api_contacts),api_result_preserved_after_recovery=True,
        database_worker_entrypoint='local database-once',database_ui_confirmed_result='passed',
        database_fixture_unchanged=True,database_result_preserved_after_recovery=True,database_fixture_not_in_backup=True,
        nested_panel_session_loss_requires_password=True,
        upgrade_preserved=True,valid_import=True,invalid_import_preserved=True,
        authenticated_reload=True,recovery_requires_fresh_login=True,recovered_results_and_license=True,installed_wheel=bool(INSTALLED_SITE),licensed_cli_discovery_and_login_passed=True,page_errors=errors,external_requests=len(external))
    (output/'ui.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__': main()
