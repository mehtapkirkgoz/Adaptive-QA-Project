"""Owner-bound local discovery dispatch, separate from legacy unowned test jobs."""

from dataclasses import dataclass, field
import json
import secrets
from uuid import uuid4

from adaptive_qa.project_store import ProjectStore, ProjectNotFound, _id
from adaptive_qa.worker_lock import worker_lock


class DiscoveryJobNotFound(LookupError):
    """Unknown and other-owner jobs have the same outcome."""


@dataclass(frozen=True)
class DiscoveryWork:
    job_id: str
    project_id: str
    configuration: dict
    claim_token: str = field(repr=False)


class DashboardDiscoveryQueue:
    """Trusted dispatch core; HTTP endpoints and worker execution are not wired yet."""

    def __init__(self, projects: ProjectStore):
        self.projects = projects
        with projects._connection() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS dashboard_discovery_jobs ('
                'sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT UNIQUE NOT NULL, '
                'project_id TEXT NOT NULL, owner_id TEXT NOT NULL, status TEXT NOT NULL, '
                'configuration_json TEXT NOT NULL, claim_token TEXT)')
            connection.execute('CREATE INDEX IF NOT EXISTS dashboard_discovery_owner '
                'ON dashboard_discovery_jobs(owner_id, sequence)')
            columns = {row['name'] for row in connection.execute('PRAGMA table_info(dashboard_discovery_jobs)')}
            if 'report_json' not in columns:
                connection.execute('ALTER TABLE dashboard_discovery_jobs ADD COLUMN report_json TEXT')

    @staticmethod
    def _public(row):
        result = {'job_id': row['job_id'], 'project_id': row['project_id'], 'status': row['status']}
        if row['status'] == 'completed' and row['report_json'] is not None:
            result['report'] = json.loads(row['report_json'])
        return result

    def _owned(self, connection, actor, project_id, job_id):
        self.projects._actor(actor)
        _id(project_id)
        _id(job_id)
        row = connection.execute('SELECT j.* FROM dashboard_discovery_jobs j '
            'JOIN dashboard_projects p ON p.project_id=j.project_id AND p.owner_id=j.owner_id '
            'WHERE j.job_id=? AND j.project_id=? AND j.owner_id=?',
            (job_id, project_id, actor.user_id)).fetchone()
        if row is None:
            raise DiscoveryJobNotFound('Discovery job not found.')
        return row

    def submit(self, actor, project_id):
        self.projects._actor(actor)
        _id(project_id)
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT s.settings_json FROM dashboard_projects p '
                'LEFT JOIN dashboard_project_settings s ON s.project_id=p.project_id '
                'WHERE p.project_id=? AND p.owner_id=?', (project_id, actor.user_id)).fetchone()
            if row is None:
                raise ProjectNotFound('Project not found.')
            if row['settings_json'] is None:
                raise ValueError('Saved configuration is required.')
            settings = json.loads(row['settings_json'])
            if settings['base_url'] not in ('http://127.0.0.1:8000', 'http://127.0.0.1:8000/'):
                raise ValueError('Only the controlled local root fixture is supported.')
            if '127.0.0.1' not in settings['allowed_hosts']:
                raise ValueError('The controlled local host must be authorized.')
            active = "status IN ('queued', 'running', 'cancel_requested')"
            count = connection.execute('SELECT count(*) FROM dashboard_discovery_jobs WHERE ' + active).fetchone()[0]
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_organization_discovery'").fetchone():
                count += connection.execute('SELECT count(*) FROM dashboard_organization_discovery WHERE ' + active).fetchone()[0]
            owned = connection.execute('SELECT count(*) FROM dashboard_discovery_jobs WHERE ' + active + ' AND owner_id=?', (actor.user_id,)).fetchone()[0]
            if count >= 100 or owned >= 5:
                raise ValueError('Discovery admission limit reached.')
            # Secret references are not needed for read-only local discovery and are excluded.
            snapshot = {key: settings[key] for key in ('base_url', 'allowed_hosts', 'allow_data_changes')}
            job_id = uuid4().hex
            connection.execute('INSERT INTO dashboard_discovery_jobs '
                '(job_id, project_id, owner_id, status, configuration_json) VALUES (?, ?, ?, ?, ?)',
                (job_id, project_id, actor.user_id, 'queued', json.dumps(snapshot)))
            return self._public(self._owned(connection, actor, project_id, job_id))

    def get(self, actor, project_id, job_id):
        with self.projects._connection() as connection:
            return self._public(self._owned(connection, actor, project_id, job_id))

    def list(self, actor, project_id):
        self.projects.get(actor, project_id)
        with self.projects._connection() as connection:
            rows = connection.execute('SELECT j.* FROM dashboard_discovery_jobs j '
                'JOIN dashboard_projects p ON p.project_id=j.project_id AND p.owner_id=j.owner_id '
                'WHERE j.project_id=? AND j.owner_id=? ORDER BY j.sequence DESC LIMIT 20',
                (project_id, actor.user_id)).fetchall()
        # History lists exclude reports; read one authorized job for its bounded report.
        return tuple({'job_id': row['job_id'], 'project_id': row['project_id'], 'status': row['status']} for row in rows)

    def cancel(self, actor, project_id, job_id):
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = self._owned(connection, actor, project_id, job_id)
            status = {'queued': 'cancelled', 'running': 'cancel_requested'}.get(row['status'], row['status'])
            connection.execute('UPDATE dashboard_discovery_jobs SET status=? WHERE job_id=?', (status, job_id))
            return {'job_id': job_id, 'project_id': project_id, 'status': status}

    def claim_next(self):
        """Trusted worker-only operation; claims are never returned through owner reads."""
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute("SELECT * FROM dashboard_discovery_jobs WHERE status='queued' ORDER BY sequence LIMIT 1").fetchone()
            if row is None:
                return None
            token = secrets.token_urlsafe(32)
            connection.execute("UPDATE dashboard_discovery_jobs SET status='running', claim_token=? WHERE job_id=?", (token, row['job_id']))
            return DiscoveryWork(row['job_id'], row['project_id'], json.loads(row['configuration_json']), token)

    def cancellation_requested(self, work):
        with self.projects._connection() as connection:
            row = connection.execute('SELECT status, claim_token FROM dashboard_discovery_jobs WHERE job_id=?', (work.job_id,)).fetchone()
        if row is None or not secrets.compare_digest(row['claim_token'] or '', work.claim_token):
            raise ValueError('Invalid worker claim.')
        return row['status'] == 'cancel_requested'

    def finish(self, work, *, failed=False, report=None):
        if type(failed) is not bool:
            raise ValueError('Failure flag must be boolean.')
        encoded = None
        if report is not None:
            if (not isinstance(report, dict) or report.get('execution_authorized') is not False
                    or report.get('project_id') != work.project_id):
                raise ValueError('A non-executing project report is required.')
            encoded = json.dumps(report, allow_nan=False)
            if len(encoded.encode('utf-8')) > 128000:
                raise ValueError('Discovery report is too large.')
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT status, claim_token FROM dashboard_discovery_jobs WHERE job_id=?', (work.job_id,)).fetchone()
            if (row is None or row['status'] not in ('running', 'cancel_requested')
                    or not secrets.compare_digest(row['claim_token'] or '', work.claim_token)):
                raise ValueError('Invalid or finalized worker claim.')
            status = 'cancelled' if row['status'] == 'cancel_requested' else ('error' if failed else 'completed')
            connection.execute('UPDATE dashboard_discovery_jobs SET status=?, claim_token=NULL, report_json=? WHERE job_id=?',
                               (status, encoded if status == 'completed' else None, work.job_id))
            return status

    def recover_interrupted(self):
        """Operator-only, never replay work; refuse recovery while an executor holds the lock."""
        with worker_lock(self.projects.database), self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            cancelled = connection.execute("UPDATE dashboard_discovery_jobs SET status='cancelled', claim_token=NULL WHERE status='cancel_requested'").rowcount
            failed = connection.execute("UPDATE dashboard_discovery_jobs SET status='error', claim_token=NULL WHERE status='running'").rowcount
            return {'cancelled': cancelled, 'error': failed}
