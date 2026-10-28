"""Transactional owned-fixture dispatch, separate from the 100-case catalog."""
from dataclasses import asdict, dataclass, field
import json
import secrets
from uuid import uuid4

from adaptive_qa.form_configuration import decode_form_mappings
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.interactive_review import SavedInteractiveReview, _review_on_connection
from adaptive_qa.licensing import LicenseError
from adaptive_qa.project_store import ProjectActor, ProjectNotFound, _id
from adaptive_qa.worker_lock import worker_lock


@dataclass(frozen=True)
class InteractiveWork:
    job_id: str
    owner_id: str
    project_id: str
    review: SavedInteractiveReview
    claim_token: str = field(repr=False)


def _snapshot(review):
    from adaptive_qa.website_login import SavedWebsiteLoginReview
    if isinstance(review,SavedWebsiteLoginReview):
        return dict(profile='website_login',check_id=review.check_id,contract_fingerprint=review.fingerprint())
    from adaptive_qa.demo_login_review import SavedDemoLoginReview
    if isinstance(review,SavedDemoLoginReview):
        return dict(profile='authorized_login_demo',scenario=review.plan.scenario.value,
            configuration_fingerprint=review.configuration_fingerprint,contract_fingerprint=review.fingerprint())
    form=review.submission.form
    from adaptive_qa.public_form_review import SavedPublicFormReview
    if isinstance(review,SavedPublicFormReview):
        return dict(profile='public_https',completion=json.loads(json.dumps(asdict(form.completion))),
            timeout_seconds=form.timeout_seconds,contract_fingerprint=review.submission.fingerprint(),
            configuration_fingerprint=form.configuration_fingerprint)
    return dict(fixture_id=review.fixture_id,completion=json.loads(json.dumps(asdict(form.completion))),
        timeout_seconds=form.timeout_seconds,contract_fingerprint=review.submission.fingerprint(),
        configuration_fingerprint=form.configuration_fingerprint)


