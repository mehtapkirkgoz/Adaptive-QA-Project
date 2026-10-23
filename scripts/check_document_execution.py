"""Title-independent document rules through guarded real child processes."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from adaptive_qa.browser_process import run_isolated_sample_test
from adaptive_qa.dashboard_evidence import validate_png
from adaptive_qa.document_checks import DOCUMENT_CHECKS


def main():
    pages = {
        '/information.html': '<html lang="en"><title>Community information</title><h1 id="intro">Welcome</h1><a href="#intro">Introduction</a></html>',
        '/commerce.html': '<html lang="en"><title>Independent book shop</title><h1 id="book">A book</h1><article aria-labelledby="book">25 EUR</article><img alt="Cover" src="http://127.0.0.1:8001/forbidden.png"></html>',
        '/account.html': '<html lang="en"><title>Member portal</title><h1 id="member">Account</h1><label for="name">Name</label><input id="name"><script>fetch("/forbidden-write", {method:"POST", body:"must-not-arrive"}).catch(()=>{});</script></html>',
    }
    defects = {
        'DOC-001': '<html lang="en"><title> </title><h1>Content</h1></html>',
        'DOC-002': '<html><title>News</title><h1>Content</h1></html>',
        'DOC-003': '<html lang="en"><title>News</title><p id="same">One</p><p id="same">Two</p></html>',
        'DOC-004': '<html lang="en"><title>News</title><main aria-labelledby="missing">Content</main></html>',
        'DOC-005': '<html lang="en"><title>News</title><a href="#missing">Content</a></html>',
    }
    for case, html in defects.items(): pages[f'/negative-{case}.html'] = html
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
            html = pages.get(self.path)
            body = (html or 'Not found').encode()
            self.send_response(200 if html else 404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
    servers, threads, results = [], [], []
    try:
        for port in (8000, 8001):
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            servers.append(server)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start(); threads.append(thread)
        with TemporaryDirectory(prefix='adaptive-document-execution-') as temporary:
            root = Path(temporary).resolve(strict=True)
            for path in ('/information.html', '/commerce.html', '/account.html'):
                for case in DOCUMENT_CHECKS:
                    result = run_isolated_sample_test(case, document_path=path, evidence_directory=root)
                    assert result.status.value == 'passed', (path, case, result.status.value)
                    assert len(result.evidence_paths) == 1
                    validate_png(Path(result.evidence_paths[0]).read_bytes())
                    results.append({'fixture': path, 'case_id': case, 'status': result.status.value})
            for case in defects:
                result = run_isolated_sample_test(case, document_path=f'/negative-{case}.html', evidence_directory=root)
                assert result.status.value == 'failed', (case, result.status.value)
                assert len(result.evidence_paths) == 1
                validate_png(Path(result.evidence_paths[0]).read_bytes())
                results.append({'fixture': 'negative', 'case_id': case, 'status': result.status.value})
            assert contacts == {'canary': 0, 'writes': 0}
    finally:
        for server in servers: server.shutdown(); server.server_close()
        for thread in threads: thread.join(timeout=5); assert not thread.is_alive()
    report = {'controlled_local_only': True, 'sample_title_required': False, 'unique_cases': 5,
              'positive_executions': 15, 'negative_defects_detected': 5, 'validated_pngs': 20,
              'forbidden_canary_contacts': contacts['canary'], 'write_requests_received': contacts['writes'],
              'public_target_execution_enabled': False, 'results': results}
    output = Path('artifacts/matching/document-execution.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'results'}))


if __name__ == '__main__': main()
