"""Supervised read-only form checks on contrasting owned HTTP fixtures."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from adaptive_qa.config import ProjectConfig
from adaptive_qa.dashboard_evidence import validate_png
from adaptive_qa.document_process import run_isolated_form_test
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy, ProjectElementMappings


def main():
    login = '<form><label>Username<input></label><label>Password<input type="password"></label><button>Sign in</button></form>'
    search = '<form><label>Search products<input type="search"></label><button>Search</button></form>'
    pages = {'/account': login, '/search': search,
        '/turkish': login.replace('Username', 'Kullanıcı adı').replace('Password', 'Şifre').replace('Sign in', 'Giriş yap'),
        '/ambiguous': login+login, '/missing': login.replace('Password', 'Unknown'),
        '/exposed': login.replace('type="password"', 'type="text"'),
        '/disabled': search.replace('<button>', '<button disabled>'),
        '/split': login.replace('<button>', '</form><form><button>'),
        '/blocked': login+'<script src="http://127.0.0.1:8001/forbidden.js"></script>',
        '/write': login+'<script>fetch("/forbidden-write",{method:"POST",body:"must-not-arrive"}).catch(()=>{});</script>',
        '/custom': '<form><input data-testid="login.username"><input data-testid="login.password" type="password"><button data-testid="login.submit">Continue</button></form>'}
    contacts = {'canary': 0, 'writes': 0, 'interactions': 0}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            contacts['writes'] += 1
            self.send_response(405); self.end_headers()
        def do_GET(self):
            if self.server.server_port == 8001:
                contacts['canary'] += 1
                self.send_response(404); self.end_headers(); return
            if self.path == '/interaction':
                contacts['interactions'] += 1
                self.send_response(204); self.end_headers(); return
            if self.path == '/redirect':
                self.send_response(302); self.send_header('Location', '/account'); self.end_headers(); return
            html = pages.get(self.path)
            instrument = '''<script>for(const event of ['input','click','submit'])
                document.addEventListener(event,()=>fetch('/interaction'));</script>'''
            body = ('<html lang="en"><title>Independent form fixture</title>'+ (html or 'Missing')+instrument+'</html>').encode('utf-8')
            self.send_response(200 if html else 404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
    servers, threads, outcomes = [], [], []
    try:
        for port in (8000, 8001):
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            servers.append(server)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start(); threads.append(thread)
        with TemporaryDirectory(prefix='adaptive-configured-forms-') as temporary:
            mappings = ProjectElementMappings('forms', tuple(ElementMapping(key,
                (LocatorSpec(LocatorStrategy.TEST_ID, key),))
                for key in ('login.username', 'login.password', 'login.submit')))
            scenarios = (
                ('LOGIN-001', '/account', 'passed', None), ('LOGIN-001', '/turkish', 'passed', None),
                ('SEARCH-001', '/search', 'passed', None), ('LOGIN-001', '/custom', 'passed', mappings),
                ('LOGIN-001', '/ambiguous', 'blocked', None), ('LOGIN-001', '/missing', 'blocked', None),
                ('LOGIN-001', '/exposed', 'failed', None), ('SEARCH-001', '/disabled', 'failed', None),
                ('LOGIN-001', '/split', 'failed', None), ('LOGIN-001', '/blocked', 'error', None),
                ('LOGIN-001', '/write', 'error', None), ('LOGIN-001', '/redirect', 'error', None),
            )
            for case, path, expected, override in scenarios:
                project = ProjectConfig('forms', 'Owned forms', 'http://127.0.0.1:8000'+path, ('127.0.0.1',))
                result = run_isolated_form_test(case, project, profile='controlled_local',
                    evidence_directory=temporary, mappings=override)
                assert result.status.value == expected, (case, path, result.status.value)
                assert len(result.evidence_paths) == 1
                validate_png(Path(result.evidence_paths[0]).read_bytes())
                outcomes.append({'case_id': case, 'fixture': path, 'status': expected})
        assert contacts == {'canary': 0, 'writes': 0, 'interactions': 0}, contacts
    finally:
        for server in servers:
            server.shutdown(); server.server_close()
        for thread in threads:
            thread.join(timeout=5)
    output = Path('artifacts/matching')
    output.mkdir(parents=True, exist_ok=True)
    report = {'outcomes': outcomes, 'contacts': contacts, 'screenshots_validated': len(outcomes),
              'public_form_activation': False, 'credential_use': False, 'catalog_cases_added': 0}
    (output/'configured-forms.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'scenarios': len(outcomes), 'contacts': contacts}))


if __name__ == '__main__':
    main()
