"""Real packaged local runtime, restored data, workers and binary rollback drill."""

from contextlib import closing, ExitStack
from functools import partial
from http.cookiejar import CookieJar
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor, urlopen

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.backup import create_backup
from adaptive_qa.backup_restore import prepare_restore
from adaptive_qa.backup_verification import verify_backup
from adaptive_qa.browser_process import _terminate_process_tree
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.local_runtime import prepare_local, select_local, local_status, run_local
from adaptive_qa.project_store import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
OLD_COMMIT = 'a71bc2c69140b3d4bd993be7495ab2d360f8decc'
ORIGIN = 'http://127.0.0.1:8877'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def request(client, path, *, body=None, csrf=None, cookie=None):
    headers = {'Origin': ORIGIN}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    if csrf:
        headers['X-CSRF-Token'] = csrf
    if cookie:
        headers['Cookie'] = cookie
    return client.open(Request(ORIGIN + path, headers=headers,
                              data=None if body is None else json.dumps(body).encode()), timeout=5)


def start(plan, release_id):
    options = {'start_new_session': True} if os.name != 'nt' else {
        'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    process = subprocess.Popen([sys.executable, '-m', 'adaptive_qa', 'deployment', 'local-run',
        '--environment', 'local', '--data-root', str(plan.data_root), '--origin', ORIGIN,
        '--role', 'serve', '--duration-seconds', '120'], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError('Packaged local server exited before readiness.')
            try:
                with urlopen(ORIGIN + '/', timeout=1) as response:
                    if response.status == 200:
                        assert response.headers['x-adaptive-qa-release'] == release_id
                        return process
            except (URLError, TimeoutError):
                time.sleep(.1)
        raise AssertionError('Packaged local server readiness timed out.')
    except BaseException:
        if process.poll() is None:
            _terminate_process_tree(process)
        raise


def stop(process, plan):
    if process.poll() is None:
        _terminate_process_tree(process)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if local_status(plan)['components']['serve'] == 'inactive':
            return
        time.sleep(.05)
    raise AssertionError('Managed server lease was not released.')


