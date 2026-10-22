"""Real separate test worker against a temporary owned controlled fixture."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread

from adaptive_qa.browser_process import _terminate_process_tree
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.project_store import ProjectStore, ProjectActor


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    root = Path(__file__).resolve().parents[1]
    server = ThreadingHTTPServer(('127.0.0.1', 8000), partial(QuietHandler, directory=str(root / 'samples/web')))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'projects.sqlite'
            projects = ProjectStore(path)
            actor = ProjectActor('a' * 32)
            project = projects.create(actor, 'Run worker acceptance')
            projects.save_configuration(actor, project.project_id, {
                'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                'allow_data_changes': False, 'secret_references': {}})
            discovery = DashboardDiscoveryQueue(projects)
            job = discovery.submit(actor, project.project_id)
            assert process_discovery_once(discovery)['status'] == 'completed'
            queue = DashboardRunQueue(projects)
            run = queue.submit(actor, project.project_id, job['job_id'], ('LOGIN-001', 'SEARCH-001'))
            options = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
            process = subprocess.Popen([sys.executable, '-m', 'adaptive_qa', 'dashboard', 'run-once',
                '--database', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
            try:
                process.wait(timeout=75)
                assert process.returncode == 0, 'Separate test worker CLI failed.'
            finally:
                if process.poll() is None:
                    _terminate_process_tree(process)
            result = DashboardRunQueue(ProjectStore(path)).get(actor, project.project_id, run['run_id'])
            assert result['status'] == 'completed', result['status']
            assert [r['case_id'] for r in result['results']] == ['LOGIN-001', 'SEARCH-001']
            assert all(r['status'] == 'passed' for r in result['results']), result['results']
            assert all('evidence_id' in r for r in result['results']), 'Actual screenshots were not attached.'
            for recorded in result['results']:
                assert queue.evidence(actor, project.project_id, run['run_id'], recorded['evidence_id']).startswith(b'\x89PNG\r\n\x1a\n')
            assert not discovery.get(actor, project.project_id, job['job_id'])['report']['execution_authorized']
            output = root / 'artifacts/dashboard/run-worker.json'
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps({'status': 'passed', 'run': result}, indent=2), encoding='utf-8')
            print('Separate owned UI test worker passed two actual assertions.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
