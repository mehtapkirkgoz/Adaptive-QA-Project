"""Configured document execution on owned contrasting fixtures only."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from adaptive_qa.config import ProjectConfig
from adaptive_qa.document_process import run_isolated_document_test
from adaptive_qa.document_checks import DOCUMENT_CHECKS
from adaptive_qa.dashboard_evidence import validate_png


def main():
    good = '<html lang="en"><title>Independent information</title><h1 id="main">Information</h1><a href="#main">Read</a></html>'
    pages = {'/information.html': good, '/shop.html': good.replace('Information', 'Store'),
             '/blocked.html': good+'<script src="http://127.0.0.1:8001/forbidden.js"></script>'}
    defects = {'DOC-001': good.replace('<title>Independent information</title>', '<title> </title>'),
               'DOC-002': good.replace('lang="en"', ''),
               'DOC-003': good+'<p id="main">Duplicate</p>',
               'DOC-004': good+'<p aria-describedby="missing">Text</p>',
               'DOC-005': good+'<a href="#missing">Broken</a>'}
    pages.update({'/negative-'+case+'.html': html for case, html in defects.items()})
    contacts = {'canary': 0, 'writes': 0}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            contacts['writes'] += 1
            self.send_response(405); self.end_headers()
        def do_GET(self):
            if self.server.server_port == 8001:
                contacts['canary'] += 1
                self.send_response(404); self.end_headers(); return
            if self.path == '/redirect.html':
                self.send_response(302); self.send_header('Location', '/information.html'); self.end_headers(); return
            html = pages.get(self.path)
            body = (html or 'Not found').encode()
            self.send_response(200 if html else 404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
    servers, threads, outcomes = [], [], []
    try:
        for port in (8000,8001):
            server=ThreadingHTTPServer(('127.0.0.1',port),Handler); servers.append(server)
            thread=Thread(target=server.serve_forever,daemon=True); thread.start(); threads.append(thread)
        with TemporaryDirectory(prefix='adaptive-configured-document-') as temporary:
            def run(case,path,expected):
                project=ProjectConfig('document','Document','http://127.0.0.1:8000'+path,('127.0.0.1',))
                result=run_isolated_document_test(case,project,profile='controlled_local',evidence_directory=temporary)
                assert result.status.value==expected,(case,path,result.status.value)
                assert len(result.evidence_paths)==1
                validate_png(Path(result.evidence_paths[0]).read_bytes())
                outcomes.append({'case_id':case,'status':expected,'fixture':path})
            for path in ('/information.html','/shop.html'):
                for case in DOCUMENT_CHECKS: run(case,path,'passed')
            for case in defects: run(case,'/negative-'+case+'.html','failed')
            run('DOC-001','/redirect.html','error')
            run('DOC-001','/blocked.html','error')
        assert contacts=={'canary':0,'writes':0}
    finally:
        for server in servers: server.shutdown();server.server_close()
        for thread in threads: thread.join(timeout=5)
    output=Path('artifacts/matching');output.mkdir(parents=True,exist_ok=True)
    report={'outcomes':outcomes,'contacts':contacts,'public_https_tested':False,'dashboard_activation':False}
    (output/'configured-document.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'checks':len(outcomes),'contacts':contacts}))

if __name__=='__main__': main()
