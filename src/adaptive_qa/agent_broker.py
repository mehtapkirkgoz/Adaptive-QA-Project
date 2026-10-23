"""Project-bound agent leases using the existing atomic shared-run ledger."""

import json
from uuid import uuid4

from adaptive_qa.agent_registry import AgentAuthenticationError
from adaptive_qa.dashboard_runs import RunWork
from adaptive_qa.organization_runs import OrganizationRunQueue
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.worker_lock import worker_lock


PILOT_CASES = frozenset(('LOGIN-001','SEARCH-001'))


class AgentBroker:
    def __init__(self, registry, runs):
        if registry.projects.database != runs.projects.database:
            raise ValueError('Agent registry and runs must share private storage.')
        self.registry,self.runs = registry,runs
        self.projects = runs.projects
        with self.projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_agent_leases ('
                      'lease_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, run_id TEXT UNIQUE NOT NULL, '
                      'deadline REAL NOT NULL, status TEXT NOT NULL)')
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_agent_leases_active '
                      'ON dashboard_agent_leases(status, deadline)')

    def claim(self, identity):
        self.sweep()
        with worker_lock(self.projects.database),self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.registry.recheck(c,identity)
            if c.execute("SELECT 1 FROM dashboard_agent_leases WHERE agent_id=? AND status='active'",(identity.agent_id,)).fetchone():
                return None
            rows = c.execute("SELECT * FROM dashboard_organization_runs WHERE organization_id=? AND project_id=? AND status='queued' ORDER BY sequence LIMIT 100",
                             (identity.organization_id,identity.project_id)).fetchall()
            for row in rows:
                if not self.runs._current(c,row):
                    self.runs._release(c,row,'cancelled')
                    c.execute("UPDATE dashboard_organization_runs SET status='cancelled' WHERE run_id=?",(row['run_id'],))
                    continue
                cases = tuple(json.loads(row['case_ids_json']))
                if not set(cases)<=PILOT_CASES:
                    continue
                quota = self.runs.admission._quota(c,identity.organization_id)
                active = c.execute("SELECT count(*) FROM dashboard_organization_admissions WHERE organization_id=? AND status='active'",(identity.organization_id,)).fetchone()[0]
                if not quota.admits('active_runs',active):
                    return None
                token = uuid4().hex
                changed = c.execute("UPDATE dashboard_organization_admissions SET status='active',claim_token=? "
                    "WHERE reservation_id=? AND organization_id=? AND user_id=? AND status='pending'",
                    (token,row['reservation_id'],identity.organization_id,row['user_id'])).rowcount
                if changed!=1:
                    raise ValueError('Invalid pending reservation.')
                c.execute("UPDATE dashboard_organization_runs SET status='running',claim_token=? WHERE run_id=?",(token,row['run_id']))
                lease_id,deadline = uuid4().hex,self.registry._now()+120
                c.execute('INSERT INTO dashboard_agent_leases VALUES (?, ?, ?, ?, ?)',(lease_id,identity.agent_id,row['run_id'],deadline,'active'))
                return {'lease_id':lease_id,'run_id':row['run_id'],'case_ids':list(cases),
                        'configuration':json.loads(row['configuration_json']),'lease_seconds':120}
        return None

    def _lease(self,c,identity,lease_id):
        self.registry.recheck(c,identity)
        lease = c.execute('SELECT * FROM dashboard_agent_leases WHERE lease_id=? AND agent_id=?',(lease_id,identity.agent_id)).fetchone()
        if lease is None or lease['status']!='active' or lease['deadline']<=self.registry._now():
            raise AgentAuthenticationError('Agent request rejected.')
        row = c.execute('SELECT * FROM dashboard_organization_runs WHERE run_id=? AND organization_id=? AND project_id=?',
                        (lease['run_id'],identity.organization_id,identity.project_id)).fetchone()
        if row is None:
            raise AgentAuthenticationError('Agent request rejected.')
        return row

    @staticmethod
    def _work(row):
        return RunWork(row['run_id'],row['project_id'],row['user_id'],tuple(json.loads(row['case_ids_json'])),
                       json.loads(row['configuration_json']),row['claim_token'])

    def _guarded(self,identity,lease_id):
        broker = self
        class GuardedRuns(OrganizationRunQueue):
            def _claimed(self,c,work):
                bound = broker._lease(c,identity,lease_id)
                if bound['run_id']!=work.run_id:
                    raise AgentAuthenticationError('Agent request rejected.')
                return super()._claimed(c,work)
        queue = GuardedRuns(self.runs.discovery,clock=self.runs.clock,retention_seconds=self.runs.retention_seconds)
        with self.projects._connection() as c:
            work = self._work(self._lease(c,identity,lease_id))
        return queue,work

    def check(self,identity,lease_id):
        queue,work = self._guarded(identity,lease_id)
        return {'cancel_requested':queue.cancellation_requested(work)}

    def result(self,identity,lease_id,case_id,status,duration_seconds,*,png=None):
        if png is not None and (not isinstance(png,bytes) or len(png)>256*1024):
            raise ValueError('Agent evidence exceeds the pilot limit.')
        result = TestResult(case_id,TestStatus(status),duration_seconds,'Authenticated agent execution outcome.')
        queue,work = self._guarded(identity,lease_id)
        return {'accepted':queue.record_result(work,result,evidence_png=png)}

    def finish(self,identity,lease_id,*,failed=False):
        queue,work = self._guarded(identity,lease_id)
        status = queue.finish(work,failed=failed)
        with self.projects._connection() as c:
            c.execute("UPDATE dashboard_agent_leases SET status='finished' WHERE lease_id=? AND agent_id=?",(lease_id,identity.agent_id))
        return {'status':status}

    def sweep(self):
        """Bounded trusted maintenance, no retry or requeue of abandoned work."""
        cancelled = 0
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            rows = c.execute("SELECT * FROM dashboard_agent_leases WHERE status='active' ORDER BY deadline LIMIT 100").fetchall()
            for lease in rows:
                row = c.execute('SELECT * FROM dashboard_organization_runs WHERE run_id=?',(lease['run_id'],)).fetchone()
                agent = c.execute('SELECT * FROM dashboard_agents WHERE agent_id=?',(lease['agent_id'],)).fetchone()
                valid = lease['deadline']>self.registry._now()
                try:
                    self.registry._current(c,agent)
                except AgentAuthenticationError:
                    valid = False
                if row is None or row['status'] not in ('running','cancel_requested'):
                    c.execute("UPDATE dashboard_agent_leases SET status='finished' WHERE lease_id=?",(lease['lease_id'],))
                elif not valid or row['status']=='cancel_requested' or not self.runs._current(c,row):
                    self.runs._release(c,row,'cancelled')
                    c.execute("UPDATE dashboard_organization_runs SET status='cancelled',claim_token=NULL WHERE run_id=?",(row['run_id'],))
                    c.execute("UPDATE dashboard_agent_leases SET status='cancelled' WHERE lease_id=?",(lease['lease_id'],))
                    cancelled+=1
        return {'cancelled':cancelled}
