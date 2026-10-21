"""Raw ASGI checks bypass client/server normalization of malformed headers/bodies."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.web_app import create_app


class WebBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app(AuthStore(Path(self.temp.name) / 'auth.sqlite'))

    async def request(self, messages, headers=(), *, stalled=False):
        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
                 'method': 'POST', 'scheme': 'http', 'path': '/api/auth/login',
                 'raw_path': b'/api/auth/login', 'query_string': b'',
                 'headers': [(b'host', b'127.0.0.1:8765'), (b'origin', b'http://127.0.0.1:8765'),
                             (b'content-type', b'application/json'), *headers],
                 'server': ('127.0.0.1', 8765), 'client': ('127.0.0.1', 1234)}
        sent = []
        async def receive():
            if messages:
                return messages.pop(0)
            if stalled:
                await asyncio.Event().wait()
            return {'type': 'http.disconnect'}
        async def send(message):
            sent.append(message)
        await self.app(scope, receive, send)
        return sent[0]['status'], dict(sent[0]['headers'])

    async def test_chunked_bytes_override_missing_or_false_length(self):
        for headers in ((), ((b'content-length', b'1'),)):
            status, response = await self.request([
                {'type': 'http.request', 'body': b'x' * 1024, 'more_body': True},
                {'type': 'http.request', 'body': b'x' * 1025, 'more_body': False}], headers)
            self.assertEqual(status, 413)
            self.assertEqual(response[b'cache-control'], b'no-store')

    async def test_disconnected_body_fails_closed(self):
        self.assertEqual((await self.request([{'type': 'http.disconnect'}]))[0], 408)

    async def test_stalled_body_has_real_deadline(self):
        start = asyncio.get_running_loop().time()
        status, _ = await self.request([], stalled=True)
        self.assertEqual(status, 408)
        self.assertLess(asyncio.get_running_loop().time() - start, 7)

    async def test_ambiguous_security_headers_and_cookie_names_rejected(self):
        for headers in (((b'origin', b'http://127.0.0.1:8765'),),
                        ((b'x-csrf-token', b'a'), (b'x-csrf-token', b'b')),
                        ((b'cookie', b'adaptive_session=a; adaptive_session=b'),),
                        ((b'content-encoding', b'gzip'),)):
            self.assertEqual((await self.request([], headers))[0], 400)
