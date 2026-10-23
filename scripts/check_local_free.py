"""Account-free UI and real local execution without central data or account storage."""
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time

import uvicorn
from playwright.sync_api import sync_playwright, expect
from adaptive_qa.local_free import create_free_app, LocalFreeProjects
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.dashboard_run_worker import process_run_once
from check_dashboard_runs import QuietHandler


def main():
    origin = 'http://127.0.0.1:8881'
    with TemporaryDirectory(prefix='adaptive-free-ui-') as temporary:
        root = Path(temporary)
        database = root/'projects.sqlite'
        server = uvicorn.Server(uvicorn.Config(create_free_app(database, port=8881, ui_directory='frontend/dist'),
            host='127.0.0.1', port=8881, log_level='critical', access_log=False, proxy_headers=False))
        thread = Thread(target=server.run, daemon=True); thread.start()
        fixture = ThreadingHTTPServer(('127.0.0.1', 8000), partial(QuietHandler, directory='samples/web'))
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
                    page.goto(origin+'/')
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
                    page.get_by_role('button', name='Queue local discovery', exact=True).click()
                    expect(page.get_by_text('queued', exact=True)).to_be_visible()
                    projects = LocalFreeProjects(database)
                    assert process_discovery_once(DashboardDiscoveryQueue(projects))['status'] == 'completed'
                    page.get_by_role('button', name='Review discovery plan', exact=True).click()
                    runs = page.get_by_label('Test runs', exact=True)
                    runs.get_by_label('Select LOGIN-001', exact=True).check()
                    runs.get_by_role('button', name='Start selected tests', exact=True).click()
                    expect(runs.get_by_text('Run queued', exact=True)).to_be_visible()
                    assert process_run_once(DashboardRunQueue(projects))['status'] == 'completed'
                    expect(runs.locator('.run-outcome').filter(has_text='LOGIN-001')).to_contain_text('passed', timeout=10000)
                    page.reload()
                    expect(page.get_by_role('button', name='+ Create project', exact=True)).to_be_disabled()
                    expect(page.get_by_role('button', name='Free local target Project configuration')).to_be_visible()
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
    report = {'account_required': False, 'one_project_cap': True, 'real_local_login_check_passed': True,
              'auth_database_created': False, 'central_requests': len(external), 'page_errors': errors}
    (output/'ui.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
