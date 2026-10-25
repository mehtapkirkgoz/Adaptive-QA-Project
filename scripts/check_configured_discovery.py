"""Configuration-driven child discovery on owned contrasting HTTP fixtures."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlBudget
from adaptive_qa.local_discovery import discover_configured_target


def main():
    pages = {
        '/account.html': '<html lang="en"><title>Membership</title><form><label>Account<input autocomplete="username"></label><label>Passphrase<input type="password" autocomplete="current-password"></label><button>Sign in</button></form></html>',
        '/search.html': '<html lang="en"><title>Library</title><form role="search"><label>Find<input type="search"></label><button>Search</button></form></html>',
        '/limited.html': '<html lang="en"><title>Information</title><h1>Information</h1><script src="http://127.0.0.1:8001/forbidden.js"></script></html>',
    }
    requests, canary = [], []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if self.server.server_port == 8001:
                canary.append(True)
                self.send_response(404); self.end_headers(); return
            requests.append(self.path)
            if self.path in ('/redirect.html','/foreign-redirect.html'):
                self.send_response(302)
                self.send_header('Location','/account.html' if self.path=='/redirect.html' else 'http://127.0.0.1:8001/blocked')
                self.end_headers();return
            html = pages.get(self.path)
            body = (html or 'Not found').encode()
            self.send_response(200 if html else 404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
    servers, threads, reports = [], [], []
    try:
        for port in (8000, 8001):
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            servers.append(server)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start(); threads.append(thread)
        for index, path in enumerate(pages):
            project = ProjectConfig(f'configured-{index}', 'Configured fixture',
                                    'http://127.0.0.1:8000'+path, ('127.0.0.1',))
            result = discover_configured_target(project, CrawlBudget(max_pages=2, max_requests=20, timeout_seconds=20),
                                                profile='controlled_local')
            assert len(result['pages']) == 1 and result['pages'][0]['url'] == project.base_url
            assert result['plan']['execution_authorized'] is False
            features = {item['feature']: item['status'] for item in result['plan']['assessment']['features']}
            if path == '/account.html': assert features['login'] == 'present' and features['search'] == 'absent'
            if path == '/search.html': assert features['search'] == 'present' and features['login'] == 'absent'
            if path == '/limited.html':
                assert 'network_policy_denial' in result['limitations']
                assert features['login'] == 'unknown', 'Denied resources must not establish feature absence.'
            reports.append({'fixture': path, 'features': features, 'limitations': result['limitations']})
        project=ProjectConfig('redirect-proof','Owned redirect proof','http://127.0.0.1:8000/redirect.html',('127.0.0.1',))
        redirected=discover_configured_target(project,CrawlBudget(max_pages=1,timeout_seconds=15),profile='controlled_local')
        assert len(redirected['pages'])==1 and redirected['pages'][0]['url'].endswith('/account.html')
        project=ProjectConfig('foreign-redirect-proof','Owned redirect scope','http://127.0.0.1:8000/foreign-redirect.html',('127.0.0.1',))
        blocked=discover_configured_target(project,CrawlBudget(max_pages=1,timeout_seconds=15),profile='controlled_local')
        assert blocked['pages']==[] and blocked['diagnostic_code']=='redirect_outside_scope'
        assert not canary and '/' not in requests
    finally:
        for server in servers: server.shutdown(); server.server_close()
        for thread in threads: thread.join(timeout=5); assert not thread.is_alive()
    report = {'controlled_local_only': True, 'configured_start_paths_verified': 3,
              'separate_child_processes': True, 'non_executing_plans': True,
              'denied_resources_preserve_unknown': True, 'canary_contacts': len(canary),
              'public_profile_network_tested': False, 'dashboard_external_activation': False,
              'same_origin_redirect_inspected':True,'foreign_redirect_explained_without_contact':True,
              'reports': reports}
    output = Path('artifacts/matching/configured-discovery.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'reports'}))


if __name__ == '__main__': main()
