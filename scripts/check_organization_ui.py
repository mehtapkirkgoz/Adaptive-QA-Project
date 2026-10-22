"""Real local organization UI, role isolation and non-executing configuration."""

import json
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time

from playwright.sync_api import sync_playwright, expect
import uvicorn

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.project_store import ProjectStore
from adaptive_qa.organization_store import OrganizationStore
from adaptive_qa.organization_policy import OrganizationRole as Role
from adaptive_qa.web_app import create_app
from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.dashboard_worker import process_discovery_once
from check_dashboard_runs import QuietHandler


def main():
    origin = 'http://127.0.0.1:8879'
    output = Path('artifacts/organizations')
    output.mkdir(parents=True, exist_ok=True)
    errors, external = [], []
    with TemporaryDirectory(prefix='adaptive-organization-ui-') as temporary:
        root = Path(temporary)
        auth = AuthStore(root/'auth.sqlite')
        alice = auth.create_user('alice@example.test', 'Local Alice password 123!')
        bob = auth.create_user('bob@example.test', 'Local Bob password 123!')
        projects = ProjectStore(root/'projects.sqlite')
        organizations = OrganizationStore(projects)
        organizations.create(bob, 'Other private organization')
        server = uvicorn.Server(uvicorn.Config(create_app(auth, projects=projects,
            ui_directory=Path('frontend/dist'), port=8879), host='127.0.0.1', port=8879,
            log_level='critical', access_log=False, proxy_headers=False))
        thread = Thread(target=server.run, daemon=True)
        thread.start()
        fixture = ThreadingHTTPServer(('127.0.0.1', 8000), partial(QuietHandler, directory='samples/web'))
        fixture_thread = Thread(target=fixture.serve_forever, daemon=True)
        fixture_thread.start()
        try:
            deadline = time.monotonic()+10
            while not server.started:
                if not thread.is_alive() or time.monotonic()>deadline:
                    raise AssertionError('Local organization server did not start.')
                time.sleep(.05)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    def intercept(route):
                        if not route.request.url.startswith(origin+'/'):
                            external.append('unexpected_destination')
                            route.abort()
                        else:
                            route.continue_()
                    page.route('**/*', intercept)
                    def login(name):
                        page.get_by_label('Email', exact=True).fill(name+'@example.test')
                        page.get_by_label('Password', exact=True).fill(f'Local {name.title()} password 123!')
                        page.get_by_role('button', name='Sign in', exact=True).click()
                        expect(page.get_by_role('heading', name='Your projects', exact=True)).to_be_visible()
                    page.goto(origin)
                    login('alice')
                    page.get_by_role('button', name='Organizations', exact=True).click()
                    panel = page.get_by_label('Organization workspace', exact=True)
                    expect(panel.get_by_text('Other private organization')).to_have_count(0)
                    panel.get_by_label('New organization name', exact=True).fill('Controlled team')
                    panel.get_by_role('button', name='Create organization', exact=True).click()
                    panel.get_by_role('button', name='Controlled team · owner', exact=True).click()
                    panel.get_by_label('Organization project name', exact=True).fill('Shared UI fixture')
                    panel.get_by_role('button', name='Create shared project', exact=True).click()
                    panel.get_by_role('button', name='Shared UI fixture', exact=True).click()
                    panel.get_by_label('Organization target URL', exact=True).fill('http://127.0.0.1:8000/')
                    panel.get_by_label('Organization allowed hosts', exact=True).fill('127.0.0.1')
                    panel.get_by_role('button', name='Save shared configuration', exact=True).click()
                    expect(panel.get_by_role('status')).to_have_text('Organization configuration saved. No work was started.')
                    organization_id = organizations.list(alice)[0]['organization_id']
                    panel.get_by_role('button', name='Queue local discovery', exact=True).click()
                    expect(panel.get_by_text('queued', exact=True)).to_be_visible()
                    queue = OrganizationDiscoveryQueue(OrganizationProjects(organizations))
                    outcome = process_discovery_once(queue)
                    assert outcome['status'] == 'completed'
                    panel.get_by_role('button', name='Review discovery plan', exact=True).click()
                    expect(panel.get_by_text('Execution authorized: No.', exact=False)).to_be_visible()
                    organizations.set_member(alice, organization_id, bob.user_id, Role.VIEWER)
                    page.screenshot(path=str(output/'owner.png'), full_page=True)
                    page.get_by_role('button', name='Sign out', exact=True).click()
                    login('bob')
                    page.get_by_role('button', name='Organizations', exact=True).click()
                    panel.get_by_role('button', name='Controlled team · viewer', exact=True).click()
                    panel.get_by_role('button', name='Shared UI fixture', exact=True).click()
                    expect(panel.get_by_label('Organization target URL', exact=True)).to_have_value('http://127.0.0.1:8000/')
                    expect(panel.get_by_label('Organization target URL', exact=True)).to_be_disabled()
                    expect(panel.get_by_role('button', name='Save shared configuration', exact=True)).to_have_count(0)
                    expect(panel.get_by_role('button', name='Queue local discovery', exact=True)).to_be_disabled()
                    organizations.remove_member(alice, organization_id, bob.user_id)
                    page.reload()
                    page.get_by_role('button', name='Organizations', exact=True).click()
                    expect(panel.get_by_role('button', name='Other private organization · owner', exact=True)).to_be_visible()
                    expect(panel.get_by_role('button', name='Controlled team · viewer', exact=True)).to_have_count(0)
                    page.set_viewport_size({'width': 390, 'height': 844})
                    page.screenshot(path=str(output/'mobile.png'), full_page=True)
                    with projects._connection() as c:
                        assert c.execute('SELECT count(*) FROM dashboard_test_runs').fetchone()[0] == 0
                    assert not errors and not external
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive()
            fixture.shutdown()
            fixture.server_close()
            fixture_thread.join(timeout=5)
    report = {'owner_create_and_save': True, 'viewer_read_only': True,
              'revocation_after_reload': True, 'other_organization_hidden': True,
              'queued_runs': 0, 'scoped_discovery_completed': True, 'plan_execution_authorized': False,
              'external_requests': len(external), 'page_errors': errors,
              'demo_modified': False}
    (output/'ui.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
