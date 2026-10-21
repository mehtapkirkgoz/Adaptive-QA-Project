"""Stateless loopback-only API fixture; never a production application server."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time
from urllib.parse import parse_qs, urlsplit

from adaptive_qa.api_models import parse_api_json


ITEMS = ({'id': 1, 'name': 'Notebook', 'price': 10}, {'id': 2, 'name': 'Pencil', 'price': 2})


class SampleApiHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _record(self):
        self.server.operations.append((self.command, urlsplit(self.path).path))

    def _respond(self, status, payload, *, raw=False, media='application/json', headers=()):
        body = payload if raw else json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', media)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.close_connection = True
        if self.command != 'HEAD':
            try:
                self.wfile.write(body)
            except OSError:
                pass

    def do_GET(self):
        self._record()
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == '/api/health':
            self._respond(200, {'ready': True})
        elif path == '/api/items':
            self._respond(200, {'items': ITEMS, 'count': len(ITEMS)})
        elif path == '/api/items/1':
            self._respond(200, ITEMS[0])
        elif path.startswith('/api/items/'):
            self._respond(404, {'error': 'item_not_found'})
        elif path == '/api/search':
            query = parse_qs(parsed.query).get('q', [''])[0]
            if not query.strip():
                self._respond(400, {'error': 'query_required'})
            elif len(query) > 64:
                self._respond(422, {'error': 'query_too_long'})
            else:
                matches = [item for item in ITEMS if query.casefold() in item['name'].casefold()]
                self._respond(200, {'items': matches, 'count': len(matches)})
        elif path in ('/api/private', '/api/admin'):
            authorization = self.headers.get('Authorization')
            if authorization is None:
                self._respond(401, {'error': 'authentication_required'})
            elif authorization != 'Bearer ' + self.server.token:
                self._respond(403, {'error': 'invalid_token'})
            elif path == '/api/admin':
                self._respond(403, {'error': 'insufficient_scope'})
            else:
                self._respond(200, {'authenticated': True})
        elif path == '/api/echo':
            self._respond(405, {'error': 'method_not_allowed'})
        elif path == '/api/redirect':
            self._respond(307, {}, headers=(('Location', self.server.redirect_target),))
        elif path == '/api/reflect':
            self._respond(200, {'value': self.headers.get('Authorization', '')},
                          headers=(('X-Debug-Token', self.server.token),))
        elif path == '/api/oversized':
            self._respond(200, {'value': 'x' * 70000})
        elif path == '/api/malformed':
            self._respond(200, b'{"value":broken}', raw=True)
        elif path == '/api/duplicate':
            self._respond(200, b'{"value":1,"value":2}', raw=True)
        elif path == '/api/overflow':
            self._respond(200, b'{"value":1e400}', raw=True)
        elif path == '/api/text':
            self._respond(200, b'not JSON', raw=True, media='text/plain')
        elif path == '/api/encoded':
            self._respond(200, b'not compressed', raw=True, headers=(('Content-Encoding', 'gzip'),))
        elif path == '/api/slow-headers':
            try:
                self.wfile.write(b'HTTP/1.1 200 OK\r\nX-Slow: ')
                self.wfile.flush()
                for _ in range(100):
                    self.wfile.write(b'x')
                    self.wfile.flush()
                    time.sleep(0.05)
                self.wfile.write(b'\r\nContent-Length: 2\r\n\r\n{}')
            except OSError:
                pass
            self.close_connection = True
        else:
            self._respond(404, {'error': 'not_found'})

    do_HEAD = do_GET

    def do_POST(self):
        self._record()
        lengths = self.headers.get_all('Content-Length', [])
        if self.headers.get('Transfer-Encoding') or len(lengths) != 1:
            self._respond(400, {'error': 'invalid_length'})
            return
        try:
            length = int(lengths[0])
            if not 0 <= length <= 65536:
                self._respond(413, {'error': 'payload_too_large'})
                return
            payload = parse_api_json(self.rfile.read(length).decode('utf-8'))
        except (ValueError, UnicodeError, RecursionError):
            self._respond(400, {'error': 'invalid_json'})
            return
        if not isinstance(payload, dict):
            self._respond(422, {'error': 'invalid_object'})
        elif self.path == '/api/echo':
            name = payload.get('name')
            if not isinstance(name, str) or not 1 <= len(name) <= 20:
                self._respond(422, {'error': 'invalid_name'})
            else:
                self._respond(201, {'name': name, 'accepted': True})
        elif self.path == '/api/quantity':
            quantity = payload.get('quantity')
            if type(quantity) is not int or not 1 <= quantity <= 10:
                self._respond(422, {'error': 'invalid_quantity'})
            else:
                self._respond(200, {'total': quantity * 10})
        else:
            self._respond(405, {'error': 'method_not_allowed'})


def create_sample_api(token: str, *, redirect_target='http://127.0.0.1:8001/forbidden'):
    if not isinstance(token, str) or not token or not token.isascii() or any(ord(c) <= 32 for c in token):
        raise ValueError('A generated ASCII fixture token is required.')
    server = ThreadingHTTPServer(('127.0.0.1', 8000), SampleApiHandler)
    server.token = token
    server.redirect_target = redirect_target
    server.operations = []
    return server
