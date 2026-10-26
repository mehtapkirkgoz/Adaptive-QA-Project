"""Owned local browser proof for integrated imported reports; no target execution."""
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time

site=os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if site:sys.path.insert(0,str(Path(site).resolve(strict=True)))
import adaptive_qa
if site:assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(site).resolve())
from adaptive_qa.browser_reviews import BrowserReviews
from adaptive_qa.local_free import LocalFreeProjects, LOCAL_ACTOR, create_free_app
from playwright.sync_api import sync_playwright,expect
import uvicorn


def main():
    origin='http://127.0.0.1:8896';artifacts=Path('artifacts/unified-reports');artifacts.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='adaptive-review-ui-') as temp:
        path=Path(temp)/'projects.sqlite';projects=LocalFreeProjects(path)
        pid=projects.create(LOCAL_ACTOR,'Preserved local project').project_id
        before=projects.configuration(LOCAL_ACTOR,pid)
        reviews=BrowserReviews(projects)
        checks=[dict(id='PASS',name='Visible content',status='passed',evidence='Content rendered.'),
                dict(id='FAIL',name='Associated labels',status='failed',evidence='<img src="https://canary.invalid/private"> is displayed as text.'),
                dict(id='BLOCK',name='TLS access',status='blocked',evidence='Certificate verification stopped access.'),
                dict(id='SKIP',name='Backend contract',status='not_run',evidence='No backend contract supplied.')]
        for name in ('First review','Second review'):
            reviews.import_review(LOCAL_ACTOR,pid,dict(name=name,target='https://example.test/',period='Owned fixture',checks=checks,notes=['Browser-only observations.']))
        app=create_free_app(path,port=8896,ui_directory=os.environ.get('ADAPTIVE_QA_VERIFY_UI','frontend/dist'))
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8896,log_level='critical',access_log=False))
        thread=Thread(target=server.run,daemon=True);thread.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:
                assert time.monotonic()<deadline;time.sleep(.05)
            with sync_playwright() as pw:
                browser=pw.chromium.launch();page=browser.new_page(viewport=dict(width=1280,height=900))
                external=[];mutations=[];errors=[]
                page.on('request',lambda r: external.append(r.url) if not r.url.startswith(origin+'/') else mutations.append(r.method) if r.method!='GET' else None)
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(origin+'/#reports');panel=page.get_by_role('region',name='Saved browser reviews')
                expect(panel.get_by_role('heading',name='Browser reviews',exact=True)).to_be_visible()
                expect(panel.get_by_role('heading',name='Second review',exact=True)).to_be_visible()
                panel.get_by_label('Choose a report',exact=False).select_option(label='First review · Owned fixture')
                expect(panel.get_by_role('heading',name='First review',exact=True)).to_be_visible()
                panel.get_by_label('Show checks',exact=True).select_option('failed')
                expect(panel.get_by_text('Associated labels',exact=True)).to_be_visible()
                expect(panel.get_by_text('Visible content',exact=True)).to_have_count(0)
                expect(panel.get_by_text('<img src="https://canary.invalid/private"> is displayed as text.',exact=True)).to_be_visible()
                assert panel.locator('img').count()==0
                panel.get_by_text('Scope and review notes',exact=True).click()
                expect(panel.get_by_text('Browser-only observations.',exact=True)).to_be_visible()
                panel.screenshot(path=str(artifacts/'desktop.png'))
                page.reload();expect(panel.get_by_role('heading',name='Second review',exact=True)).to_be_visible()
                page.set_viewport_size(dict(width=390,height=844));panel.scroll_into_view_if_needed()
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
                panel.screenshot(path=str(artifacts/'mobile.png'))
                assert not external and not mutations and not errors,(external,mutations,errors)
                assert projects.configuration(LOCAL_ACTOR,pid)==before and len(reviews.list(LOCAL_ACTOR))==2
                browser.close()
            result=dict(installed_wheel=bool(site),same_workspace=True,imported_browser_provenance_visible=True,
                        selection_and_filter=True,escaped_evidence=True,reload_no_replay=True,prior_configuration_preserved=True,
                        external_requests=0,mutation_requests=0,page_errors=0,mobile_overflow=False)
            (artifacts/('installed.json' if site else 'source.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(result))
        finally:server.should_exit=True;thread.join(10)

if __name__=='__main__':main()
