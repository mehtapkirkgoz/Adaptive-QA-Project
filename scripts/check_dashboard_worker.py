"""A separate worker CLI processes a temporary owned job against a guarded fixture."""

from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread

from check_local_discovery import Handler
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.project_store import ProjectStore, ProjectActor
from adaptive_qa.browser_process import _terminate_process_tree
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.api_catalog import API_CASES
from adaptive_qa.database_catalog import DATABASE_CASES


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 8000), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'projects.sqlite'
            projects = ProjectStore(path)
            actor = ProjectActor('a' * 32)
            project = projects.create(actor, 'Local worker acceptance')
            projects.save_configuration(actor, project.project_id, {
                'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                'allow_data_changes': False, 'secret_references': {}})
            queue = DashboardDiscoveryQueue(projects)
            job = queue.submit(actor, project.project_id)
            options = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
            process = subprocess.Popen([sys.executable, '-m', 'adaptive_qa', 'dashboard',
                'discovery-once', '--database', str(path)], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, **options)
            try:
                process.wait(timeout=45)
                assert process.returncode == 0, 'Separate dashboard worker CLI failed.'
            finally:
                if process.poll() is None:
                    _terminate_process_tree(process)
            result = DashboardDiscoveryQueue(ProjectStore(path)).get(actor, project.project_id, job['job_id'])
            assert result['status'] == 'completed', result['status']
            report = result['report']
            assert not report['execution_authorized']
            assert report['inspected_pages'] > 0
            assert 0 < report['counts']['selected'] <= len(TEST_CASES)
            assert report['counts']['catalog'] == len(TEST_CASES) + len(API_CASES) + len(DATABASE_CASES)
            assert all(c['decision'] == 'blocked' for c in report['cases'] if c['test_type'] != 'ui')
            output = Path('artifacts/dashboard/worker.json')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps({'status': 'passed', 'report': report}, indent=2), encoding='utf-8')
            print('Separate owned dashboard discovery worker passed.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
