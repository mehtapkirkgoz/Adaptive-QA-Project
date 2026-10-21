"""Exercise bounded discovery through a real guarded local browser process."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from adaptive_qa.crawler import CrawlBudget
from adaptive_qa.local_discovery import discover_local_sample
from adaptive_qa.catalog import TEST_CASES


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/':
            body = '''<a href="/login">Login</a><a href="/search">Search</a>
                <a href="/login#duplicate">Again</a><a href="/redirect">Redirect</a>
                <a href="http://127.0.0.1:8001/forbidden">Forbidden</a>'''
        elif self.path == '/login':
            body = '''<form><input type="email"><input type="password">
                <button>Sign in</button></form><a href="/">Home</a><a href="/deep">More</a>'''
        elif self.path == '/search':
            body = '<form role="search"><input type="search"><button>Search</button></form>'
        elif self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/search')
            self.end_headers()
            return
        else:
            body = '<h1>Information</h1>'
        payload = body.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 8000), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    reports = {}
    try:
        reports['normal'] = discover_local_sample(CrawlBudget(max_pages=10))
        result = reports['normal']
        assert result['pages'], result
        urls = {page['url'] for page in result['pages']}
        assert len(urls) == len(result['pages']), result
        assert urls == {f'http://127.0.0.1:8000{path}' for path in ('/', '/login', '/search', '/deep')}, result
        assert 'excluded_link' in result['limitations']
        plan = result['plan']
        assert not plan['execution_authorized']
        assert sum(case['decision'] == 'selected' for case in plan['cases']) == len(TEST_CASES)
        for case in plan['cases']:
            if case['decision'] == 'selected':
                path = ('/login' if case['case_id'].startswith(('LOGIN', 'FORM')) else
                        '/search' if case['case_id'].startswith('SEARCH') else '/')
                assert case['target_url'] == 'http://127.0.0.1:8000' + path
                assert case['evidence']
        reports['pages'] = discover_local_sample(CrawlBudget(max_pages=1))
        assert reports['pages']['attempted_pages'] == 1
        assert 'page_limit' in reports['pages']['limitations']
        assert all(case['decision'] == 'blocked' for case in reports['pages']['plan']['cases']
                   if not case['case_id'].startswith('NAV'))
        reports['depth'] = discover_local_sample(CrawlBudget(max_depth=0))
        assert len(reports['depth']['pages']) == 1
        assert 'depth_limit' in reports['depth']['limitations']
        reports['requests'] = discover_local_sample(CrawlBudget(max_requests=1))
        assert 'request_limit' in reports['requests']['limitations']
        reports['time'] = discover_local_sample(CrawlBudget(timeout_seconds=0.01))
        assert reports['time']['limitations'] == ['time_limit']
        assert all(case['decision'] == 'blocked' for case in reports['time']['plan']['cases'])
        directory = Path('artifacts/discovery')
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'report.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
        print('Five guarded discovery scenarios passed.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
