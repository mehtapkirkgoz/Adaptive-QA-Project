"""Verify real Chromium cookies and revocation on an owned loopback server."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time

from playwright.sync_api import sync_playwright
import uvicorn

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.web_app import create_app, SESSION_COOKIE, CSRF_COOKIE


def main():
    with TemporaryDirectory() as directory:
        store = AuthStore(Path(directory) / 'auth.sqlite')
        actor = store.create_user('browser@example.test', 'Local browser password 123!')
        server = uvicorn.Server(uvicorn.Config(create_app(store), host='127.0.0.1',
            port=8765, log_level='critical', access_log=False, proxy_headers=False))
        thread = Thread(target=server.run, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() >= deadline:
                    raise RuntimeError('Owned dashboard server did not start.')
                time.sleep(0.05)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    context = browser.new_context()
                    page = context.new_page()
                    page.goto('http://127.0.0.1:8765/api/auth/me', timeout=10000)
                    result = page.evaluate('''async () => {
                        const response = await fetch('/api/auth/login', {method:'POST',
                          headers:{'Content-Type':'application/json'},
                          body:JSON.stringify({email:'browser@example.test',password:'Local browser password 123!'})});
                        return {status:response.status, body:await response.json()};
                    }''')
                    assert result == {'status': 200, 'body': {'user_id': actor.user_id}}
                    cookies = {c['name']: c for c in context.cookies()}
                    assert cookies[SESSION_COOKIE]['httpOnly']
                    assert cookies[SESSION_COOKIE]['sameSite'] == 'Strict'
                    assert not cookies[CSRF_COOKIE]['httpOnly']
                    visible = page.evaluate('document.cookie')
                    assert SESSION_COOKIE not in visible and CSRF_COOKIE in visible
                    projects = page.evaluate('''async () => {
                        const csrf = document.cookie.split('; ').find(c=>c.startsWith('adaptive_csrf=')).split('=')[1];
                        const headers = {'Content-Type':'application/json','X-CSRF-Token':csrf};
                        const create = await fetch('/api/projects', {method:'POST',headers,body:JSON.stringify({name:'Browser project'})});
                        const project = await create.json();
                        const rename = await fetch('/api/projects/'+project.project_id, {method:'PATCH',headers,body:JSON.stringify({name:'Renamed project'})});
                        const listed = await (await fetch('/api/projects?limit=1&offset=0')).json();
                        const fetched = await (await fetch('/api/projects/'+project.project_id)).json();
                        const path = '/api/projects/'+project.project_id+'/configuration';
                        const empty = await (await fetch(path)).json();
                        const settings = {base_url:'http://127.0.0.1:8000/',allowed_hosts:['127.0.0.1'],
                          allow_data_changes:false,secret_references:{login_password:empty.available_secret_references.login_password}};
                        const saved = await fetch(path, {method:'PUT',headers,body:JSON.stringify(settings)});
                        const configuration = await (await fetch(path)).json();
                        return {created:create.status,renamed:rename.status,listed:listed.projects,fetched,
                          settings_status:saved.status,configuration};
                    }''')
                    assert projects['created'] == 201 and projects['renamed'] == 200
                    assert projects['listed'] == [projects['fetched']]
                    assert projects['fetched']['name'] == 'Renamed project'
                    assert projects['settings_status'] == 200
                    assert projects['configuration']['configured']
                    assert projects['configuration']['secret_references']['login_password']['value'] == '[REDACTED]'
                    assert not projects['configuration']['allow_data_changes']
                    assert page.evaluate("async () => (await fetch('/api/auth/logout', {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status") == 401
                    assert page.evaluate('''async () => {
                        const csrf = document.cookie.split('; ').find(c=>c.startsWith('adaptive_csrf=')).split('=')[1];
                        return (await fetch('/api/auth/logout', {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:'{}'})).status;
                    }''') == 200
                    assert page.evaluate("async () => (await fetch('/api/auth/me')).status") == 401
                    assert not context.cookies()
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError('Owned dashboard server did not stop.')
    output = Path('artifacts/dashboard/auth.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'browser_auth': 'passed', 'checks': [
        'login identity', 'HttpOnly session', 'Strict SameSite', 'readable CSRF only',
        'project create rename list read', 'project settings and masked references',
        'missing CSRF denied', 'logout',
        'revoked identity', 'cookies removed']}), encoding='utf-8')
    print('Local dashboard browser authentication passed.')


if __name__ == '__main__':
    main()