class OwnedInteractiveQueue:
    """Explicit internal dispatch only; constructing/reviewing a plan never calls submit."""
    def __init__(self,projects):
        self.projects=projects
        with projects._connection() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS dashboard_interactive_jobs ('
                'sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL UNIQUE, '
                'owner_id TEXT NOT NULL, project_id TEXT NOT NULL, review_json TEXT NOT NULL, '
                'status TEXT NOT NULL, claim_token TEXT, result_json TEXT)')

    def _owned(self,connection,actor,project_id,job_id):
        self.projects._actor(actor);_id(project_id);_id(job_id)
        row=connection.execute('SELECT j.* FROM dashboard_interactive_jobs j '
            'JOIN dashboard_projects p ON p.project_id=j.project_id AND p.owner_id=j.owner_id '
            'WHERE j.job_id=? AND j.project_id=? AND j.owner_id=?',(job_id,project_id,actor.user_id)).fetchone()
        if row is None:raise ProjectNotFound('Project not found.')
        return row

    @staticmethod
    def _public(row):
        data=json.loads(row['review_json'])
        if data.get('profile')=='website_login':
            return dict(job_id=row['job_id'],project_id=row['project_id'],status=row['status'],
                scope='website_login',check_id=data['check_id'],result=json.loads(row['result_json']) if row['result_json'] else None)
        if data.get('profile')=='authorized_login_demo':
            return dict(job_id=row['job_id'],project_id=row['project_id'],status=row['status'],
                scope='authorized_login_demo',scenario=data['scenario'],result=json.loads(row['result_json']) if row['result_json'] else None)
        return dict(job_id=row['job_id'],project_id=row['project_id'],status=row['status'],
                    scope='reviewed_public_https' if json.loads(row['review_json']).get('profile')=='public_https' else 'owned_loopback_only' if json.loads(row['review_json']).get('fixture_id') is None else 'owned_fixture_only',result=json.loads(row['result_json']) if row['result_json'] else None)

    def _current(self,connection,row):
        data=json.loads(row['review_json'])
        if isinstance(data,dict) and data.get('profile')=='website_login':
            from adaptive_qa.website_login import _review_on_connection as website_review
            if set(data)!={'profile','check_id','contract_fingerprint'}:raise ValueError('Invalid login review.')
            review=website_review(connection,ProjectActor(row['owner_id']),row['project_id'],data['check_id'])
            if _snapshot(review)!=data:raise ValueError('Login review changed.')
            return review
        if isinstance(data,dict) and data.get('profile')=='authorized_login_demo':
            if set(data)!={'profile','scenario','configuration_fingerprint','contract_fingerprint'}:
                raise ValueError('Invalid queued demo snapshot.')
            from adaptive_qa.demo_login_review import _review_on_connection as demo_review
            from adaptive_qa.demo_login_contract import DemoLoginScenario
            review=demo_review(connection,ProjectActor(row['owner_id']),row['project_id'],
                scenario=DemoLoginScenario(data['scenario']),authorized_demo=True)
            if _snapshot(review)!=data:raise ValueError('Queued demo review changed.')
            return review
        if isinstance(data,dict) and data.get('profile')=='public_https':
            if set(data)!={'profile','completion','timeout_seconds','contract_fingerprint','configuration_fingerprint'}:
                raise ValueError('Invalid queued HTTPS snapshot.')
            from adaptive_qa.public_form_review import _review_on_connection as public_review
            completion=decode_form_mappings({'project_id':row['project_id'],'mappings':[data['completion']]}).mappings[0]
            review=public_review(connection,ProjectActor(row['owner_id']),row['project_id'],completion=completion,
                timeout_seconds=data['timeout_seconds'])
            if _snapshot(review)!=data:raise ValueError('Queued HTTPS settings changed.')
            return review
        if not isinstance(data,dict) or set(data)!={'fixture_id','completion','timeout_seconds','contract_fingerprint','configuration_fingerprint'}:
            raise ValueError('Invalid queued interactive snapshot.')
        completion=decode_form_mappings({'project_id':row['project_id'],'mappings':[data['completion']]}).mappings[0]
        review=_review_on_connection(connection,ProjectActor(row['owner_id']),row['project_id'],
            fixture_id=data['fixture_id'],completion=completion,timeout_seconds=data['timeout_seconds'])
        if _snapshot(review)!=data:raise ValueError('Queued interactive settings changed.')
        return review

    def submit(self,actor,review):
        self.projects._actor(actor)
        if not isinstance(review,SavedInteractiveReview):raise ValueError('A typed saved review is required.')
        return self._admit_review(actor,review)

    def submit_public(self,actor,review,*,confirmed_fingerprint):
        """Internal explicit single-operation admission; no HTTP route activation."""
        self.projects._actor(actor)
        from adaptive_qa.public_form_review import SavedPublicFormReview
        if not isinstance(review,SavedPublicFormReview):raise ValueError('A typed saved HTTPS review is required.')
        if (not isinstance(confirmed_fingerprint,str) or len(confirmed_fingerprint)!=64 or
                any(character not in '0123456789abcdef' for character in confirmed_fingerprint) or
                not secrets.compare_digest(confirmed_fingerprint,review.submission.fingerprint())):
            raise ValueError('Confirm the exact current single-operation review.')
        return self._admit_review(actor,review)

    def _admit_review(self,actor,review):
        if actor.user_id!=review.owner_id:raise ProjectNotFound('Project not found.')
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            from adaptive_qa.demo_login_review import SavedDemoLoginReview
            from adaptive_qa.website_login import SavedWebsiteLoginReview
            project_id=review.project_id if isinstance(review,(SavedDemoLoginReview,SavedWebsiteLoginReview)) else review.submission.form.project_id
            snapshot=_snapshot(review)
            current=self._current(connection,dict(review_json=json.dumps(snapshot),owner_id=actor.user_id,
                project_id=project_id))
            if current!=review:raise ValueError('Review current settings before admission.')
            if hasattr(self.projects,'admit_execution'):self.projects.admit_execution(connection)
            active="status IN ('queued','running','cancel_requested')"
            total=connection.execute('SELECT count(*) FROM dashboard_interactive_jobs WHERE '+active).fetchone()[0]
            owned=connection.execute('SELECT count(*) FROM dashboard_interactive_jobs WHERE '+active+' AND owner_id=?',(actor.user_id,)).fetchone()[0]
            for table,owner_column in (('dashboard_test_runs','owner_id'),('dashboard_organization_runs','user_id'),('dashboard_api_jobs','owner_id'),('dashboard_database_jobs','owner_id')):
                if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                    total+=connection.execute(f'SELECT count(*) FROM {table} WHERE '+active).fetchone()[0]
                    owned+=connection.execute(f'SELECT count(*) FROM {table} WHERE '+active+f' AND {owner_column}=?',(actor.user_id,)).fetchone()[0]
            if total>=100 or owned>=5:raise ValueError('Interactive admission limit reached.')
            job_id=uuid4().hex
            connection.execute('INSERT INTO dashboard_interactive_jobs '
                '(job_id,owner_id,project_id,review_json,status) VALUES (?,?,?,?,?)',
                (job_id,actor.user_id,project_id,json.dumps(_snapshot(review)), 'queued'))
            return self._public(self._owned(connection,actor,project_id,job_id))

    def submit_demo(self,actor,review,*,confirmed_fingerprint):
        self.projects._actor(actor)
        from adaptive_qa.demo_login_review import SavedDemoLoginReview
        if not isinstance(review,SavedDemoLoginReview):raise ValueError('An explicit saved demo review is required.')
        if (not isinstance(confirmed_fingerprint,str) or len(confirmed_fingerprint)!=64
                or any(c not in '0123456789abcdef' for c in confirmed_fingerprint)
                or not secrets.compare_digest(confirmed_fingerprint,review.fingerprint())):
            raise ValueError('Confirm this exact demo scenario.')
        return self._admit_review(actor,review)

    def submit_website_login(self,actor,review,*,confirmed_fingerprint,authorized):
        from adaptive_qa.website_login import SavedWebsiteLoginReview
        self.projects._actor(actor)
        if (not isinstance(review,SavedWebsiteLoginReview) or authorized is not True
                or not isinstance(confirmed_fingerprint,str)
                or not secrets.compare_digest(confirmed_fingerprint,review.fingerprint())):
            raise ValueError('Confirm the inspected website and disposable test-account permission.')
        return self._admit_review(actor,review)

    def get(self,actor,project_id,job_id):
        with self.projects._connection() as connection:return self._public(self._owned(connection,actor,project_id,job_id))

    def list(self,actor,project_id):
        self.projects.get(actor,project_id)
        with self.projects._connection() as connection:
            rows=connection.execute('SELECT j.* FROM dashboard_interactive_jobs j '
                'JOIN dashboard_projects p ON p.project_id=j.project_id AND p.owner_id=j.owner_id '
                'WHERE j.project_id=? AND j.owner_id=? ORDER BY sequence DESC LIMIT 20',
                (project_id,actor.user_id)).fetchall()
            return tuple(self._public(row) for row in rows)

    def cancel(self,actor,project_id,job_id):
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=self._owned(connection,actor,project_id,job_id)
            status={'queued':'cancelled','running':'cancel_requested'}.get(row['status'],row['status'])
            connection.execute('UPDATE dashboard_interactive_jobs SET status=? WHERE job_id=?',(status,job_id))
            return self._public(self._owned(connection,actor,project_id,job_id))

    def claim_next(self, *, job_id=None):
        if job_id is not None:_id(job_id)
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=connection.execute("SELECT * FROM dashboard_interactive_jobs WHERE status='queued'"+
                (' AND job_id=?' if job_id is not None else '')+' ORDER BY sequence LIMIT 1',
                (job_id,) if job_id is not None else ()).fetchone()
            if row is None:return None
            if hasattr(self.projects,'admit_execution'):
                try:self.projects.admit_execution(connection,starting=True)
                except LicenseError:return None
            try:review=self._current(connection,row)
            except (ValueError,TypeError,KeyError,LookupError):
                connection.execute("UPDATE dashboard_interactive_jobs SET status='error',claim_token=NULL WHERE job_id=?",(row['job_id'],))
                return None
            token=secrets.token_urlsafe(32)
            connection.execute("UPDATE dashboard_interactive_jobs SET status='running',claim_token=? WHERE job_id=?",(token,row['job_id']))
            return InteractiveWork(row['job_id'],row['owner_id'],row['project_id'],review,token)

    def _claimed(self,connection,work):
        if not isinstance(work,InteractiveWork):raise ValueError('A typed interactive claim is required.')
        row=connection.execute('SELECT * FROM dashboard_interactive_jobs WHERE job_id=? AND owner_id=? AND project_id=?',
            (work.job_id,work.owner_id,work.project_id)).fetchone()
        if (row is None or row['status'] not in ('running','cancel_requested')
                or not secrets.compare_digest(row['claim_token'] or '',work.claim_token)
                or json.loads(row['review_json'])!=_snapshot(work.review)):
            raise ValueError('Invalid or finalized interactive claim.')
        return row

    def cancellation_requested(self,work):
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=self._claimed(connection,work)
            stop=row['status']=='cancel_requested'
            if hasattr(self.projects,'execution_allowed') and not self.projects.execution_allowed():stop=True
            try:self._current(connection,row)
            except (ValueError,TypeError,KeyError,LookupError):stop=True
            if stop:connection.execute("UPDATE dashboard_interactive_jobs SET status='cancel_requested' WHERE job_id=?",(work.job_id,))
            return stop

    def finish(self,work,result):
        if not isinstance(result,InteractiveProbeResult):raise ValueError('A typed interactive outcome is required.')
        with self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=self._claimed(connection,work)
            status='cancelled' if row['status']=='cancel_requested' or result.status.value=='cancelled' else 'completed'
            try:self._current(connection,row)
            except (ValueError,TypeError,KeyError,LookupError):status='error'
            if hasattr(self.projects,'execution_allowed') and not self.projects.execution_allowed():status='cancelled'
            # Never persist adapter text, references, bodies, screenshots or uncertain success.
            outcome='cancelled' if status=='cancelled' else 'error' if status=='error' else result.status.value
            payload=dict(status=outcome,attempted_submissions=result.attempted_submissions)
            from adaptive_qa.website_login import SavedWebsiteLoginReview
            if isinstance(work.review,SavedWebsiteLoginReview):
                from adaptive_qa.website_login_process import WebsiteLoginResult, validate_result
                if isinstance(result,WebsiteLoginResult) and outcome==result.status.value:
                    payload['cases']=validate_result(dict(cases=list(result.cases),attempted_submissions=result.attempted_submissions))['cases']
            from adaptive_qa.demo_login_review import SavedDemoLoginReview
            if isinstance(work.review,SavedDemoLoginReview) and outcome=='error':
                from adaptive_qa.demo_login_outcome import diagnostic_from_message
                code=diagnostic_from_message(result.message)
                if code is not None:payload['diagnostic_code']=code
            connection.execute('UPDATE dashboard_interactive_jobs SET status=?,result_json=?,claim_token=NULL WHERE job_id=?',
                (status,json.dumps(payload),work.job_id))
            return status

    def recover_interrupted(self):
        with worker_lock(self.projects.database),self.projects._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            cancelled=connection.execute("UPDATE dashboard_interactive_jobs SET status='cancelled',claim_token=NULL WHERE status='cancel_requested'").rowcount
            failed=connection.execute("UPDATE dashboard_interactive_jobs SET status='error',claim_token=NULL WHERE status='running'").rowcount
            return dict(cancelled=cancelled,error=failed)


