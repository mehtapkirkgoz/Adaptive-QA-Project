"""Account-free UI and real local execution without central data or account storage."""
from functools import partial
from contextlib import closing
import hashlib
import os
import sqlite3
from http.server import ThreadingHTTPServer
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
import time

import uvicorn
from playwright.sync_api import sync_playwright, expect
from adaptive_qa.local_free import create_free_app, LocalFreeProjects, LOCAL_ACTOR
from adaptive_qa.project_settings import reference_name
from check_dashboard_runs import QuietHandler


def main():
    origin = 'http://127.0.0.1:8881'
    api_contacts=[]
    class ApiFixture(QuietHandler):
        def do_GET(self):
            if self.path!='/service/available': return super().do_GET()
            api_contacts.append('GET')
            raw=b'{"available":true}'
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    with TemporaryDirectory(prefix='adaptive-free-ui-') as temporary:
        root = Path(temporary)
        database = root/'projects.sqlite'
        def cycle():
            result = subprocess.run([sys.executable, '-m', 'adaptive_qa', 'dashboard',
                'free-worker-cycle', '--database', str(database)],
                capture_output=True, check=True, timeout=120)
            return json.loads(result.stdout)
        server = uvicorn.Server(uvicorn.Config(create_free_app(database, port=8881, ui_directory='frontend/dist'),
            host='127.0.0.1', port=8881, log_level='critical', access_log=False, proxy_headers=False))
        thread = Thread(target=server.run, daemon=True); thread.start()
        fixture = ThreadingHTTPServer(('127.0.0.1', 8000), partial(ApiFixture, directory='samples/web'))
        fixture_thread = Thread(target=fixture.serve_forever, daemon=True); fixture_thread.start()
        external, errors = [], []
        try:
            deadline = time.monotonic()+10
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError('Owned free server did not start.')
                time.sleep(.05)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('request', lambda request: external.append(request.url) if not request.url.startswith(origin+'/') else None)
                    page.goto(origin+'/#advanced')
                    expect(page.get_by_text('FREE · LOCAL', exact=True)).to_be_visible()
                    expect(page.get_by_role('heading', name='Sign in', exact=True)).to_have_count(0)
                    expect(page.get_by_role('button', name='Organizations', exact=True)).to_have_count(0)
                    page.get_by_label('New project name', exact=True).fill('Free local target')
                    page.get_by_role('button', name='+ Create project', exact=True).click()
                    expect(page.get_by_role('button', name='+ Create project', exact=True)).to_be_disabled()
                    page.get_by_role('button', name='Free local target Project configuration').click()
                    page.get_by_label('Target URL', exact=True).fill('http://127.0.0.1:8000/')
                    page.get_by_label('Allowed hosts', exact=True).fill('127.0.0.1')
                    page.get_by_role('button', name='Save configuration', exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    page.get_by_label('Target URL',exact=True).fill('http://127.0.0.1:8000/variants/english.html')
                    expect(page.get_by_role('button',name='Queue local discovery',exact=True)).to_be_disabled()
                    held_save=[]
                    def delay_save(route):
                        if route.request.method=='PUT':held_save.append(route)
                        else:route.continue_()
                    page.route('**/configuration',delay_save)
                    with page.expect_request(lambda request:request.method=='PUT' and request.url.endswith('/configuration')):
                        page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_role('button',name='Queue local discovery',exact=True)).to_be_disabled()
                    assert len(held_save)==1
                    held_save[0].continue_()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    page.unroute('**/configuration',delay_save)
                    page.get_by_label('Target URL',exact=True).fill('http://127.0.0.1:8000/')
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    page.get_by_role('button', name='Queue local discovery', exact=True).click()
                    expect(page.get_by_text('queued', exact=True)).to_be_visible()
                    projects = LocalFreeProjects(database)
                    outcome = cycle()
                    assert outcome['discovery']['status'] == 'completed'
                    assert outcome['run'] is None and outcome['interactive'] is None
                    page.get_by_role('button', name='Review discovery plan', exact=True).click()
                    runs = page.get_by_label('Test runs', exact=True)
                    runs.get_by_label('Select LOGIN-001', exact=True).check()
                    runs.get_by_role('button', name='Start selected tests', exact=True).click()
                    expect(runs.get_by_text('Run queued', exact=True)).to_be_visible()
                    outcome = cycle()
                    assert outcome['run']['status'] == 'completed'
                    assert outcome['discovery'] is None and outcome['interactive'] is None
                    expect(runs.locator('.run-outcome').filter(has_text='LOGIN-001')).to_contain_text('passed', timeout=10000)
                    saved_project = projects.list(LOCAL_ACTOR)[0]
                    binding = dict(path='/service/available', expected_status=200, json_field='available', expected_boolean=True)
                    history_failures={'api':0,'database':0}
                    def unavailable_history(route):
                        profile='database' if '/local-database/' in route.request.url else 'api'
                        if route.request.method=='GET' and not history_failures[profile]:
                            history_failures[profile]+=1
                            route.fulfill(status=503,content_type='application/json',body='{}')
                        else:route.continue_()
                    page.route('**/local-api/jobs',unavailable_history)
                    editor=page.get_by_role('region',name='Explicit local API binding')
                    editor.get_by_role('checkbox',name='Configure explicit API response').check()
                    status_input=editor.get_by_label('Expected API HTTP status',exact=True)
                    status_input.fill('')
                    expect(status_input).to_have_value('')
                    assert not status_input.evaluate('(input) => input.checkValidity()')
                    status_input.fill('302')
                    assert not status_input.evaluate('(input) => input.checkValidity()')
                    status_input.fill('200')
                    assert status_input.evaluate('(input) => input.checkValidity()')
                    editor.get_by_label('GET endpoint path',exact=True).fill(binding['path'])
                    editor.get_by_label('API JSON boolean field',exact=True).fill(binding['json_field'])
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    api_panel=page.get_by_role('region',name='Explicit API execution')
                    expect(api_panel.get_by_text('API history is unavailable. Refresh history before confirming another job.',exact=True)).to_be_visible()
                    expect(api_panel.get_by_text('No API jobs yet.',exact=True)).to_have_count(0)
                    api_panel.get_by_role('button',name='Review saved API binding',exact=True).click()
                    expect(api_panel.get_by_label('API review confirmation')).to_be_visible()
                    editor.get_by_label('API JSON boolean field',exact=True).fill('changed')
                    expect(api_panel.get_by_label('API review confirmation')).to_have_count(0)
                    expect(api_panel.get_by_role('button',name='Review saved API binding',exact=True)).to_be_disabled()
                    editor.get_by_label('API JSON boolean field',exact=True).fill(binding['json_field'])
                    api_panel.get_by_role('button',name='Review saved API binding',exact=True).click()
                    assert api_contacts==[]
                    api_panel.get_by_role('checkbox',name='I authorize one GET request to my owned local API.').check()
                    expect(api_panel.get_by_role('button',name='Queue one API request',exact=True)).to_be_disabled()
                    api_panel.get_by_role('button',name='Refresh API history',exact=True).click()
                    expect(api_panel.get_by_role('button',name='Queue one API request',exact=True)).to_be_enabled()
                    page.unroute('**/local-api/jobs',unavailable_history)
                    api_panel.get_by_role('button',name='Queue one API request',exact=True).click()
                    expect(api_panel.get_by_role('button',name='Cancel API job',exact=True)).to_be_visible()
                    result=subprocess.run([sys.executable,'-m','adaptive_qa','dashboard','free-api-once',
                        '--database',str(database)],capture_output=True,check=True,timeout=45)
                    assert json.loads(result.stdout)['status']=='completed' and api_contacts==['GET']
                    expect(api_panel.get_by_text('API result: passed',exact=True)).to_be_visible(timeout=10000)
                    api_panel.get_by_role('button',name='Review saved API binding',exact=True).click()
                    api_panel.get_by_role('checkbox',name='I authorize one GET request to my owned local API.').check()
                    api_panel.get_by_role('button',name='Queue one API request',exact=True).click()
                    api_panel.get_by_role('button',name='Cancel API job',exact=True).click()
                    expect(api_panel.get_by_text('cancelled',exact=True)).to_be_visible()
                    assert api_contacts==['GET']
                    page.set_viewport_size(dict(width=390,height=900))
                    api_panel.get_by_text('Run an API worker locally',exact=True).click()
                    expect(api_panel.get_by_text('python -m adaptive_qa dashboard free-api-once',exact=False)).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    screenshot=Path('artifacts/local-free/api-panel-mobile.png');screenshot.parent.mkdir(parents=True,exist_ok=True)
                    api_panel.screenshot(path=str(screenshot))
                    page.set_viewport_size(dict(width=1440,height=1000))
                    page.reload()
                    expect(page.get_by_role('button', name='+ Create project', exact=True)).to_be_disabled()
                    expect(page.get_by_role('button', name='Free local target Project configuration')).to_be_visible()
                    page.get_by_role('button', name='Free local target Project configuration').click()
                    page.get_by_role('button', name='Save configuration', exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.', exact=True)).to_be_visible()
                    assert projects.configuration(LOCAL_ACTOR, saved_project.project_id)['local_api_binding'] == binding
                    editor=page.get_by_role('region',name='Explicit local API binding')
                    expect(editor.get_by_label('GET endpoint path',exact=True)).to_have_value(binding['path'])
                    editor.get_by_role('checkbox',name='Configure explicit API response').uncheck()
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    assert 'local_api_binding' not in projects.configuration(LOCAL_ACTOR,saved_project.project_id)
                    with projects._connection() as c:
                        assert c.execute('SELECT count(*) FROM dashboard_api_jobs').fetchone()[0]==2
                    database_binding=dict(table='inventory',expected_count=3)
                    page.route('**/local-database/jobs',unavailable_history)
                    fixture_root=root/'database-fixtures'/saved_project.project_id
                    fixture_root.mkdir(parents=True)
                    fixture_path=fixture_root/'owned.sqlite'
                    with closing(sqlite3.connect(fixture_path)) as connection:
                        with connection:
                            connection.execute('CREATE TABLE inventory (id INTEGER)')
                            connection.executemany('INSERT INTO inventory VALUES (?)',[(1,),(2,),(3,)])
                    fixture_digest=hashlib.sha256(fixture_path.read_bytes()).hexdigest()
                    db_editor=page.get_by_role('region',name='Explicit local database binding')
                    db_editor.get_by_role('checkbox',name='Configure explicit database count').check()
                    count_input=db_editor.get_by_label('Expected database record count',exact=True)
                    count_input.fill('')
                    expect(count_input).to_have_value('')
                    assert not count_input.evaluate('(input) => input.checkValidity()')
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    assert 'local_database_binding' not in projects.configuration(LOCAL_ACTOR,saved_project.project_id)
                    db_editor.get_by_label('Expected database record count',exact=True).fill('3')
                    page.get_by_role('checkbox',name='database path',exact=False).check()
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    db_panel=page.get_by_role('region',name='Explicit database execution')
                    expect(db_panel.get_by_text('Database history is unavailable. Refresh history before confirming another job.',exact=True)).to_be_visible()
                    expect(db_panel.get_by_text('No database jobs yet.',exact=True)).to_have_count(0)
                    db_panel.get_by_role('button',name='Review saved database count',exact=True).click()
                    expect(db_panel.get_by_label('database review confirmation')).to_be_visible()
                    db_editor.get_by_label('Expected database record count',exact=True).fill('4')
                    expect(db_panel.get_by_label('database review confirmation')).to_have_count(0)
                    expect(db_panel.get_by_role('button',name='Review saved database count',exact=True)).to_be_disabled()
                    db_editor.get_by_label('Expected database record count',exact=True).fill('3')
                    db_panel.get_by_role('button',name='Review saved database count',exact=True).click()
                    expect(db_panel.get_by_role('button',name='Queue one database count',exact=True)).to_be_disabled()
                    db_panel.get_by_role('checkbox',name='I authorize one read-only count on my owned SQLite fixture.').check()
                    expect(db_panel.get_by_role('button',name='Queue one database count',exact=True)).to_be_disabled()
                    db_panel.get_by_role('button',name='Refresh database history',exact=True).click()
                    expect(db_panel.get_by_role('button',name='Queue one database count',exact=True)).to_be_enabled()
                    page.unroute('**/local-database/jobs',unavailable_history)
                    db_panel.get_by_role('button',name='Queue one database count',exact=True).click()
                    expect(db_panel.get_by_role('button',name='Cancel database job',exact=True)).to_be_visible()
                    database_reference=reference_name(LOCAL_ACTOR.user_id,saved_project.project_id,'database_path')
                    with patch.dict(os.environ,{database_reference:str(fixture_path)}):
                        result=subprocess.run([sys.executable,'-m','adaptive_qa','dashboard','free-database-once',
                            '--database',str(database)],capture_output=True,check=True,timeout=45)
                    assert json.loads(result.stdout)['status']=='completed'
                    expect(db_panel.get_by_text('database result: passed',exact=True)).to_be_visible(timeout=10000)
                    db_panel.get_by_role('button',name='Review saved database count',exact=True).click()
                    db_panel.get_by_role('checkbox',name='I authorize one read-only count on my owned SQLite fixture.').check()
                    db_panel.get_by_role('button',name='Queue one database count',exact=True).click()
                    db_panel.get_by_role('button',name='Cancel database job',exact=True).click()
                    expect(db_panel.get_by_text('cancelled',exact=True)).to_be_visible()
                    page.set_viewport_size(dict(width=390,height=900))
                    db_panel.get_by_text('Run a database worker locally',exact=True).click()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    db_panel.screenshot(path='artifacts/local-free/database-panel-mobile.png')
                    page.set_viewport_size(dict(width=1440,height=1000))
                    page.reload()
                    page.get_by_role('button',name='Free local target Project configuration').click()
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    assert projects.configuration(LOCAL_ACTOR,saved_project.project_id)['local_database_binding']==database_binding
                    page.get_by_role('checkbox',name='Configure explicit database count').uncheck()
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    assert 'local_database_binding' not in projects.configuration(LOCAL_ACTOR,saved_project.project_id)
                    assert hashlib.sha256(fixture_path.read_bytes()).hexdigest()==fixture_digest
                    saves=[]
                    page.on('request',lambda request:saves.append(request.method) if request.method=='PUT' and request.url.endswith('/configuration') else None)
                    page.context.clear_cookies()
                    page.get_by_label('Target URL',exact=True).fill('http://127.0.0.1:8000/not-saved')
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_role('heading',name='Reopen local workspace',exact=True)).to_be_visible()
                    expect(page.get_by_role('heading',name='Sign in',exact=True)).to_have_count(0)
                    assert saves==['PUT']
                    page.set_viewport_size(dict(width=390,height=900))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.get_by_role('region',name='Reopen local workspace').screenshot(path='artifacts/local-free/reopen-session-mobile.png')
                    page.set_viewport_size(dict(width=1440,height=1000))
                    page.get_by_role('button',name='Reopen workspace',exact=True).click()
                    expect(page.get_by_text('Local workspace reopened. No previous request was retried. Select your project to review saved settings.',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Free local target Project configuration').click()
                    expect(page.get_by_label('Target URL',exact=True)).to_have_value('http://127.0.0.1:8000/')
                    assert saves==['PUT']
                    page.context.clear_cookies()
                    page.get_by_role('button',name='Queue local discovery',exact=True).click()
                    expect(page.get_by_role('heading',name='Reopen local workspace',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Reopen workspace',exact=True).click()
                    expect(page.get_by_role('button',name='Free local target Project configuration')).to_be_visible()
                    with projects._connection() as connection:
                        assert connection.execute('SELECT count(*) FROM dashboard_discovery_jobs').fetchone()[0]==1
                    delayed=[]
                    def hold_old_history(route):
                        delayed.append(route)
                    page.route('**/api/projects/*/runs',hold_old_history)
                    with page.expect_request(lambda request:request.method=='GET' and request.url.endswith('/runs')):
                        page.get_by_role('button',name='Free local target Project configuration').click()
                    expect(page.get_by_role('button',name='Save configuration',exact=True)).to_be_visible()
                    assert len(delayed)==1
                    page.context.clear_cookies()
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_role('heading',name='Reopen local workspace',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Reopen workspace',exact=True).click()
                    expect(page.get_by_text('Local workspace reopened. No previous request was retried. Select your project to review saved settings.',exact=True)).to_be_visible()
                    with page.expect_response(lambda response:response.url.endswith('/runs') and response.status==401):
                        delayed[0].fulfill(status=401,content_type='application/json',body='{}')
                    page.wait_for_load_state('networkidle')
                    expect(page.get_by_role('heading',name='Project workspace',exact=True)).to_be_visible()
                    expect(page.get_by_role('heading',name='Reopen local workspace',exact=True)).to_have_count(0)
                    page.unroute('**/api/projects/*/runs',hold_old_history)
                    assert not (root/'auth.sqlite').exists()
                    with projects._connection() as connection:
                        assert not connection.execute("SELECT 1 FROM sqlite_master WHERE name='dashboard_users'").fetchone()
                    assert not external and not errors
                finally:
                    browser.close()
        finally:
            server.should_exit = True; thread.join(timeout=10)
            fixture.shutdown(); fixture.server_close(); fixture_thread.join(timeout=5)
            assert not thread.is_alive()
    output = Path('artifacts/local-free'); output.mkdir(parents=True, exist_ok=True)
    report = {'account_required': False, 'worker_entrypoint': 'dashboard free-worker-cycle',
              'one_project_cap': True, 'real_local_login_check_passed': True, 'ui_preserved_saved_api_binding': True,
              'api_editor_save_reload_remove': True, 'api_jobs_explicitly_confirmed': 2, 'api_job_cancelled_before_execution': True,
              'api_ui_cli_result': 'passed', 'api_requests': len(api_contacts), 'api_unsaved_confirmation_cleared': True,
              'ui_preserved_saved_database_binding': True,
              'database_editor_save_reload_remove': True, 'database_jobs_explicitly_confirmed': 2,
              'database_job_cancelled_before_execution': True, 'database_ui_cli_result': 'passed',
              'database_fixture_unchanged': True, 'database_unsaved_confirmation_cleared': True,
              'empty_numeric_inputs_blocked': True, 'redirect_api_expectation_blocked': True,
              'free_session_reopen_without_login_or_mutation_retry': True,
              'nested_panel_session_loss_recovered_without_requeue': True,
              'api_and_database_history_failure_blocks_admission_until_manual_refresh': True,
              'late_old_session_failure_does_not_clear_reopened_workspace': True,
              'discovery_admission_blocked_during_unsaved_and_pending_save': True,
              'auth_database_created': False, 'central_requests': len(external), 'page_errors': errors}
    (output/'ui.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
