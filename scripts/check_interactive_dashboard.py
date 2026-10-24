"""Built local UI review/confirmation/history without any target submission."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic,sleep

import uvicorn
from playwright.sync_api import sync_playwright,expect
from adaptive_qa.local_free import LocalFreeProjects,LOCAL_ACTOR,create_free_app
from adaptive_qa.project_settings import reference_name
from adaptive_qa.interactive_queue import OwnedInteractiveQueue
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.models import TestStatus


def main():
    port=8893;origin=f'http://127.0.0.1:{port}'
    output=Path('artifacts/dashboard');output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='interactive-dashboard-') as temporary:
        database=Path(temporary)/'projects.sqlite'
        projects=LocalFreeProjects(database);project=projects.create(LOCAL_ACTOR,'Owned interactive controls')
        settings=dict(base_url='http://127.0.0.1:8000/interactive/login-transition',allowed_hosts=['127.0.0.1'],
            allow_data_changes=True,secret_references={slot:reference_name(LOCAL_ACTOR.user_id,project.project_id,slot)
                for slot in ('login_username','login_password')})
        projects.save_configuration(LOCAL_ACTOR,project.project_id,settings)
        queue=OwnedInteractiveQueue(projects)
        app=create_free_app(database,port=port,ui_directory=Path('frontend/dist'))
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='critical',access_log=False,proxy_headers=False))
        thread=Thread(target=server.run,daemon=True);thread.start()
        errors=[];external=[]
        try:
            deadline=monotonic()+10
            while not server.started:
                if not thread.is_alive() or monotonic()>=deadline:raise RuntimeError('Owned UI failed to start.')
                sleep(.05)
            with sync_playwright() as p:
                browser=p.chromium.launch()
                try:
                    page=browser.new_page(viewport=dict(width=1440,height=1100));page.set_default_timeout(10000)
                    page.on('pageerror',lambda error:errors.append(type(error).__name__))
                    def route(request):
                        if request.request.url.startswith(origin+'/'):request.continue_()
                        else:external.append('denied');request.abort()
                    page.route('**/*',route)
                    page.goto(origin+'/',timeout=10000)
                    page.get_by_role('button',name='Owned interactive controls').click()
                    panel=page.get_by_role('region',name='Controlled interactive forms')
                    expect(panel).to_be_visible()
                    panel.get_by_role('button',name='Review interactive submission',exact=True).click()
                    confirmation=panel.get_by_label('Interactive review confirmation')
                    expect(confirmation).to_be_visible()
                    authorize=panel.get_by_role('checkbox',name='I authorize this one submission on my owned local fixture.')
                    authorize.check()
                    panel.get_by_label('Completion test ID',exact=True).fill('changed-marker')
                    expect(confirmation).to_have_count(0)
                    panel.get_by_label('Completion test ID',exact=True).fill('result')
                    panel.get_by_role('button',name='Review interactive submission',exact=True).click()
                    expect(confirmation).to_be_visible();authorize.check()
                    panel.screenshot(path=str(output/'interactive-operator.png'))
                    panel.get_by_role('button',name='Queue one interactive submission',exact=True).click()
                    expect(confirmation).to_have_count(0)
                    cancel=panel.get_by_role('button',name='Cancel interactive job',exact=True)
                    expect(cancel).to_be_visible();cancel.click()
                    expect(panel.get_by_text('cancelled',exact=True)).to_be_visible()
                    assert queue.list(LOCAL_ACTOR,project.project_id)[0]['status']=='cancelled'
                    # Synthetic unknown worker outcome checks UI wording, not target behavior.
                    panel.get_by_role('button',name='Review interactive submission',exact=True).click()
                    expect(confirmation).to_be_visible();authorize.check()
                    panel.get_by_role('button',name='Queue one interactive submission',exact=True).click()
                    expect(cancel).to_be_visible()
                    work=queue.claim_next();assert work is not None
                    queue.finish(work,InteractiveProbeResult(TestStatus.ERROR,'sanitized synthetic outcome',None))
                    expect(panel.get_by_text('Result: error; submissions: unknown',exact=True)).to_be_visible(timeout=10000)
                    page.set_viewport_size(dict(width=390,height=900))
                    panel.scroll_into_view_if_needed();panel.screenshot(path=str(output/'interactive-operator-mobile.png'))
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'
                    reusable=dict(operation='login',document_url='http://127.0.0.1:8000/portal/access',endpoint_url='http://127.0.0.1:8000/auth/check',
                        field_names=['identity','accessCode'],accepted=dict(status_code=201,field_name='sessionReady',expected_value=True),
                        rejected=dict(status_code=403,field_name='sessionReady',expected_value=False))
                    projects.save_configuration(LOCAL_ACTOR,project.project_id,dict(settings,base_url=reusable['document_url'],local_form_binding=reusable))
                    page.reload();page.get_by_role('button',name='Owned interactive controls').click()
                    expect(page.get_by_role('heading',name='Project settings',exact=True)).to_be_visible()
                    expect(panel).to_have_count(0)
                    page.get_by_role('button',name='Save configuration',exact=True).click()
                    expect(page.get_by_text('Configuration saved. No tests were started.',exact=True)).to_be_visible()
                    assert projects.configuration(LOCAL_ACTOR,project.project_id)['local_form_binding']==reusable
                    assert not errors and not external
                    assert not database.with_name('auth.sqlite').exists()
                    assert b'sanitized synthetic outcome' not in database.read_bytes()
                finally:browser.close()
        finally:
            server.should_exit=True;thread.join(timeout=10)
            assert not thread.is_alive(),'Owned UI did not stop'
    report=dict(review_does_not_execute=True,confirmation_cleared_on_edit=True,confirmation_cleared_on_admission=True,
        queued_cancellation=True,synthetic_unknown_outcome_visible=True,external_requests=0,page_errors=0,
        target_submissions=0,mobile_overflow=False,accounts_created=0,saved_reusable_binding_preserved=True)
    (output/'interactive-operator.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
