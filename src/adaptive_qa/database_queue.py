"""Explicit confirmed local database count jobs, with current settings and shared licenses."""
from dataclasses import dataclass, field
import json
import re
import secrets
from uuid import uuid4
from adaptive_qa.saved_database_review import SavedDatabaseExecution
from adaptive_qa.local_database_review import review_local_database,run_reviewed_local_database
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.project_store import ProjectActor, ProjectNotFound, _id
from adaptive_qa.saved_database_review import _review_database_on_connection
from adaptive_qa.licensing import LicenseError
from adaptive_qa.worker_lock import worker_lock


@dataclass(frozen=True)
class DatabaseWork:
    job_id: str
    owner_id: str
    project_id: str
    fingerprint: str
    review: SavedDatabaseExecution
    token: str = field(repr=False)


class LocalDatabaseQueue:
    def __init__(self, projects):
        self.projects = projects
        with projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_database_jobs ('
                'sequence INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT UNIQUE NOT NULL,'
                'owner_id TEXT NOT NULL,project_id TEXT NOT NULL,fingerprint TEXT NOT NULL,'
                'status TEXT NOT NULL,claim_token TEXT,result_json TEXT)')

    def _owned(self, c, actor, project_id, job_id):
        self.projects._actor(actor); _id(project_id); _id(job_id)
        row=c.execute('SELECT j.* FROM dashboard_database_jobs j JOIN dashboard_projects p '
            'ON p.project_id=j.project_id AND p.owner_id=j.owner_id '
            'WHERE j.owner_id=? AND j.project_id=? AND j.job_id=?',
            (actor.user_id,project_id,job_id)).fetchone()
        if row is None: raise ProjectNotFound('Project not found.')
        return row

    @staticmethod
    def _public(row):
        return dict(job_id=row['job_id'],project_id=row['project_id'],status=row['status'],
            scope='owned_workspace_fixtures_only',result=json.loads(row['result_json']) if row['result_json'] else None)

    def _current(self,c,row):
        public,review=_review_database_on_connection(c,ProjectActor(row['owner_id']),row['project_id'])
        if not secrets.compare_digest(public['contract_fingerprint'],row['fingerprint']):
            raise ValueError('Saved database configuration changed.')
        return review

    def submit(self,actor,project_id,confirmed_fingerprint):
        self.projects._actor(actor); _id(project_id)
        if not isinstance(confirmed_fingerprint,str) or not re.fullmatch('[0-9a-f]{64}',confirmed_fingerprint):
            raise ValueError('Explicit current review confirmation is required.')
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            public,_=_review_database_on_connection(c,actor,project_id)
            if not secrets.compare_digest(public['contract_fingerprint'],confirmed_fingerprint):
                raise ValueError('Review current saved database settings before admission.')
            if hasattr(self.projects,'admit_execution'): self.projects.admit_execution(c)
            total=owned=0
            for table,column in (('dashboard_database_jobs','owner_id'),('dashboard_api_jobs','owner_id'),('dashboard_test_runs','owner_id'),
                                 ('dashboard_interactive_jobs','owner_id'),('dashboard_organization_runs','user_id')):
                if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                    active="status IN ('queued','running','cancel_requested')"
                    total+=c.execute(f'SELECT count(*) FROM {table} WHERE '+active).fetchone()[0]
                    owned+=c.execute(f'SELECT count(*) FROM {table} WHERE '+active+f' AND {column}=?',(actor.user_id,)).fetchone()[0]
            if total>=100 or owned>=5: raise ValueError('Local database admission capacity reached.')
            job_id=uuid4().hex
            c.execute('INSERT INTO dashboard_database_jobs(job_id,owner_id,project_id,fingerprint,status) VALUES(?,?,?,?,?)',
                (job_id,actor.user_id,project_id,confirmed_fingerprint,'queued'))
            return self._public(self._owned(c,actor,project_id,job_id))

    def get(self,actor,project_id,job_id):
        with self.projects._connection() as c: return self._public(self._owned(c,actor,project_id,job_id))

    def list(self,actor,project_id):
        self.projects.get(actor,project_id)
        with self.projects._connection() as c:
            rows=c.execute('SELECT * FROM dashboard_database_jobs WHERE owner_id=? AND project_id=? '
                'ORDER BY sequence DESC LIMIT 20',(actor.user_id,project_id)).fetchall()
            return tuple(self._public(row) for row in rows)

    def cancel(self,actor,project_id,job_id):
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE'); row=self._owned(c,actor,project_id,job_id)
            status={'queued':'cancelled','running':'cancel_requested'}.get(row['status'],row['status'])
            c.execute('UPDATE dashboard_database_jobs SET status=? WHERE job_id=?',(status,job_id))
            return self._public(self._owned(c,actor,project_id,job_id))

    def claim_next(self):
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT * FROM dashboard_database_jobs WHERE status='queued' ORDER BY sequence LIMIT 1").fetchone()
            if row is None: return None
            if hasattr(self.projects,'admit_execution'):
                try: self.projects.admit_execution(c,starting=True)
                except LicenseError: return None
            try: review=self._current(c,row)
            except (ValueError,TypeError,KeyError,LookupError):
                c.execute("UPDATE dashboard_database_jobs SET status='error' WHERE job_id=?",(row['job_id'],)); return None
            token=secrets.token_urlsafe(32)
            c.execute("UPDATE dashboard_database_jobs SET status='running',claim_token=? WHERE job_id=?",(token,row['job_id']))
            return DatabaseWork(row['job_id'],row['owner_id'],row['project_id'],row['fingerprint'],review,token)

    def _claim(self,c,work):
        if not isinstance(work,DatabaseWork): raise ValueError('A typed database claim is required.')
        row=self._owned(c,ProjectActor(work.owner_id),work.project_id,work.job_id)
        if (row['status'] not in ('running','cancel_requested') or row['fingerprint']!=work.fingerprint
                or not secrets.compare_digest(row['claim_token'] or '',work.token) or self._current(c,row)!=work.review):
            raise ValueError('Invalid database claim or changed settings.')
        return row

    def cancellation_requested(self,work):
        with self.projects._connection() as c:
            try: row=self._claim(c,work)
            except (ValueError,TypeError,KeyError,LookupError): return True
            return row['status']=='cancel_requested' or (hasattr(self.projects,'execution_allowed') and not self.projects.execution_allowed())

    def finish(self,work,result):
        if not isinstance(result,TestResult) or result.case_id!=work.review.case.definition.case_id or result.evidence_paths:
            raise ValueError('A correlated database result without raw evidence is required.')
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=self._owned(c,ProjectActor(work.owner_id),work.project_id,work.job_id)
            if row['status'] not in ('running','cancel_requested') or not secrets.compare_digest(row['claim_token'] or '',work.token):
                raise ValueError('database claim was invalidated or already finalized.')
            status='completed'; outcome=result.status.value
            try: self._claim(c,work)
            except (ValueError,TypeError,KeyError,LookupError): status='error'; outcome='error'
            if row['status']=='cancel_requested' or result.status==TestStatus.CANCELLED or (hasattr(self.projects,'execution_allowed') and not self.projects.execution_allowed()):
                status='cancelled'; outcome='cancelled'
            c.execute('UPDATE dashboard_database_jobs SET status=?,result_json=?,claim_token=NULL WHERE job_id=?',
                (status,json.dumps(dict(status=outcome)),work.job_id))
            return status

    def recover_interrupted(self):
        with worker_lock(self.projects.database),self.projects._connection() as c:
            cancelled=c.execute("UPDATE dashboard_database_jobs SET status='cancelled',claim_token=NULL WHERE status='cancel_requested'").rowcount
            failed=c.execute("UPDATE dashboard_database_jobs SET status='error',claim_token=NULL WHERE status='running'").rowcount
            return dict(cancelled=cancelled,error=failed)


def process_local_database_once(queue):
    with worker_lock(queue.projects.database):
        work=queue.claim_next()
        if work is None:return None
        try:
            # The server/worker selects this root; no HTTP or environment root override.
            root=queue.projects.database.parent/'database-fixtures'/work.project_id
            if root.resolve(strict=True)!=root or not root.is_dir():
                raise ValueError('The owned workspace fixture root must not redirect.')
            configuration=work.review.configuration;binding=work.review.binding
            review=review_local_database(configuration,table=binding.table,
                expected_count=binding.expected_count,fixture_root=root)
            result=run_reviewed_local_database(review,configuration,confirmed_fingerprint=review.fingerprint,
                should_cancel=lambda:queue.cancellation_requested(work))
        except Exception:
            result=TestResult(work.review.case.definition.case_id,TestStatus.ERROR,0,'Local database worker could not complete.')
        return dict(job_id=work.job_id,project_id=work.project_id,status=queue.finish(work,result))
