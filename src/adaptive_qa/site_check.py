"""Explicit one-click local orchestration; existing guarded workers remain authoritative."""

import json
from threading import Lock, Thread
from urllib.parse import urlsplit
from uuid import uuid4

from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.dashboard_run_worker import process_run_once
from adaptive_qa.discovery_target import configured_discovery
from adaptive_qa.document_target import validate_runtime_binding
from adaptive_qa.smoke_checks import SMOKE_CHECKS
from adaptive_qa.document_checks import DOCUMENT_CHECKS
from adaptive_qa.form_checks import FORM_CHECKS
from adaptive_qa.native_form_checks import NATIVE_FORM_CHECKS,NATIVE_NUMBER_CHECKS
from adaptive_qa.project_store import ProjectNotFound, OwnedProject, _id
from adaptive_qa.project_settings import validate_settings
from adaptive_qa.worker_lock import worker_lock


ACTIVE = ('discovering', 'testing', 'cancelling')


class SiteCheckBusy(ValueError):
    """One managed check per local runtime; never build an unbounded thread queue."""


class _Discovery(DashboardDiscoveryQueue):
    def claim_next(self):
        return super().claim_next(job_id=self.only_id)


class _Runs(DashboardRunQueue):
    def claim_next(self):
        return super().claim_next(run_id=self.only_id)


