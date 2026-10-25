"""Owned real-child proof: HTML structure checks exclude assets without relaxing egress."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

INSTALLED_SITE=os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
if INSTALLED_SITE: sys.path.insert(0,str(Path(INSTALLED_SITE).resolve(strict=True)))
import adaptive_qa
if INSTALLED_SITE: assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(INSTALLED_SITE).resolve())

from adaptive_qa.config import ProjectConfig
from adaptive_qa.document_process import run_isolated_document_test, run_isolated_form_test
from adaptive_qa.models import TestStatus


def main():
    requests, writes = [], []
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self): writes.append(self.path); self.send_error(405)
        def do_GET(self):
            requests.append(self.path)
            if self.path == '/redirect':
                self.send_response(302);self.send_header('Location','http://127.0.0.1:1/private');self.end_headers();return
            broken = self.path == '/broken.html'
            raw = (('<html>' if broken else '<html lang="en">')+'''<head><title>Owned HTML</title>
                <link rel="stylesheet" href="https://asset.example.invalid/style.css">
                <script>document.title='Changed by script';document.documentElement.removeAttribute('lang');fetch('/mutation',{method:'POST'});</script>
                <script src="/script.js"></script></head><body><p id="ok">Owned HTML</p>
                <img src="https://asset.example.invalid/image.png"><iframe src="/embedded"></iframe>
                <form><label>Username<input name="username"></label><label>Password<input type="password"></label><button>Sign in</button></form>
                <a href="#ok">Valid anchor</a>'''+('<p id="ok">Duplicate</p>' if broken else '')+'</body></html>').encode()
            self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    fixture=ThreadingHTTPServer(('127.0.0.1',8000),Fixture);thread=Thread(target=fixture.serve_forever,daemon=True);thread.start()
    outcomes=[]
    try:
        with TemporaryDirectory(prefix='adaptive-html-proof-') as temporary:
            root=Path(temporary)
            def project(path): return ProjectConfig('html-proof','HTML proof','http://127.0.0.1:8000'+path,('127.0.0.1',))
            for case in ('DOC-001','DOC-002','DOC-003','DOC-004','DOC-005'):
                result=run_isolated_document_test(case,project('/valid.html'),profile='controlled_local',evidence_directory=root)
                assert result.status==TestStatus.PASSED,(case,result.status,result.message)
                outcomes.append(result.status.value)
            for case in ('DOC-002','DOC-003'):
                result=run_isolated_document_test(case,project('/broken.html'),profile='controlled_local',evidence_directory=root)
                assert result.status==TestStatus.FAILED,(case,result.status,result.message)
                outcomes.append(result.status.value)
            # Assert denied navigation still fails, rather than granting broader host/port authority.
            result=run_isolated_document_test('DOC-001',project('/redirect'),profile='controlled_local',evidence_directory=root)
            assert result.status==TestStatus.ERROR,(result.status,result.message)
            form=run_isolated_form_test('LOGIN-001',project('/valid.html'),profile='controlled_local',evidence_directory=root)
            assert form.status==TestStatus.ERROR,(form.status,form.message)
            assert not writes and '/mutation' not in requests and '/script.js' not in requests[:7] and '/embedded' not in requests[:7]
            report=dict(installed_wheel=bool(INSTALLED_SITE),source_html_passes=5,source_html_assertion_failures=2,redirect_blocked=True,
                rendered_form_coverage_still_fails_closed=True,scripts_assets_and_frames_excluded=True,
                mutation_requests=0,private_destination_not_contacted=True,scope='owned_controlled_fixture')
            output=Path('artifacts/html-inspection');output.mkdir(parents=True,exist_ok=True)
            (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(report))
    finally: fixture.shutdown();fixture.server_close();thread.join(5)


if __name__=='__main__':main()
