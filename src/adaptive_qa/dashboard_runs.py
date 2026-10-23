"""Explicit owned test-run admission, separate from non-executing discovery plans."""
from adaptive_qa.form_configuration import runtime_configuration
from adaptive_qa.licensing import LicenseError

import json
import secrets
import hashlib
import time
import re
from dataclasses import asdict
from dataclasses import dataclass, field
from uuid import uuid4

from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_worker import configuration_fingerprint
from adaptive_qa.project_store import ProjectNotFound, _id
from adaptive_qa.smoke_checks import SMOKE_CHECKS
from adaptive_qa.models import TestResult
from adaptive_qa.worker_lock import worker_lock
from adaptive_qa.dashboard_evidence import validate_png
from adaptive_qa.document_target import validate_runtime_binding
from adaptive_qa.discovery_target import configured_discovery


@dataclass(frozen=True)
class RunWork:
    run_id: str
    project_id: str
    owner_id: str
    case_ids: tuple[str, ...]
    configuration: dict
    claim_token: str = field(repr=False)


class TestRunNotFound(LookupError):
    """Missing and other-owner runs have the same outcome."""


class DashboardRunQueue:
    """Owned dispatch and result lifecycle; HTTP integration remains separate."""

    def __init__(self, projects, *, clock=None, retention_seconds=7 * 86400):
        if type(retention_seconds) is not int or not 60 <= retention_seconds <= 30 * 86400:
            raise ValueError('Evidence retention must be 60 seconds to 30 days.')
        self.projects = projects
        self.clock = clock or time.time
        self.retention_seconds = retention_seconds
        DashboardDiscoveryQueue(projects)
        with projects._connection() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS dashboard_test_runs ('
                'sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT UNIQUE NOT NULL, '
                'project_id TEXT NOT NULL, owner_id TEXT NOT NULL, discovery_job_id TEXT NOT NULL, '
                'case_ids_json TEXT NOT NULL, configuration_json TEXT NOT NULL, status TEXT NOT NULL)')
            connection.execute('CREATE INDEX IF NOT EXISTS dashboard_runs_owner ON dashboard_test_runs(owner_id, sequence)')
            connection.execute('CREATE TABLE IF NOT EXISTS dashboard_run_evidence ('
                'evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, case_id TEXT NOT NULL, png BLOB NOT NULL)')
            evidence_columns = {row['name'] for row in connection.execute('PRAGMA table_info(dashboard_run_evidence)')}
            if 'expires_at' not in evidence_columns:
                connection.execute('ALTER TABLE dashboard_run_evidence ADD COLUMN expires_at REAL')
            connection.execute('CREATE INDEX IF NOT EXISTS dashboard_evidence_expiry '
                'ON dashboard_run_evidence(coalesce(expires_at, 0), evidence_id)')
            columns = {row['name'] for row in connection.execute('PRAGMA table_info(dashboard_test_runs)')}
            for name, declaration in (('claim_token', 'TEXT'), ('results_json', "TEXT NOT NULL DEFAULT '[]'"),
                                      ('rerun_of', 'TEXT'), ('contracts_json', 'TEXT'), ('execution_context', 'TEXT')):
                if name not in columns:
                    connection.execute(f'ALTER TABLE dashboard_test_runs ADD COLUMN {name} {declaration}')

    def _public(self, row):
        results = json.loads(row['results_json'])
        for result in results:
            if result.get('evidence_id') and result.get('evidence_expires_at', 0) <= self.clock():
                result.pop('evidence_id')
                result['evidence_expired'] = True
        return {'run_id': row['run_id'], 'project_id': row['project_id'],
                'discovery_job_id': row['discovery_job_id'], 'case_ids': json.loads(row['case_ids_json']),
                'status': row['status'], 'results': results, 'rerun_of': row['rerun_of']}

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

    def submit(self, actor, project_id, discovery_job_id, case_ids, *, rerun_of=None):
        self.projects._actor(actor)
        _id(project_id)
        _id(discovery_job_id)
        if (not isinstance(case_ids, tuple) or not 1 <= len(case_ids) <= 10
                or any(not isinstance(case, str) or len(case) > 30 for case in case_ids)
                or len(set(case_ids)) != len(case_ids)):
            raise ValueError('Select one to ten distinct test case IDs.')
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            if hasattr(self.projects, 'admit_execution'):
                self.projects.admit_execution(connection)
            if rerun_of is not None:
                parent = self._owned(connection, actor, project_id, rerun_of)
                if parent['status'] not in ('completed', 'cancelled', 'error'):
                    raise ValueError('Only finalized runs can be rerun.')
                if not set(case_ids) <= set(json.loads(parent['case_ids_json'])):
                    raise ValueError('Rerun selection must belong to the original run.')
            row = connection.execute('SELECT s.settings_json FROM dashboard_projects p '
                'LEFT JOIN dashboard_project_settings s ON s.project_id=p.project_id '
                'WHERE p.project_id=? AND p.owner_id=?', (project_id, actor.user_id)).fetchone()
            if row is None:
                raise ProjectNotFound('Project not found.')
            if row['settings_json'] is None:
                raise ValueError('Saved settings are required.')
            saved = json.loads(row['settings_json'])
            snapshot = runtime_configuration(saved)
            configured_discovery(snapshot)
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
                        or decision.get('test_type') != 'ui'):
                    raise ValueError('A selected read-only UI case bound to the saved target is required.')
                validate_runtime_binding(snapshot, case_id, decision)
            active = "status IN ('queued', 'running', 'cancel_requested')"
            total = connection.execute('SELECT count(*) FROM dashboard_test_runs WHERE ' + active).fetchone()[0]
            owned = connection.execute('SELECT count(*) FROM dashboard_test_runs WHERE ' + active + ' AND owner_id=?', (actor.user_id,)).fetchone()[0]
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_organization_runs'").fetchone():
                total += connection.execute('SELECT count(*) FROM dashboard_organization_runs WHERE ' + active).fetchone()[0]
                owned += connection.execute('SELECT count(*) FROM dashboard_organization_runs WHERE ' + active + ' AND user_id=?', (actor.user_id,)).fetchone()[0]
            if total >= 100 or owned >= 5:
                raise ValueError('Test run admission limit reached.')
            run_id = uuid4().hex
            contracts = {case_id: hashlib.sha256(json.dumps(asdict(catalog[case_id]),
                sort_keys=True).encode()).hexdigest() for case_id in case_ids}
            connection.execute('INSERT INTO dashboard_test_runs '
                '(run_id, project_id, owner_id, discovery_job_id, case_ids_json, configuration_json, status, rerun_of, contracts_json) '
                "VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)", (run_id, project_id, actor.user_id,
                discovery_job_id, json.dumps(case_ids), json.dumps(snapshot), rerun_of, json.dumps(contracts)))
            return self._public(self._owned(connection, actor, project_id, run_id))

    def comparison_context(self, actor, project_id, run_id):
        with self.projects._connection() as connection:
            row = self._owned(connection, actor, project_id, run_id)
            return {'configuration': configuration_fingerprint(json.loads(row['configuration_json'])),
                    'contracts': json.loads(row['contracts_json']) if row['contracts_json'] else None,
                    'execution_context': row['execution_context']}

    def record_execution_context(self, work, context):
        if not isinstance(context, str) or not re.fullmatch('[0-9a-f]{64}', context):
            raise ValueError('A validated execution context digest is required.')
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = self._claimed(connection, work)
            if row['status'] == 'cancel_requested':
                return False
            connection.execute('UPDATE dashboard_test_runs SET execution_context=? WHERE run_id=?',
                               (context, work.run_id))
            return True

    def get(self, actor, project_id, run_id):
        with self.projects._connection() as connection:
            return self._public(self._owned(connection, actor, project_id, run_id))

    def list(self, actor, project_id):
        self.projects.get(actor, project_id)
        with self.projects._connection() as connection:
            rows = connection.execute('SELECT r.* FROM dashboard_test_runs r '
                'JOIN dashboard_projects p ON p.project_id=r.project_id AND p.owner_id=r.owner_id '
                'WHERE r.project_id=? AND r.owner_id=? ORDER BY r.sequence DESC LIMIT 20',
                (project_id, actor.user_id)).fetchall()
        return tuple(self._public(row) for row in rows)

    def cancel(self, actor, project_id, run_id):
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = self._owned(connection, actor, project_id, run_id)
            status = {'queued': 'cancelled', 'running': 'cancel_requested'}.get(row['status'], row['status'])
            connection.execute('UPDATE dashboard_test_runs SET status=? WHERE run_id=?', (status, run_id))
            return self._public(self._owned(connection, actor, project_id, run_id))

    def claim_next(self):
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute("SELECT * FROM dashboard_test_runs WHERE status='queued' ORDER BY sequence LIMIT 1").fetchone()
            if row is None:
                return None
            if hasattr(self.projects, 'admit_execution'):
                try:
                    self.projects.admit_execution(connection, starting=True)
                except LicenseError:
                    return None
            token = secrets.token_urlsafe(32)
            connection.execute("UPDATE dashboard_test_runs SET status='running', claim_token=? WHERE run_id=?", (token, row['run_id']))
            return RunWork(row['run_id'], row['project_id'], row['owner_id'],
                           tuple(json.loads(row['case_ids_json'])), json.loads(row['configuration_json']), token)

    @staticmethod
    def _claimed(connection, work):
        row = connection.execute('SELECT * FROM dashboard_test_runs WHERE run_id=? AND project_id=? AND owner_id=?',
                                 (work.run_id, work.project_id, work.owner_id)).fetchone()
        if (row is None or row['status'] not in ('running', 'cancel_requested')
                or not secrets.compare_digest(row['claim_token'] or '', work.claim_token)):
            raise ValueError('Invalid or finalized run claim.')
        return row

    def cancellation_requested(self, work):
        with self.projects._connection() as connection:
            if hasattr(self.projects, 'execution_allowed'):
                connection.execute('BEGIN IMMEDIATE')
                self._claimed(connection, work)
                if not self.projects.execution_allowed():
                    connection.execute("UPDATE dashboard_test_runs SET status='cancel_requested' WHERE run_id=?", (work.run_id,))
                    return True
            return self._claimed(connection, work)['status'] == 'cancel_requested'

    def configuration_current(self, work):
        with self.projects._connection() as connection:
            self._claimed(connection, work)
            return self._configuration_current(connection, work)

    @staticmethod
    def _configuration_current(connection, work):
        row = connection.execute('SELECT s.settings_json FROM dashboard_projects p '
            'JOIN dashboard_project_settings s ON s.project_id=p.project_id '
            'WHERE p.project_id=? AND p.owner_id=?', (work.project_id, work.owner_id)).fetchone()
        if row is None:
            return False
        saved = json.loads(row['settings_json'])
        snapshot = runtime_configuration(saved)
        return configuration_fingerprint(snapshot) == configuration_fingerprint(work.configuration)

    def record_result(self, work, result, *, evidence_png=None):
        if not isinstance(result, TestResult):
            raise ValueError('A typed test result is required.')
        if evidence_png is not None:
            validate_png(evidence_png)
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = self._claimed(connection, work)
            if row['status'] == 'cancel_requested':
                return False
            if not self._configuration_current(connection, work):
                raise ValueError('Run settings changed before result commit.')
            results = json.loads(row['results_json'])
            ids = json.loads(row['case_ids_json'])
            if len(results) >= len(ids) or result.case_id != ids[len(results)]:
                raise ValueError('Result must match the next requested case.')
            # Raw adapter messages and filesystem paths are never exposed in dashboard results.
            results.append({'case_id': result.case_id, 'status': result.status,
                            'duration_seconds': result.duration_seconds,
                            'message': f'Test execution outcome: {result.status.value}.'})
            if evidence_png is not None:
                evidence_id = uuid4().hex
                expires_at = self.clock() + self.retention_seconds
                connection.execute('INSERT INTO dashboard_run_evidence '
                    '(evidence_id, run_id, case_id, png, expires_at) VALUES (?, ?, ?, ?, ?)',
                    (evidence_id, work.run_id, result.case_id, evidence_png, expires_at))
                results[-1]['evidence_id'] = evidence_id
                results[-1]['evidence_expires_at'] = expires_at
            connection.execute('UPDATE dashboard_test_runs SET results_json=? WHERE run_id=?',
                               (json.dumps(results, allow_nan=False), work.run_id))
            return True

    def evidence(self, actor, project_id, run_id, evidence_id):
        _id(evidence_id)
        with self.projects._connection() as connection:
            self._owned(connection, actor, project_id, run_id)
            row = connection.execute('SELECT png, expires_at FROM dashboard_run_evidence WHERE evidence_id=? AND run_id=?',
                                     (evidence_id, run_id)).fetchone()
        if row is None or row['expires_at'] is None or row['expires_at'] <= self.clock():
            raise TestRunNotFound('Test run not found.')
        return bytes(row['png'])

    def prune_expired_evidence(self, *, limit=100):
        """Trusted operator cleanup; expired access is denied even before pruning."""
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Cleanup batch size must be between 1 and 1000.')
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            removed = connection.execute('DELETE FROM dashboard_run_evidence WHERE evidence_id IN '
                '(SELECT evidence_id FROM dashboard_run_evidence WHERE coalesce(expires_at, 0)<=? '
                'ORDER BY coalesce(expires_at, 0), evidence_id LIMIT ?)', (self.clock(), limit)).rowcount
        return {'removed': removed}

    def finish(self, work, *, failed=False):
        if type(failed) is not bool:
            raise ValueError('Failure flag must be boolean.')
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = self._claimed(connection, work)
            incomplete = len(json.loads(row['results_json'])) != len(json.loads(row['case_ids_json']))
            status = 'cancelled' if row['status'] == 'cancel_requested' else ('error' if failed or incomplete or not self._configuration_current(connection, work) else 'completed')
            connection.execute('UPDATE dashboard_test_runs SET status=?, claim_token=NULL WHERE run_id=?', (status, work.run_id))
            return status

    def recover_interrupted(self):
        with worker_lock(self.projects.database), self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            cancelled = connection.execute("UPDATE dashboard_test_runs SET status='cancelled', claim_token=NULL WHERE status='cancel_requested'").rowcount
            failed = connection.execute("UPDATE dashboard_test_runs SET status='error', claim_token=NULL WHERE status='running'").rowcount
            return {'cancelled': cancelled, 'error': failed}
