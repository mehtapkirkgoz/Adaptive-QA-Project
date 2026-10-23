"""Scoped UI dispatch with atomic quota, result and evidence lifecycle."""
from adaptive_qa.form_configuration import runtime_configuration

import json
import secrets
import time
from uuid import uuid4

from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.dashboard_runs import RunWork, TestRunNotFound
from adaptive_qa.dashboard_worker import configuration_fingerprint
from adaptive_qa.dashboard_evidence import validate_png
from adaptive_qa.models import TestResult
from adaptive_qa.organization_admission import OrganizationAdmission
from adaptive_qa.organization_policy import OrganizationAction as Action
from adaptive_qa.project_store import ProjectActor, _id
from adaptive_qa.smoke_checks import SMOKE_CHECKS
from adaptive_qa.worker_lock import worker_lock
from adaptive_qa.document_target import validate_runtime_binding
from adaptive_qa.discovery_target import configured_discovery


class OrganizationRunQueue:
    def __init__(self, discovery, *, clock=time.time, retention_seconds=7*86400):
        if type(retention_seconds) is not int or not 60 <= retention_seconds <= 30*86400:
            raise ValueError('Evidence retention must be 60 seconds to 30 days.')
        self.discovery = discovery
        self.scoped = discovery.scoped
        self.projects = discovery.projects
        self.clock, self.retention_seconds = clock, retention_seconds
        self.admission = OrganizationAdmission(discovery.organizations, clock=clock)
        with self.projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_organization_runs ('
                      'sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT UNIQUE NOT NULL, '
                      'organization_id TEXT NOT NULL, project_id TEXT NOT NULL, user_id TEXT NOT NULL, '
                      'discovery_job_id TEXT NOT NULL, reservation_id TEXT UNIQUE NOT NULL, '
                      'case_ids_json TEXT NOT NULL, configuration_json TEXT NOT NULL, status TEXT NOT NULL, '
                      "claim_token TEXT, results_json TEXT NOT NULL DEFAULT '[]')")
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_organization_runs_scope '
                      'ON dashboard_organization_runs(organization_id, project_id, sequence)')
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_organization_evidence ('
                      'evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, case_id TEXT NOT NULL, '
                      'png BLOB NOT NULL, expires_at REAL NOT NULL)')
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_organization_evidence_expiry '
                      'ON dashboard_organization_evidence(expires_at, evidence_id)')

    def _public(self, row):
        results = json.loads(row['results_json'])
        for item in results:
            if item.get('evidence_id') and item['evidence_expires_at'] <= self.clock():
                item.pop('evidence_id')
                item['evidence_expired'] = True
        return {'run_id': row['run_id'], 'project_id': row['project_id'], 'status': row['status'],
                'discovery_job_id': row['discovery_job_id'], 'case_ids': json.loads(row['case_ids_json']),
                'results': results, 'rerun_of': None}

    def _owned(self, c, actor, organization_id, project_id, run_id, action=Action.READ):
        self.scoped._row(c, actor, organization_id, project_id, action)
        _id(run_id)
        row = c.execute('SELECT * FROM dashboard_organization_runs WHERE run_id=? AND organization_id=? AND project_id=?',
                        (run_id, organization_id, project_id)).fetchone()
        if row is None:
            raise TestRunNotFound('Test run not found.')
        return row

    def submit(self, actor, organization_id, project_id, discovery_job_id, case_ids):
        _id(discovery_job_id)
        if (not isinstance(case_ids, tuple) or not 1 <= len(case_ids) <= 10
                or any(not isinstance(case, str) or len(case)>30 for case in case_ids)
                or len(set(case_ids)) != len(case_ids)):
            raise ValueError('Select one to ten distinct test cases.')
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            project = self.scoped._row(c, actor, organization_id, project_id, Action.EXECUTE)
            job = self.discovery._owned(c, actor, organization_id, project_id, discovery_job_id)
            if project['settings_json'] is None or job['status'] != 'completed' or not job['report_json'] or not self.discovery._current(c, job):
                raise ValueError('Current saved settings and completed discovery are required.')
            saved = json.loads(project['settings_json'])
            snapshot = runtime_configuration(saved)
            report = json.loads(job['report_json'])
            configured_discovery(snapshot)
            if (report.get('execution_authorized') is not False or report.get('project_id') != project_id
                    or report.get('discovery_status') != 'completed' or type(report.get('inspected_pages')) is not int
                    or report['inspected_pages'] < 1
                    or report.get('configuration_fingerprint') != configuration_fingerprint(snapshot)):
                raise ValueError('Discovery report does not match the controlled project.')
            decisions = {item['case_id']: item for item in report.get('cases', [])}
            catalog = {item.case_id: item for item in TEST_CASES}
            for case in case_ids:
                definition, decision = catalog.get(case), decisions.get(case)
                if (definition is None or definition.changes_data or case not in SMOKE_CHECKS
                        or decision is None or decision.get('decision') != 'selected'
                        or decision.get('test_type') != 'ui'):
                    raise ValueError('A selected read-only UI case bound to the saved target is required.')
                validate_runtime_binding(snapshot, case, decision)
            active = "status IN ('queued','running','cancel_requested')"
            total = c.execute('SELECT count(*) FROM dashboard_organization_runs WHERE '+active).fetchone()[0]
            owned = c.execute('SELECT count(*) FROM dashboard_organization_runs WHERE '+active+' AND user_id=?', (actor.user_id,)).fetchone()[0]
            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_test_runs'").fetchone():
                total += c.execute('SELECT count(*) FROM dashboard_test_runs WHERE '+active).fetchone()[0]
                owned += c.execute('SELECT count(*) FROM dashboard_test_runs WHERE '+active+' AND owner_id=?', (actor.user_id,)).fetchone()[0]
            if total >= 100 or owned >= 5:
                raise ValueError('Test run admission capacity reached.')
            reservation = self.admission._reserve(c, actor, organization_id)
            run_id = uuid4().hex
            c.execute('INSERT INTO dashboard_organization_runs (run_id, organization_id, project_id, user_id, '
                      'discovery_job_id, reservation_id, case_ids_json, configuration_json, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                      (run_id, organization_id, project_id, actor.user_id, discovery_job_id, reservation,
                       json.dumps(case_ids), json.dumps(snapshot), 'queued'))
            return self._public(self._owned(c, actor, organization_id, project_id, run_id))

    def get(self, actor, organization_id, project_id, run_id):
        with self.projects._connection() as c:
            return self._public(self._owned(c, actor, organization_id, project_id, run_id))

    def list(self, actor, organization_id, project_id):
        with self.projects._connection() as c:
            self.scoped._row(c, actor, organization_id, project_id)
            return [self._public(row) for row in c.execute('SELECT * FROM dashboard_organization_runs '
                'WHERE organization_id=? AND project_id=? ORDER BY sequence DESC LIMIT 20', (organization_id, project_id))]

    def _current(self, c, row):
        try:
            project = self.scoped._row(c, ProjectActor(row['user_id']), row['organization_id'], row['project_id'], Action.EXECUTE)
            settings = json.loads(project['settings_json'])
            return runtime_configuration(settings) == json.loads(row['configuration_json'])
        except (LookupError, TypeError):
            return False

    @staticmethod
    def _release(c, row, status):
        changed = c.execute('UPDATE dashboard_organization_admissions SET status=?, claim_token=NULL '
                            'WHERE reservation_id=? AND organization_id=? AND user_id=? AND '
                            "((status='pending' AND claim_token IS NULL) OR (status='active' AND claim_token=?))",
                            ('cancelled' if status=='cancelled' else 'finished', row['reservation_id'],
                             row['organization_id'], row['user_id'], row['claim_token'])).rowcount
        if changed != 1:
            raise ValueError('Run reservation is no longer valid.')

    def cancel(self, actor, organization_id, project_id, run_id):
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._owned(c, actor, organization_id, project_id, run_id, Action.EXECUTE)
            status = {'queued':'cancelled', 'running':'cancel_requested'}.get(row['status'], row['status'])
            if row['status']=='queued':
                self._release(c, row, 'cancelled')
            c.execute('UPDATE dashboard_organization_runs SET status=? WHERE run_id=?', (status, run_id))
            return self._public(self._owned(c, actor, organization_id, project_id, run_id))

    def claim_next(self):
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            for row in c.execute("SELECT * FROM dashboard_organization_runs WHERE status='queued' ORDER BY sequence LIMIT 100").fetchall():
                if not self._current(c, row):
                    self._release(c, row, 'cancelled')
                    c.execute("UPDATE dashboard_organization_runs SET status='cancelled' WHERE run_id=?", (row['run_id'],))
                    continue
                quota = self.admission._quota(c, row['organization_id'])
                active = c.execute("SELECT count(*) FROM dashboard_organization_admissions WHERE organization_id=? AND status='active'", (row['organization_id'],)).fetchone()[0]
                if not quota.admits('active_runs', active):
                    continue
                token = uuid4().hex
                changed = c.execute("UPDATE dashboard_organization_admissions SET status='active', claim_token=? "
                    "WHERE reservation_id=? AND organization_id=? AND user_id=? AND status='pending'",
                    (token, row['reservation_id'], row['organization_id'], row['user_id'])).rowcount
                if changed != 1:
                    raise ValueError('Missing pending run reservation.')
                c.execute("UPDATE dashboard_organization_runs SET status='running', claim_token=? WHERE run_id=?", (token,row['run_id']))
                return RunWork(row['run_id'],row['project_id'],row['user_id'],tuple(json.loads(row['case_ids_json'])),json.loads(row['configuration_json']),token)
        return None

    def _claimed(self, c, work):
        if not isinstance(work, RunWork):
            raise ValueError('A typed worker claim is required.')
        row = c.execute('SELECT * FROM dashboard_organization_runs WHERE run_id=? AND project_id=? AND user_id=?',
                        (work.run_id,work.project_id,work.owner_id)).fetchone()
        if row is None or row['status'] not in ('running','cancel_requested') or not secrets.compare_digest(row['claim_token'] or '',work.claim_token):
            raise ValueError('Invalid or finalized run claim.')
        reservation = c.execute('SELECT status, claim_token FROM dashboard_organization_admissions WHERE reservation_id=?', (row['reservation_id'],)).fetchone()
        if reservation is None or reservation['status']!='active' or not secrets.compare_digest(reservation['claim_token'] or '',work.claim_token):
            raise ValueError('Invalid quota reservation claim.')
        return row

    def cancellation_requested(self, work):
        with self.projects._connection() as c:
            row = self._claimed(c,work)
            return row['status']=='cancel_requested' or not self._current(c,row)

    def configuration_current(self, work):
        with self.projects._connection() as c:
            return self._current(c,self._claimed(c,work))

    def record_execution_context(self, work, context):
        # Advisory comparison is not enabled for organizational runs yet.
        return None

    def record_result(self, work, result, *, evidence_png=None):
        if not isinstance(result,TestResult):
            raise ValueError('A typed test result is required.')
        if evidence_png is not None:
            validate_png(evidence_png)
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._claimed(c,work)
            if row['status']=='cancel_requested' or not self._current(c,row):
                return False
            results, ids = json.loads(row['results_json']), json.loads(row['case_ids_json'])
            if len(results)>=len(ids) or result.case_id!=ids[len(results)]:
                raise ValueError('Result must match the next requested case.')
            item = {'case_id':result.case_id,'status':result.status.value,'duration_seconds':result.duration_seconds,
                    'message':f'Test execution outcome: {result.status.value}.'}
            if evidence_png is not None:
                evidence_id, expires = uuid4().hex, self.clock()+self.retention_seconds
                c.execute('INSERT INTO dashboard_organization_evidence VALUES (?, ?, ?, ?, ?)',(evidence_id,work.run_id,result.case_id,evidence_png,expires))
                item.update(evidence_id=evidence_id,evidence_expires_at=expires)
            results.append(item)
            c.execute('UPDATE dashboard_organization_runs SET results_json=? WHERE run_id=?',(json.dumps(results,allow_nan=False),work.run_id))
            return True

    def evidence(self, actor, organization_id, project_id, run_id, evidence_id):
        _id(evidence_id)
        with self.projects._connection() as c:
            self._owned(c,actor,organization_id,project_id,run_id)
            row = c.execute('SELECT png,expires_at FROM dashboard_organization_evidence WHERE run_id=? AND evidence_id=?',(run_id,evidence_id)).fetchone()
            if row is None or row['expires_at']<=self.clock():
                raise TestRunNotFound('Test run not found.')
            return bytes(row['png'])

    def prune_expired_evidence(self, *, limit=100):
        if type(limit) is not int or not 1<=limit<=1000:
            raise ValueError('A bounded cleanup limit is required.')
        with self.projects._connection() as c:
            removed = c.execute('DELETE FROM dashboard_organization_evidence WHERE evidence_id IN '
                '(SELECT evidence_id FROM dashboard_organization_evidence WHERE expires_at<=? ORDER BY expires_at,evidence_id LIMIT ?)',(self.clock(),limit)).rowcount
            return {'removed':removed}

    def finish(self, work, *, failed=False):
        if type(failed) is not bool:
            raise ValueError('A boolean failure flag is required.')
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._claimed(c,work)
            incomplete = len(json.loads(row['results_json']))!=len(json.loads(row['case_ids_json']))
            status = 'cancelled' if row['status']=='cancel_requested' or not self._current(c,row) else ('error' if failed or incomplete else 'completed')
            self._release(c,row,status)
            c.execute('UPDATE dashboard_organization_runs SET status=?,claim_token=NULL WHERE run_id=?',(status,work.run_id))
            return status

    def recover_interrupted(self):
        counts = {'cancelled':0,'error':0}
        with worker_lock(self.projects.database), self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_agent_leases'").fetchone():
                if c.execute("SELECT 1 FROM dashboard_agent_leases WHERE status='active' AND deadline>? LIMIT 1",(self.clock(),)).fetchone():
                    raise ValueError('Live agent leases must stop or expire before recovery.')
            for row in c.execute("SELECT * FROM dashboard_organization_runs WHERE status IN ('running','cancel_requested')").fetchall():
                status = 'cancelled' if row['status']=='cancel_requested' else 'error'
                self._release(c,row,status)
                c.execute('UPDATE dashboard_organization_runs SET status=?,claim_token=NULL WHERE run_id=?',(status,row['run_id']))
                counts[status]+=1
        return counts