def process_owned_interactive_once(queue):
    """Trusted operator worker; no HTTP activation, screenshots or automatic retries."""
    from adaptive_qa.interactive_process import run_isolated_interactive_probe
    from adaptive_qa.models import TestStatus
    with worker_lock(queue.projects.database):
        work=queue.claim_next()
        if work is None:return None
        review=work.review
        try:
            from adaptive_qa.demo_login_review import SavedDemoLoginReview
            if isinstance(review,SavedDemoLoginReview):
                from adaptive_qa.demo_login_process import run_isolated_demo_login
                result=run_isolated_demo_login(review.plan,timeout_seconds=45,
                    should_cancel=lambda:queue.cancellation_requested(work))
                status=queue.finish(work,result)
                return dict(job_id=work.job_id,project_id=work.project_id,status=status)
            from adaptive_qa.local_form_binding import LocalFormBinding
            from adaptive_qa.public_form_proposal import PublicFormProposal
            from adaptive_qa.interactive_process import run_isolated_local_form
            options=dict(current_fingerprint=review.submission.form.configuration_fingerprint,
                timeout_seconds=45,mappings=review.mappings,should_cancel=lambda:queue.cancellation_requested(work))
            if isinstance(review.submission,PublicFormProposal):
                from adaptive_qa.public_browser_process import run_isolated_public_browser
                from adaptive_qa.public_submission import ReviewedPublicForm
                result=run_isolated_public_browser(ReviewedPublicForm(review.submission,review.submission.fingerprint()),
                    review.configuration,owner_id=work.owner_id,**options)
            elif isinstance(review.submission,LocalFormBinding):
                result=run_isolated_local_form(review.submission,review.configuration,**options)
            else:
                result=run_isolated_interactive_probe(review.submission.form,review.configuration,
                    fixture_id=review.fixture_id,fixture_source='owned_submission',**options)
        except Exception:
            result=InteractiveProbeResult(TestStatus.ERROR,'Controlled form probe could not complete.',None)
        status=queue.finish(work,result)
        return dict(job_id=work.job_id,project_id=work.project_id,status=status)
