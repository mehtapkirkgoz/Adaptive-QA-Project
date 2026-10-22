"""Real built React dashboard against temporary owned local accounts and storage."""

import json
import os
import subprocess
import sys
from http.server import ThreadingHTTPServer
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time

from playwright.sync_api import sync_playwright, expect
import uvicorn

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.project_store import ProjectStore
from adaptive_qa.web_app import create_app
from adaptive_qa.browser_process import _terminate_process_tree
from check_dashboard_runs import QuietHandler


def main():
    output = Path('artifacts/dashboard')
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as directory:
        auth = AuthStore(Path(directory) / 'auth.sqlite')
        auth.create_user('dashboard@example.test', 'Local dashboard password 123!')
        other = auth.create_user('other@example.test', 'Other dashboard password 123!')
        projects = ProjectStore(Path(directory) / 'projects.sqlite')
        projects.create(other, 'Other owner private project')
        app = create_app(auth, projects=projects, ui_directory=Path('frontend/dist'))
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=8765,
            log_level='critical', access_log=False, proxy_headers=False))
        thread = Thread(target=server.run, daemon=True)
        thread.start()
        errors, external = [], []
        fixture, fixture_thread, worker = None, None, None
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() >= deadline:
                    raise RuntimeError('Owned dashboard server did not start.')
                time.sleep(0.05)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('request', lambda request: external.append(request.url)
                            if not request.url.startswith('http://127.0.0.1:8765/') else None)
                    page.goto('http://127.0.0.1:8765/', timeout=10000)
                    expect(page.get_by_role('heading', name='Sign in', exact=True)).to_be_visible()
                    page.get_by_label('Email', exact=True).fill('dashboard@example.test')
                    page.get_by_label('Password', exact=True).fill('Wrong dashboard password 123!')
                    page.get_by_role('button', name='Sign in', exact=True).click()
                    expect(page.get_by_role('alert')).to_be_visible()
                    expect(page.get_by_label('Password', exact=True)).to_have_value('')
                    page.get_by_label('Email', exact=True).fill('dashboard@example.test')
                    page.get_by_label('Password', exact=True).fill('Local dashboard password 123!')
                    page.get_by_role('button', name='Sign in', exact=True).click()
                    expect(page.get_by_role('heading', name='Project workspace')).to_be_visible()
                    expect(page.get_by_text('Other owner private project')).to_have_count(0)
                    page.get_by_label('New project name').fill('Storefront QA')
                    page.get_by_role('button', name='+ Create project', exact=True).click()
                    page.get_by_role('button', name='Storefront QA Project configuration').click()
                    page.get_by_label('Project name', exact=True).fill('Storefront regression')
                    page.get_by_role('button', name='Rename', exact=True).click()
                    expect(page.get_by_role('status')).to_have_text('Project name saved.')
                    page.get_by_label('Target URL').fill('http://127.0.0.1:8000/')
                    page.get_by_label('Allowed hosts').fill('127.0.0.1')
                    page.get_by_label('login password', exact=True).check()
                    page.get_by_role('button', name='Save configuration', exact=True).click()
                    expect(page.get_by_role('status')).to_have_text('Configuration saved. No tests were started.')
                    page.reload()
                    page.get_by_role('button', name='Storefront regression Project configuration').click()
                    expect(page.get_by_label('Target URL')).to_have_value('http://127.0.0.1:8000/')
                    expect(page.get_by_label('Allow tests that change data')).not_to_be_checked()
                    expect(page.get_by_label('login password', exact=False)).to_be_checked()
                    expect(page.get_by_text('[REDACTED]', exact=True)).to_be_visible()
                    page.get_by_role('button', name='Review saved plan', exact=True).click()
                    review = page.get_by_label('Plan review results')
                    expect(review).to_contain_text('Catalog: 86 · Selected: 0 · Skipped: 0 · Blocked: 86')
                    expect(review).to_contain_text('Execution authorized: No.')
                    expect(review.locator('details')).to_have_count(86)
                    discovery = page.get_by_label('Discovery jobs')
                    discovery.get_by_role('button', name='Queue local discovery', exact=True).click()
                    expect(discovery.get_by_text('queued', exact=True)).to_be_visible()
                    discovery.get_by_role('button', name='Cancel discovery', exact=True).click()
                    expect(discovery.get_by_text('cancelled', exact=True)).to_be_visible()
                    discovery.get_by_role('button', name='Queue local discovery', exact=True).click()
                    expect(discovery.get_by_text('queued', exact=True)).to_be_visible()
                    fixture = ThreadingHTTPServer(('127.0.0.1', 8000), partial(QuietHandler, directory=str(Path('samples/web').resolve())))
                    fixture_thread = Thread(target=fixture.serve_forever, daemon=True)
                    fixture_thread.start()
                    options = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
                    worker = subprocess.Popen([sys.executable, '-m', 'adaptive_qa', 'dashboard',
                        'discovery-once', '--database', str(projects.database)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
                    expect(discovery.get_by_text('completed', exact=True)).to_be_visible(timeout=45000)
                    worker.wait(timeout=5)
                    assert worker.returncode == 0
                    discovery.get_by_role('button', name='Review discovery plan', exact=True).click()
                    expect(review).to_contain_text('Discovery completed.')
                    expect(review).not_to_contain_text('Selected: 0 ·')
                    expect(review).to_contain_text('Execution authorized: No.')
                    runs = page.get_by_label('Test runs', exact=True)
                    expect(runs.get_by_role('button', name='Start selected tests')).to_be_disabled()
                    for case_id in ('LOGIN-001', 'SEARCH-001'):
                        runs.get_by_label('Select ' + case_id, exact=True).check()
                    runs.get_by_role('button', name='Start selected tests').click()
                    expect(runs.get_by_text('Run queued', exact=True)).to_be_visible()
                    runs.get_by_role('button', name='Cancel test run').click()
                    expect(runs.get_by_text('Run cancelled', exact=True)).to_be_visible()
                    for case_id in ('LOGIN-001', 'SEARCH-001'):
                        runs.get_by_label('Select ' + case_id, exact=True).check()
                    runs.get_by_role('button', name='Start selected tests').click()
                    expect(runs.get_by_text('Run queued', exact=True)).to_be_visible()
                    worker = subprocess.Popen([sys.executable, '-m', 'adaptive_qa', 'dashboard',
                        'run-once', '--database', str(projects.database)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
                    expect(runs.get_by_text('Run completed', exact=True)).to_be_visible(timeout=75000)
                    worker.wait(timeout=5)
                    assert worker.returncode == 0
                    expect(runs.get_by_text('passed', exact=True)).to_have_count(2)
                    expect(runs.get_by_text('2 of 2 test results recorded.', exact=False)).to_be_visible()
                    expect(runs.get_by_role('link', name='View screenshot', exact=True)).to_have_count(2)
                    completed = runs.locator('article').filter(has_text='Run completed')
                    completed.get_by_role('button', name='Review report', exact=True).click()
                    report = completed.get_by_label('Run report', exact=True)
                    expect(report).to_contain_text('Requested: 2. Recorded: 2. Unrecorded: 0.')
                    expect(report).to_contain_text('Catalog: 86.')
                    report.get_by_label('Result status').select_option('failed')
                    expect(report).to_contain_text('No recorded outcomes match this filter.')
                    expect(report).to_contain_text('passed: 2')
                    report.get_by_label('Result status').select_option('passed')
                    expect(report.get_by_role('link', name='Report screenshot', exact=True)).to_have_count(2)
                    with page.expect_download() as download_info:
                        report.get_by_role('link', name='Download JSON report', exact=True).click()
                    download = download_info.value
                    assert download.suggested_filename == 'test-run-report.json'
                    exported = json.loads(Path(download.path()).read_text(encoding='utf-8'))
                    assert exported['recorded_total'] == 2 and exported['status_counts']['passed'] == 2
                    assert exported['catalog_total'] == 86
                    assert len(exported['results']) == 2
                    link = runs.locator('.run-outcome').filter(has_text='LOGIN-001').get_by_role('link', name='View screenshot', exact=True)
                    evidence_url = 'http://127.0.0.1:8765' + link.get_attribute('href')
                    with page.expect_popup() as popup_info:
                        link.click()
                    popup = popup_info.value
                    popup.wait_for_function("document.querySelector('img')?.complete && document.querySelector('img')?.naturalWidth > 0", timeout=10000)
                    popup.close()
                    evidence_response = page.context.request.get(evidence_url)
                    assert evidence_response.status == 200
                    assert evidence_response.headers['cache-control'] == 'no-store'
                    assert evidence_response.body().startswith(b'\x89PNG\r\n\x1a\n')
                    isolated = browser.new_context()
                    try:
                        assert isolated.request.get(evidence_url).status == 401
                        grant = auth.login('other@example.test', 'Other dashboard password 123!')
                        isolated.add_cookies([{'name': 'adaptive_session', 'value': grant.token.value,
                            'url': 'http://127.0.0.1:8765/', 'httpOnly': True, 'sameSite': 'Strict'}])
                        assert isolated.request.get(evidence_url).status == 404
                    finally:
                        isolated.close()
                    page.evaluate('window.scrollTo(0, 0)')
                    page.screenshot(path=str(output / 'workspace-desktop.png'), full_page=True)
                    page.set_viewport_size({'width': 390, 'height': 844})
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                    page.screenshot(path=str(output / 'workspace-mobile.png'), full_page=True)
                    page.get_by_label('Allow tests that change data').check()
                    page.get_by_role('button', name='Save configuration', exact=True).click()
                    expect(page.get_by_role('status')).to_have_text('Configuration saved. No tests were started.')
                    page.get_by_role('button', name='Review discovery plan', exact=True).click()
                    expect(page.get_by_text('This report uses older target or policy settings.', exact=False)).to_be_visible()
                    expect(page.get_by_label('Plan review results')).to_have_count(0)
                    page.get_by_role('button', name='Sign out', exact=True).click()
                    expect(page.get_by_role('heading', name='Sign in', exact=True)).to_be_visible()
                    page.reload()
                    expect(page.get_by_role('heading', name='Sign in', exact=True)).to_be_visible()
                    assert not errors, 'Dashboard JavaScript failed.'
                    assert not external, 'Dashboard attempted external requests.'
                finally:
                    browser.close()
        finally:
            if worker is not None and worker.poll() is None:
                _terminate_process_tree(worker)
            if fixture is not None:
                fixture.shutdown()
                fixture.server_close()
                fixture_thread.join(timeout=5)
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError('Owned dashboard server did not stop.')
    (output / 'ui.json').write_text(json.dumps({'status': 'passed', 'checks': [
        'invalid login', 'password cleared', 'login', 'owner-filtered list', 'create',
        'rename', 'save settings', 'reload persistence', 'masked reference',
        'conservative non-executing plan review', 'mobile width', 'logout persistence',
        'queue and cancel discovery', 'separate real worker and polled completion',
        'discovery-backed plan review', 'historical policy mismatch denied',
        'explicit two-case selection', 'queued test-run cancellation',
        'separate test worker completion and two real passed outcomes',
        'report filters preserve aggregate totals', 'downloaded JSON agrees with real outcomes',
        'decoded authorized screenshot', 'anonymous screenshot denied', 'other-owner screenshot denied',
        'no script errors or external requests']}), encoding='utf-8')
    print('Built React dashboard browser checks passed.')


if __name__ == '__main__':
    main()