class SiteChecks:
    def __init__(self, projects, *, free=False):
        self.projects, self.server_id, self.lock = projects, uuid4().hex, Lock()
        self.free = free
        self.thread = None
        self.transition = Lock()
        self.discovery, self.runs = _Discovery(projects), _Runs(projects)
        with projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_site_checks ('
                'sequence INTEGER PRIMARY KEY AUTOINCREMENT, check_id TEXT UNIQUE NOT NULL, '
                'owner_id TEXT NOT NULL, project_id TEXT NOT NULL, server_id TEXT NOT NULL, '
                'status TEXT NOT NULL, url TEXT NOT NULL, discovery_id TEXT, run_id TEXT, '
                "summary_json TEXT NOT NULL DEFAULT '{}')")

    def _row(self, actor, check_id):
        self.projects._actor(actor); _id(check_id)
        with self.projects._connection() as c:
            row = c.execute('SELECT * FROM dashboard_site_checks WHERE check_id=? AND owner_id=?',
                            (check_id, actor.user_id)).fetchone()
        if row is None:
            raise ProjectNotFound('Site check not found.')
        self.projects.get(actor, row['project_id'])
        return dict(row)

    def get(self, actor, check_id):
        row = self._row(actor, check_id)
        status = row['status']
        if status in ACTIVE and row['server_id'] != self.server_id:
            status = 'interrupted'  # Never restart target work just because a browser/server reopened.
        out = {k: row[k] for k in ('check_id', 'project_id', 'url')}
        out.update(status=status, **json.loads(row['summary_json']))
        if row['run_id']:
            run = self.runs.get(actor, row['project_id'], row['run_id'])
            out['results'] = run['results']
            out['run_id'] = run['run_id']
            if status == 'completed' and run['results'] and all(r['status'] in ('error', 'blocked', 'cancelled') for r in run['results']):
                out['status'] = 'execution_error'
                out['diagnostic_code'] = 'no_reliable_test_outcomes'
            elif status == 'completed' and any(r['status'] not in ('passed','failed') for r in run['results']):
                out['status'] = 'partial'
            out['outcome_counts'] = {key: sum(r['status'] == key for r in run['results'])
                                     for key in ('passed','failed','error','blocked','cancelled','skipped')}

        return out

    def list(self, actor):
        self.projects._actor(actor)
        with self.projects._connection() as c:
            ids = [r[0] for r in c.execute('SELECT check_id FROM dashboard_site_checks '
                'WHERE owner_id=? ORDER BY sequence DESC LIMIT 20', (actor.user_id,))]
        return [self.get(actor, check_id) for check_id in ids]

    def _update(self, check_id, **values):
        allowed = {'status', 'discovery_id', 'run_id', 'summary_json'}
        if not values or not set(values) <= allowed:
            raise ValueError('Invalid check update.')
        with self.projects._connection() as c:
            c.execute('UPDATE dashboard_site_checks SET '+','.join(k+'=?' for k in values)
                      +' WHERE check_id=?', (*values.values(), check_id))

    def submit(self, actor, url, *, project_id=None):
        # Pure syntax/IP-literal validation before saving anything. DNS remains guarded at execution.
        if not isinstance(url, str) or len(url) > 512:
            raise ValueError('A bounded HTTPS URL is required.')
        url = url.strip()
        parsed = urlsplit(url)
        settings = dict(base_url=url, allowed_hosts=[parsed.hostname or ''], allow_data_changes=False,
                        secret_references={}, form_mappings=[])
        self.projects._actor(actor)
        validate_settings(OwnedProject('0'*32, actor.user_id, (parsed.hostname or 'Site check')[:100]), settings)
        configured_discovery(settings)
        if not self.lock.acquire(blocking=False):
            raise SiteCheckBusy('Another site check is active.')
        try:
            # Separate orchestration lock prevents two local servers admitting overlapping managed checks.
            gate = worker_lock(self.projects.database.with_suffix('.site-check.sqlite'))
            gate.__enter__()
        except Exception:
            self.lock.release()
            raise SiteCheckBusy('Another site check is active.') from None
        try:
            self.projects._actor(actor)
            if project_id is not None:
                project = self.projects.get(actor, project_id)
            else:
                owned = self.projects.list(actor, limit=100)
                match = next((p for p in owned if self.projects.configuration(actor, p.project_id).get('base_url') == url), None)
                project = match or (owned[0] if owned and self.free else None)
                if project is None:
                    project = self.projects.create(actor, (parsed.hostname or 'Site check')[:100])
            with self.projects._connection() as c:
                for table in ('dashboard_discovery_jobs', 'dashboard_test_runs', 'dashboard_interactive_jobs', 'dashboard_api_jobs', 'dashboard_database_jobs'):
                    if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                        if c.execute('SELECT 1 FROM '+table+" WHERE project_id=? AND status IN ('running','cancel_requested')", (project.project_id,)).fetchone():
                            raise SiteCheckBusy('This project already has running work.')
            previous = self.projects.configuration(actor, project.project_id)
            # Do not silently discard an owner's advanced contracts or data policy.
            if (previous.get('allow_data_changes') or previous.get('form_mappings')
                    or any(previous.get(k) for k in ('local_form_binding', 'local_api_binding', 'local_database_binding', 'secret_references'))):
                raise ValueError('This project has advanced settings; use Advanced settings or a separate project.')
            self.projects.save_configuration(actor, project.project_id, settings)
            job = self.discovery.submit(actor, project.project_id)
            check_id = uuid4().hex
            with self.projects._connection() as c:
                c.execute('INSERT INTO dashboard_site_checks '
                    '(check_id,owner_id,project_id,server_id,status,url,discovery_id) VALUES (?,?,?,?,?,?,?)',
                    (check_id, actor.user_id, project.project_id, self.server_id, 'discovering', url, job['job_id']))
            thread = Thread(target=self._work, args=(actor, check_id, gate), daemon=True,
                            name='adaptive-site-check')
            self.thread = thread
            try:
                thread.start()
            except Exception:
                self.discovery.cancel(actor, project.project_id, job['job_id'])
                self._update(check_id, status='error')
                raise
            return {'check_id':check_id, 'project_id':project.project_id, 'url':url, 'status':'discovering'}
        except Exception:
            gate.__exit__(None, None, None)
            self.lock.release()
            raise

    def shutdown(self):
        from adaptive_qa.project_store import ProjectActor
        with self.projects._connection() as c:
            rows = c.execute("SELECT check_id,owner_id FROM dashboard_site_checks WHERE server_id=? AND status IN ('discovering','testing','cancelling')", (self.server_id,)).fetchall()
        for row in rows:
            self.cancel(ProjectActor(row['owner_id']), row['check_id'])
        if self.thread is not None:
            self.thread.join(timeout=5)

    def cancel(self, actor, check_id):
        row = self._row(actor, check_id)
        with self.transition:
            row = self._row(actor, check_id)
            if row['status'] in ACTIVE:
                self._update(check_id, status='cancelling')
                if row['discovery_id']:
                    self.discovery.cancel(actor, row['project_id'], row['discovery_id'])
                if row['run_id']:
                    self.runs.cancel(actor, row['project_id'], row['run_id'])
        return self.get(actor, check_id)

    def _work(self, actor, check_id, gate):
        try:
            row = self._row(actor, check_id)
            project_id = row['project_id']
            self.discovery.only_id = row['discovery_id']
            process_discovery_once(self.discovery)
            job = self.discovery.get(actor, project_id, row['discovery_id'])
            if self._row(actor, check_id)['status'] == 'cancelling' or job['status'] == 'cancelled':
                self._update(check_id, status='cancelled'); return
            if job['status'] != 'completed':
                from adaptive_qa.discovery_diagnostics import ACCESS_DIAGNOSTICS
                code=job.get('diagnostic_code','inspection_unavailable')
                if not isinstance(code,str) or code not in ACCESS_DIAGNOSTICS:code='inspection_unavailable'
                self._update(check_id, status='error',summary_json=json.dumps(dict(diagnostic_code=code))); return
            report = job['report']
            settings = self.projects.configuration(actor, project_id)
            eligible = []
            for case in report['cases']:
                if (case['decision'] != 'selected' or case['test_type'] != 'ui'
                        or case['changes_data'] or case['case_id'] not in SMOKE_CHECKS
                        or case['case_id'] not in {*DOCUMENT_CHECKS, *FORM_CHECKS}):
                    continue
                if case['case_id'] in NATIVE_NUMBER_CHECKS and case['case_id'] not in report.get('native_number_candidates',[]):
                    continue
                if case['case_id'] in NATIVE_FORM_CHECKS and case['case_id'] not in NATIVE_NUMBER_CHECKS and not report.get('native_email_candidate'):
                    continue
                try:
                    validate_runtime_binding(settings, case['case_id'], case)
                except ValueError:
                    continue
                eligible.append(case['case_id'])
            eligible.sort(key=lambda case:0 if case in DOCUMENT_CHECKS else 1 if case in NATIVE_FORM_CHECKS else 2)
            selected = eligible[:10]
            summary = dict(inspected_pages=report['inspected_pages'], requested=len(selected),
                not_run=len(report['cases'])-len(selected),
                names={c['case_id']: c['name'] for c in report['cases'] if c['case_id'] in selected},
                execution_scope='source_html_native_validity_and_read_only_forms',
                limitations=['source_html_only', 'read_only', 'five_page_discovery', 'ten_check_limit', 'no_login_api_database', 'no_ai_claim'])
            self._update(check_id, summary_json=json.dumps(summary))
            # Cancellation and child-run publication share a transition lock.
            with self.transition:
                if self._row(actor, check_id)['status'] == 'cancelling':
                    self._update(check_id, status='cancelled'); return
                if not selected:
                    self._update(check_id, status='no_tests'); return
                run = self.runs.submit(actor, project_id, row['discovery_id'], tuple(selected))
                self._update(check_id, run_id=run['run_id'], status='testing')
            self.runs.only_id = run['run_id']
            process_run_once(self.runs)
            final = self.runs.get(actor, project_id, run['run_id'])
            self._update(check_id, status=final['status'] if final['status'] in ('completed', 'cancelled') else 'error')
        except Exception:
            # Fixed outcome only; raw exceptions/headers/body/secrets never reach the summary.
            row = self._row(actor, check_id)
            if row['discovery_id']:
                self.discovery.cancel(actor, row['project_id'], row['discovery_id'])
            if row['run_id']:
                self.runs.cancel(actor, row['project_id'], row['run_id'])
            self._update(check_id, status='error')
        finally:
            gate.__exit__(None, None, None)
            self.lock.release()