def main(candidate):
    candidate = Path(candidate).resolve()
    new_commit = json.loads((candidate / 'release.json').read_text())['source_commit']
    old_candidate = ROOT / 'artifacts/releases' / OLD_COMMIT
    assert new_commit != OLD_COMMIT
    fixture = ThreadingHTTPServer(('127.0.0.1', 8000), partial(QuietHandler, directory=str(ROOT / 'samples/web')))
    fixture_thread = Thread(target=fixture.serve_forever, daemon=True)
    fixture_thread.start()
    process = None
    try:
        with TemporaryDirectory(prefix='adaptive-local-runtime-') as temporary, ExitStack() as cleanup:
            cleanup.callback(lambda: _terminate_process_tree(process)
                             if process is not None and process.poll() is None else None)
            plan = DeploymentPlan(Environment.LOCAL, Path(temporary), ORIGIN)
            auth = AuthStore(plan.directory / 'auth.sqlite')
            actor = auth.create_user('runtime@example.test', 'Disposable runtime password 2026!')
            grant = auth.login('runtime@example.test', 'Disposable runtime password 2026!')
            projects = ProjectStore(plan.directory / 'projects.sqlite')
            project = projects.create(actor, 'Runtime fixture project')
            projects.save_configuration(actor, project.project_id, {'base_url': 'http://127.0.0.1:8000/',
                'allowed_hosts': ['127.0.0.1'], 'allow_data_changes': False, 'secret_references': {}})
            DashboardRunQueue(projects)
            bundle = create_backup(plan, maintenance_confirmed=True)['bundle_id']
            recovery = prepare_restore(plan, bundle, maintenance_confirmed=True)['recovery_id']
            original_databases = {name: (plan.directory / name).read_bytes()
                                  for name in ('auth.sqlite', 'projects.sqlite')}
            for path, commit in ((old_candidate, OLD_COMMIT), (candidate, new_commit)):
                prepare_local(plan, path, commit, maintenance_confirmed=True, trusted_release=True)
            selected = select_local(plan, OLD_COMMIT, maintenance_confirmed=True)
            process = start(plan, OLD_COMMIT)
            anonymous = build_opener()
            with request(anonymous, '/api/auth/me', cookie='adaptive_session=' + grant.token.value) as response:
                assert response.status == 200
            try:
                select_local(plan, new_commit, expected_selection=selected['selection_id'], maintenance_confirmed=True)
            except ValueError:
                pass
            else:
                raise AssertionError('A running server did not block release switching.')
            stop(process, plan)
            process = None
            selected = select_local(plan, new_commit, recovery_id=recovery,
                expected_selection=selected['selection_id'], maintenance_confirmed=True)
            process = start(plan, new_commit)
            try:
                request(anonymous, '/api/auth/me', cookie='adaptive_session=' + grant.token.value)
            except HTTPError as error:
                assert error.code == 401
            else:
                raise AssertionError('Restored session token remained valid.')
            cookies = CookieJar()
            client = build_opener(HTTPCookieProcessor(cookies))
            with request(client, '/api/auth/login', body={'email': 'runtime@example.test',
                    'password': 'Disposable runtime password 2026!'}) as response:
                assert response.status == 200
            csrf = next(cookie.value for cookie in cookies if cookie.name == 'adaptive_csrf')
            with request(client, '/api/projects', body={'name': 'Created after local upgrade'}, csrf=csrf) as response:
                added = json.loads(response.read())['project_id']
            data = plan.directory / 'recovery' / recovery
            recovered = ProjectStore(data / 'projects.sqlite')
            discovery = DashboardDiscoveryQueue(recovered)
            job = discovery.submit(actor, project.project_id)
            assert run_local(plan, 'discovery-once', duration_seconds=90)['status'] == 'completed'
            assert discovery.get(actor, project.project_id, job['job_id'])['status'] == 'completed'
            assert discovery.get(actor, project.project_id, job['job_id'])['report']['execution_authorized'] is False
            queue = DashboardRunQueue(recovered)
            work = queue.submit(actor, project.project_id, job['job_id'], ('LOGIN-001', 'SEARCH-001'))
            assert run_local(plan, 'run-once', duration_seconds=90)['status'] == 'completed'
            result = queue.get(actor, project.project_id, work['run_id'])
            assert result['status'] == 'completed' and len(result['results']) == 2
            assert all(item['status'] == 'passed' and item.get('evidence_id') for item in result['results']), [
                {'case_id': item['case_id'], 'status': item['status'],
                 'evidence_present': bool(item.get('evidence_id'))} for item in result['results']]
            rejected = queue.submit(actor, project.project_id, job['job_id'], ('LOGIN-001',))
            recovered.save_configuration(actor, project.project_id, {'base_url': 'http://127.0.0.1:8000/changed-fixture',
                'allowed_hosts': ['127.0.0.1'], 'allow_data_changes': False, 'secret_references': {}})
            assert run_local(plan, 'run-once', duration_seconds=90)['status'] == 'stopped'
            assert queue.get(actor, project.project_id, rejected['run_id'])['status'] == 'error'
            recovered.save_configuration(actor, project.project_id, {'base_url': 'http://127.0.0.1:8000/',
                'allowed_hosts': ['127.0.0.1'], 'allow_data_changes': False, 'secret_references': {}})
            stop(process, plan)
            process = None
            selected = select_local(plan, OLD_COMMIT,
                expected_selection=selected['selection_id'], maintenance_confirmed=True)
            process = start(plan, OLD_COMMIT)
            with request(client, '/api/projects') as response:
                assert added in {item['project_id'] for item in json.loads(response.read())['projects']}
            with request(client, f"/api/projects/{project.project_id}/runs/{work['run_id']}") as response:
                assert json.loads(response.read())['status'] == 'completed'
            stop(process, plan)
            process = None
            assert all(value == 'inactive' for value in local_status(plan)['components'].values())
            expired = run_local(plan, 'serve', duration_seconds=5)
            assert expired['timed_out'] is True and local_status(plan)['components']['serve'] == 'inactive'
            assert verify_backup(plan, bundle)['verified']
            assert all((plan.directory / name).read_bytes() == value for name, value in original_databases.items())
    finally:
        if process is not None and process.poll() is None:
            _terminate_process_tree(process)
        fixture.shutdown()
        fixture.server_close()
        fixture_thread.join(timeout=5)
    report = {'old_release': OLD_COMMIT, 'new_release': new_commit,
              'sequence': ['old/live', 'new/restored', 'old/restored'], 'local_only': True,
              'active_server_switch_blocked': True, 'restored_session_revoked': True,
              'post_upgrade_project_preserved_on_rollback': True, 'managed_worker_cases_passed': 2,
              'screenshots_persisted': 2, 'component_leases_released': True,
              'supervisor_deadline_cleanup': True,
              'failed_job_nonzero_exit_verified': True,
              'original_database_bytes_preserved': True,
              'backup_still_verified': True, 'public_backend': False}
    output = ROOT / 'artifacts/deployment/local-runtime.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main(sys.argv[1])
