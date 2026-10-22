"""Explicit owned test-run admission, separate from non-executing discovery plans."""

import json
from uuid import uuid4

from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_worker import configuration_fingerprint
from adaptive_qa.project_store import ProjectNotFound, _id
from adaptive_qa.smoke_checks import SMOKE_CHECKS


class TestRunNotFound(LookupError):
    """Missing and other-owner runs have the same outcome."""


class DashboardRunQueue:
    """Admission/persistence only; no HTTP routes or test executor wired yet."""

    def __init__(self, projects):
        self.projects = projects
        DashboardDiscoveryQueue(projects)
        with projects._connection() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS dashboard_test_runs ('
                'sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT UNIQUE NOT NULL, '
                'project_id TEXT NOT NULL, owner_id TEXT NOT NULL, discovery_job_id TEXT NOT NULL, '
                'case_ids_json TEXT NOT NULL, configuration_json TEXT NOT NULL, status TEXT NOT NULL)')
            connection.execute('CREATE INDEX IF NOT EXISTS dashboard_runs_owner ON dashboard_test_runs(owner_id, sequence)')

    @staticmethod
    def _public(row):
        return {'run_id': row['run_id'], 'project_id': row['project_id'],
                'discovery_job_id': row['discovery_job_id'], 'case_ids': json.loads(row['case_ids_json']),
                'status': row['status']}

    def _owned(self, connection, actor, project_id, run_id):
        self.projects._actor(actor)
        _id(project_id)
        _id(run_id)
        row = connection.execute('SELECT r.* FROM dashboard_test_runs r '
            'JOIN dashboard_projects p ON p.project_id=r.project_id AND p.owner_id=r.owner_id '
            'WHERE r.run_id=? AND r.project_id=? AND r.owner_id=?', (run_id, project_id, actor.user_id)).fetchone()
        if row is None:
            raise TestRunNotFound('Test run not found.')
        return row

    def submit(self, actor, project_id, discovery_job_id, case_ids):
        self.projects._actor(actor)
        _id(project_id)
        _id(discovery_job_id)
        if (not isinstance(case_ids, tuple) or not 1 <= len(case_ids) <= 10
                or any(not isinstance(case, str) or len(case) > 30 for case in case_ids)
                or len(set(case_ids)) != len(case_ids)):
            raise ValueError('Select one to ten distinct test case IDs.')
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT s.settings_json FROM dashboard_projects p '
                'LEFT JOIN dashboard_project_settings s ON s.project_id=p.project_id '
                'WHERE p.project_id=? AND p.owner_id=?', (project_id, actor.user_id)).fetchone()
            if row is None:
                raise ProjectNotFound('Project not found.')
            if row['settings_json'] is None:
                raise ValueError('Saved settings are required.')
            saved = json.loads(row['settings_json'])
            snapshot = {key: saved[key] for key in ('base_url', 'allowed_hosts', 'allow_data_changes')}
            if snapshot['base_url'] not in ('http://127.0.0.1:8000', 'http://127.0.0.1:8000/'):
                raise ValueError('Only the controlled local root fixture is supported.')
            discovery = connection.execute('SELECT report_json FROM dashboard_discovery_jobs '
                "WHERE job_id=? AND project_id=? AND owner_id=? AND status='completed'",
                (discovery_job_id, project_id, actor.user_id)).fetchone()
            if discovery is None or discovery['report_json'] is None:
                raise ValueError('An owned completed discovery report is required.')
            report = json.loads(discovery['report_json'])
            if (report.get('execution_authorized') is not False or report.get('project_id') != project_id
                    or report.get('discovery_status') != 'completed'
                    or type(report.get('inspected_pages')) is not int or report['inspected_pages'] < 1
                    or report.get('configuration_fingerprint') != configuration_fingerprint(snapshot)):
                raise ValueError('Discovery report does not match current settings.')
            evidence = {case['case_id']: case for case in report.get('cases', [])}
            catalog = {case.case_id: case for case in TEST_CASES}
            for case_id in case_ids:
                definition, decision = catalog.get(case_id), evidence.get(case_id)
                if (definition is None or case_id not in SMOKE_CHECKS or definition.changes_data
                        or decision is None or decision.get('decision') != 'selected'
                        or decision.get('test_type') != 'ui' or decision.get('target_binding') != 'local_root'):
                    raise ValueError('A selected read-only UI case bound to the local root is required.')
            active = "status IN ('queued', 'running', 'cancel_requested')"
            total = connection.execute('SELECT count(*) FROM dashboard_test_runs WHERE ' + active).fetchone()[0]
            owned = connection.execute('SELECT count(*) FROM dashboard_test_runs WHERE ' + active + ' AND owner_id=?', (actor.user_id,)).fetchone()[0]
            if total >= 100 or owned >= 5:
                raise ValueError('Test run admission limit reached.')
            run_id = uuid4().hex
            connection.execute('INSERT INTO dashboard_test_runs '
                '(run_id, project_id, owner_id, discovery_job_id, case_ids_json, configuration_json, status) '
                "VALUES (?, ?, ?, ?, ?, ?, 'queued')", (run_id, project_id, actor.user_id,
                discovery_job_id, json.dumps(case_ids), json.dumps(snapshot)))
            return self._public(self._owned(connection, actor, project_id, run_id))

    def get(self, actor, project_id, run_id):
        with self.projects._connection() as connection:
            return self._public(self._owned(connection, actor, project_id, run_id))

    def cancel(self, actor, project_id, run_id):
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = self._owned(connection, actor, project_id, run_id)
            if row['status'] not in ('queued', 'cancelled'):
                raise ValueError('Only queued test runs can currently be cancelled.')
            connection.execute("UPDATE dashboard_test_runs SET status='cancelled' WHERE run_id=?", (run_id,))
            return self._public(self._owned(connection, actor, project_id, run_id))
