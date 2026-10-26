"""Detached number probes on contrasting owned documents; zero page events/writes."""
import json,os,sys,subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import BaseHTTPRequestHandler
from check_owned_submission import server

INSTALLED=os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if INSTALLED:sys.path.insert(0,str(Path(INSTALLED).resolve(strict=True)))
import adaptive_qa
if INSTALLED:
    assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(INSTALLED).resolve())
    child=subprocess.check_output([sys.executable,'-c','import adaptive_qa;print(adaptive_qa.__file__)'],text=True).strip()
    assert Path(child).resolve().is_relative_to(Path(INSTALLED).resolve())
from adaptive_qa.config import ProjectConfig
from adaptive_qa.document_process import run_isolated_form_test
from adaptive_qa.models import TestStatus
from adaptive_qa.native_form_checks import check_number_bound
from adaptive_qa.page_collector import collect_page_snapshot
from playwright.sync_api import sync_playwright


def main():
    contacts=[];writes=[]
    fields={
        '/stock':'<input type="number" min="2" max="20" value="7">',
        '/balance':'<input type="number" min="-3.5" max="2.75" step="0.25" value="1.25">',
        '/min':'<input type="number" min="10">',
        '/max':'<input type="number" max="-1">',
        '/ambiguous':'<input type="number" min="1" max="9"><input type="number" min="1" max="9">',
        '/disabled':'<input type="number" min="1" max="9" disabled>',
        '/readonly':'<input type="number" min="1" max="9" readonly>',
        '/hidden':'<input type="number" min="1" max="9" hidden>',
        '/invalid':'<input type="number" min="wrong" max="Infinity">',
        '/unbounded':'<input type="number" min="-1e99" max="1e99">',
        '/none':'<input type="number">'}
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):writes.append(self.path);self.send_error(405)
        def do_GET(self):
            contacts.append(self.path)
            if self.path=='/redirect':
                self.send_response(302);self.send_header('Location','http://127.0.0.1:1/forbidden');self.end_headers();return
            if self.path not in fields:self.send_error(404);return
            control=fields[self.path].replace('<input ','<input oninput="fetch(\'/mutation\',{method:\'POST\'})" ')
            raw=('<html lang="en"><title>Owned number</title><script src="/script.js"></script>'
                 '<script>fetch("/mutation",{method:"POST"})</script><form method="post" action="/mutation">'
                 '<label>Amount '+control+'</label><button>Submit</button></form></html>').encode()
            self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(raw)
    records=[]
    with TemporaryDirectory(prefix='native-number-') as temporary,server(Fixture,8000):
        for path in fields:
            for case in ('FORM-008','FORM-009'):
                expected=(TestStatus.PASSED if path in ('/stock','/balance') or
                    (path=='/min' and case=='FORM-008') or (path=='/max' and case=='FORM-009') else TestStatus.BLOCKED)
                project=ProjectConfig('native-number','Owned number proof','http://127.0.0.1:8000'+path,('127.0.0.1',))
                result=run_isolated_form_test(case,project,profile='controlled_local',evidence_directory=Path(temporary))
                assert result.status==expected,(path,case,result.status,result.message)
                records.append(dict(path=path,case_id=case,status=result.status.value))
        project=ProjectConfig('native-number','Owned redirect','http://127.0.0.1:8000/redirect',('127.0.0.1',))
        assert run_isolated_form_test('FORM-008',project,profile='controlled_local',evidence_directory=Path(temporary)).status==TestStatus.ERROR
        with sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                page=browser.new_page(java_script_enabled=False)
                page.route('**/*',lambda route:route.continue_() if route.request.resource_type=='document' else route.abort())
                page.goto('http://127.0.0.1:8000/stock')
                snapshot=collect_page_snapshot(page);field=snapshot.forms[0].fields[0]
                assert field.native_minimum and field.native_maximum
                page.evaluate('''() => { const el=document.querySelector('input');window.events=0;
                    el.addEventListener('input',()=>window.events++);el.addEventListener('change',()=>window.events++);
                    Object.defineProperty(el,'value',{get(){throw new Error('live-value-read')},configurable:true}); }''')
                check_number_bound(page,minimum=True);check_number_bound(page,minimum=False)
                assert page.evaluate('window.events')==0
                assert page.locator('input').evaluate("el => el.valueAsNumber")==7
            finally:browser.close()
        assert not writes and '/mutation' not in contacts and '/script.js' not in contacts
    report=dict(scenarios=records,passed=sum(r['status']=='passed' for r in records),
        blocked=sum(r['status']=='blocked' for r in records),redirect_rejected=True,
        page_events=0,submissions=0,live_value_preserved=True,live_value_getter_not_read=True,
        constraints_from_site=True,unique_field_required=True,discovery_booleans_verified=True,
        installed_wheel=bool(INSTALLED),supervised_child_package_verified=bool(INSTALLED),
        owned_fixtures_only=True,customer_targets_contacted=False)
    output=Path('artifacts/native-numbers');output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='scenarios'}))


if __name__=='__main__':main()
