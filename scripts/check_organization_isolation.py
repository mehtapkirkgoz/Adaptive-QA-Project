"""Two disposable tenants: concurrent admission, active limits and real UI work."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from adaptive_qa.project_store import ProjectStore
from adaptive_qa.auth_store import AuthStore
from adaptive_qa.organization_store import OrganizationStore, OrganizationNotFound
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
from adaptive_qa.organization_runs import OrganizationRunQueue
from adaptive_qa.organization_policy import OrganizationQuota, OrganizationRole as Role
from adaptive_qa.organization_admission import OrganizationCapacityExceeded
from adaptive_qa.dashboard_runs import TestRunNotFound
from adaptive_qa.dashboard_worker import process_discovery_once
from adaptive_qa.dashboard_run_worker import process_run_once
from adaptive_qa.dashboard_evidence import validate_png
from check_dashboard_runs import QuietHandler


def main():
    fixture = ThreadingHTTPServer(('127.0.0.1',8000),partial(QuietHandler,directory='samples/web'))
    thread = Thread(target=fixture.serve_forever,daemon=True)
    thread.start()
    try:
        with TemporaryDirectory(prefix='adaptive-two-organizations-') as temporary:
            root = Path(temporary)
            auth = AuthStore(root/'auth.sqlite')
            actors = [auth.create_user(f'{name}@example.test',f'Disposable {name} password 123!') for name in ('alpha','beta','viewer')]
            projects = ProjectStore(root/'projects.sqlite')
            organizations = OrganizationStore(projects)
            scoped = OrganizationProjects(organizations)
            discovery = OrganizationDiscoveryQueue(scoped)
            runs = OrganizationRunQueue(discovery)
            tenants = []
            for actor,name in zip(actors[:2],('Alpha','Beta')):
                organization = organizations.create(actor,name,quota=OrganizationQuota(2,2,1,3))
                project = scoped.create(actor,organization,'Controlled UI fixture')['project_id']
                scoped.save_configuration(actor,organization,project,{'base_url':'http://127.0.0.1:8000/',
                    'allowed_hosts':['127.0.0.1'],'allow_data_changes':False,'secret_references':{}})
                job = discovery.submit(actor,organization,project)['job_id']
                assert process_discovery_once(discovery)['status']=='completed'
                tenants.append((actor,organization,project,job))
            def submit(tenant):
                actor,organization,project,job = tenant
                try:
                    return runs.submit(actor,organization,project,job,('LOGIN-001','SEARCH-001'))
                except OrganizationCapacityExceeded:
                    return None
            with ThreadPoolExecutor(max_workers=8) as pool:
                admitted = list(pool.map(submit,[tenants[i%2] for i in range(16)]))
            assert sum(value is not None for value in admitted)==4
            for actor,organization,project,job in tenants:
                assert runs.admission.usage(actor,organization)['pending_runs']==2
            first,second = runs.claim_next(),runs.claim_next()
            assert first is not None and second is not None and first.owner_id!=second.owner_id
            assert runs.claim_next() is None
            for actor,organization,project,job in tenants:
                snapshot = runs.admission.usage(actor,organization)
                assert snapshot['active_runs']==snapshot['pending_runs']==1
            # Interrupted-claim simulation is explicitly error, never fabricated passes.
            assert runs.finish(first,failed=True)=='error'
            assert runs.finish(second,failed=True)=='error'
            assert process_run_once(runs)['status']=='completed'
            assert process_run_once(runs)['status']=='completed'
            assert process_run_once(runs) is None
            completed = []
            for actor,organization,project,job in tenants:
                history = runs.list(actor,organization,project)
                passed = [run for run in history if run['status']=='completed']
                assert len(passed)==1
                run = passed[0]
                assert len(run['results'])==2 and all(item['status']=='passed' and item.get('evidence_id') for item in run['results'])
                for item in run['results']:
                    validate_png(runs.evidence(actor,organization,project,run['run_id'],item['evidence_id']))
                completed.append(run)
                last = submit((actor,organization,project,job))
                assert last is not None
                runs.cancel(actor,organization,project,last['run_id'])
                assert submit((actor,organization,project,job)) is None
                assert runs.admission.usage(actor,organization)=={
                    'utc_day':runs.admission._day(),'pending_runs':0,'active_runs':0,'daily_admitted_runs':3}
            actor_a,org_a,project_a,_ = tenants[0]
            actor_b,org_b,project_b,_ = tenants[1]
            try:
                runs.get(actor_b,org_a,project_a,completed[0]['run_id'])
            except OrganizationNotFound:
                pass
            else:
                raise AssertionError('Foreign organization became visible.')
            try:
                runs.evidence(actor_b,org_b,project_b,completed[0]['run_id'],completed[0]['results'][0]['evidence_id'])
            except TestRunNotFound:
                pass
            else:
                raise AssertionError('Foreign evidence crossed organization scope.')
            organizations.set_member(actor_a,org_a,actors[2].user_id,Role.VIEWER)
            assert runs.get(actors[2],org_a,project_a,completed[0]['run_id'])['status']=='completed'
            try:
                runs.submit(actors[2],org_a,project_a,tenants[0][3],('LOGIN-001',))
            except OrganizationNotFound:
                pass
            else:
                raise AssertionError('Viewer dispatched execution.')
            organizations.remove_member(actor_a,org_a,actors[2].user_id)
            try:
                runs.get(actors[2],org_a,project_a,completed[0]['run_id'])
            except OrganizationNotFound:
                pass
            else:
                raise AssertionError('Revoked reader retained access.')
    finally:
        fixture.shutdown()
        fixture.server_close()
        thread.join(timeout=5)
    report = {'organizations':2,'concurrent_attempts':16,'admitted_before_claim':4,
              'active_per_organization':1,'interrupted_runs_recorded_as_error':2,
              'real_completed_runs':2,'real_passed_cases':4,'validated_pngs':4,
              'daily_admissions_per_organization':3,'cancel_does_not_refund_daily':True,
              'cross_tenant_results_and_evidence_denied':True,'viewer_dispatch_denied':True,
              'revocation_effective':True,'customer_sites_contacted':False}
    output = Path('artifacts/organizations/isolation.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()
