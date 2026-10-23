"""Membership-bound discovery queue using the existing bounded local worker."""

from dataclasses import dataclass, field
import json
import secrets
from uuid import uuid4

from adaptive_qa.dashboard_jobs import DiscoveryJobNotFound
from adaptive_qa.organization_policy import OrganizationAction as Action
from adaptive_qa.project_store import ProjectActor, _id
from adaptive_qa.worker_lock import worker_lock
from adaptive_qa.document_target import controlled_start_path


@dataclass(frozen=True)
class OrganizationDiscoveryWork:
    job_id: str
    project_id: str
    configuration: dict
    claim_token: str = field(repr=False)


class OrganizationDiscoveryQueue:
    def __init__(self, organization_projects):
        self.scoped = organization_projects
        self.organizations = organization_projects.organizations
        self.projects = self.organizations.projects
        with self.projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_organization_discovery ('
                      'sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT UNIQUE NOT NULL, '
                      'organization_id TEXT NOT NULL, project_id TEXT NOT NULL, user_id TEXT NOT NULL, '
                      'status TEXT NOT NULL, configuration_json TEXT NOT NULL, claim_token TEXT, report_json TEXT)')
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_organization_discovery_scope '
                      'ON dashboard_organization_discovery(organization_id, project_id, sequence)')

    @staticmethod
    def _public(row, *, report=True):
        result = {k: row[k] for k in ('job_id', 'project_id', 'status')}
        if report and row['status'] == 'completed' and row['report_json'] is not None:
            result['report'] = json.loads(row['report_json'])
        return result

    def _owned(self, c, actor, organization_id, project_id, job_id, action=Action.READ):
        self.scoped._row(c, actor, organization_id, project_id, action)
        _id(job_id)
        row = c.execute('SELECT * FROM dashboard_organization_discovery '
                        'WHERE job_id=? AND organization_id=? AND project_id=?',
                        (job_id, organization_id, project_id)).fetchone()
        if row is None:
            raise DiscoveryJobNotFound('Discovery job not found.')
        return row

    def submit(self, actor, organization_id, project_id):
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self.scoped._row(c, actor, organization_id, project_id, Action.EXECUTE)
            if row['settings_json'] is None:
                raise ValueError('Saved configuration is required.')
            settings = json.loads(row['settings_json'])
            controlled_start_path(settings)
            active = "status IN ('queued', 'running', 'cancel_requested')"
            total = c.execute('SELECT count(*) FROM dashboard_organization_discovery WHERE '+active).fetchone()[0]
            # Include the personal discovery queue when it exists; never bypass its global limit.
            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_discovery_jobs'").fetchone():
                total += c.execute('SELECT count(*) FROM dashboard_discovery_jobs WHERE '+active).fetchone()[0]
            count = c.execute('SELECT count(*) FROM dashboard_organization_discovery WHERE '+active+
                              ' AND organization_id=?', (organization_id,)).fetchone()[0]
            quota = c.execute('SELECT max_pending_runs FROM dashboard_organizations WHERE organization_id=?',
                              (organization_id,)).fetchone()[0]
            if total >= 100 or count >= min(5, quota):
                raise ValueError('Discovery admission capacity reached.')
            snapshot = {key: settings[key] for key in ('base_url', 'allowed_hosts', 'allow_data_changes')}
            job_id = uuid4().hex
            c.execute('INSERT INTO dashboard_organization_discovery '
                      '(job_id, organization_id, project_id, user_id, status, configuration_json) VALUES (?, ?, ?, ?, ?, ?)',
                      (job_id, organization_id, project_id, actor.user_id, 'queued', json.dumps(snapshot)))
            return self._public(self._owned(c, actor, organization_id, project_id, job_id))

    def list(self, actor, organization_id, project_id):
        with self.projects._connection() as c:
            self.scoped._row(c, actor, organization_id, project_id)
            return [self._public(row, report=False) for row in c.execute(
                'SELECT * FROM dashboard_organization_discovery WHERE organization_id=? AND project_id=? '
                'ORDER BY sequence DESC LIMIT 20', (organization_id, project_id))]

    def get(self, actor, organization_id, project_id, job_id):
        with self.projects._connection() as c:
            row = self._owned(c, actor, organization_id, project_id, job_id)
            result = self._public(row)
            result['configuration_current'] = self._current(c, row)
            return result

    def cancel(self, actor, organization_id, project_id, job_id):
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._owned(c, actor, organization_id, project_id, job_id, Action.EXECUTE)
            status = {'queued': 'cancelled', 'running': 'cancel_requested'}.get(row['status'], row['status'])
            c.execute('UPDATE dashboard_organization_discovery SET status=? WHERE job_id=?', (status, job_id))
            return {'job_id': job_id, 'project_id': project_id, 'status': status}

    def _current(self, c, row):
        try:
            project = self.scoped._row(c, ProjectActor(row['user_id']), row['organization_id'], row['project_id'], Action.EXECUTE)
            if project['settings_json'] is None:
                return False
            settings = json.loads(project['settings_json'])
            return {key: settings[key] for key in ('base_url', 'allowed_hosts', 'allow_data_changes')} == json.loads(row['configuration_json'])
        except LookupError:
            return False

    def claim_next(self):
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            rows = c.execute("SELECT * FROM dashboard_organization_discovery WHERE status='queued' ORDER BY sequence LIMIT 100").fetchall()
            for row in rows:
                if not self._current(c, row):
                    c.execute("UPDATE dashboard_organization_discovery SET status='cancelled' WHERE job_id=?", (row['job_id'],))
                    continue
                token = secrets.token_urlsafe(32)
                c.execute("UPDATE dashboard_organization_discovery SET status='running', claim_token=? WHERE job_id=?", (token, row['job_id']))
                return OrganizationDiscoveryWork(row['job_id'], row['project_id'], json.loads(row['configuration_json']), token)
        return None

    def _claimed(self, c, work):
        if not isinstance(work, OrganizationDiscoveryWork):
            raise ValueError('A typed organization discovery claim is required.')
        row = c.execute('SELECT * FROM dashboard_organization_discovery WHERE job_id=?', (work.job_id,)).fetchone()
        if (row is None or row['project_id'] != work.project_id or row['status'] not in ('running', 'cancel_requested')
                or not secrets.compare_digest(row['claim_token'] or '', work.claim_token)):
            raise ValueError('Invalid or finalized discovery claim.')
        return row

    def cancellation_requested(self, work):
        with self.projects._connection() as c:
            row = self._claimed(c, work)
            return row['status'] == 'cancel_requested' or not self._current(c, row)

    def finish(self, work, *, failed=False, report=None):
        if type(failed) is not bool:
            raise ValueError('A boolean failure flag is required.')
        encoded = None
        if report is not None:
            if not isinstance(report, dict) or report.get('execution_authorized') is not False or report.get('project_id') != work.project_id:
                raise ValueError('A non-executing scoped report is required.')
            encoded = json.dumps(report, allow_nan=False)
            if len(encoded.encode()) > 128000:
                raise ValueError('Discovery report exceeds its bound.')
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._claimed(c, work)
            status = 'cancelled' if row['status'] == 'cancel_requested' or not self._current(c, row) else ('error' if failed or report is None else 'completed')
            c.execute('UPDATE dashboard_organization_discovery SET status=?, claim_token=NULL, report_json=? WHERE job_id=?',
                      (status, encoded if status == 'completed' else None, work.job_id))
            return status

    def recover_interrupted(self):
        with worker_lock(self.projects.database), self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            cancelled = c.execute("UPDATE dashboard_organization_discovery SET status='cancelled', claim_token=NULL WHERE status='cancel_requested'").rowcount
            failed = c.execute("UPDATE dashboard_organization_discovery SET status='error', claim_token=NULL WHERE status='running'").rowcount
            return {'cancelled': cancelled, 'error': failed}
