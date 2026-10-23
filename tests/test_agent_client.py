"""Real sockets: response authentication, no redirects/proxies/DNS and hard timeout."""

from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from threading import Thread,Event
from time import monotonic
import unittest
from unittest.mock import patch

from adaptive_qa.agent_registry import message_signature,token_signing_key
from adaptive_qa.agent_transport import AgentClient,AgentTransportError
from adaptive_qa.secrets import SecretValue


class AgentClientTests(unittest.TestCase):
    def server(self,mode):
        token = SecretValue('a'*43)
        key = token_signing_key(token.value)
        observed,release = [],Event()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('content-length','0')))
                observed.append((self.path,dict(self.headers)))
                if mode=='redirect':
                    self.send_response(302); self.send_header('Location','http://127.0.0.1:1/forbidden'); self.end_headers(); return
                response = b'{"work":null}'
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(100 if mode=='stall' else len(response)))
                signature = message_signature(key,self.path,int(self.headers['x-agent-sequence']),response,response=True)
                self.send_header('X-Agent-Response-Signature',signature if mode!='unsigned' else '0'*64)
                self.end_headers()
                if mode=='stall':
                    self.wfile.write(b'{'); self.wfile.flush(); release.wait(10)
                else:
                    self.wfile.write(response)
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        server.daemon_threads = True
        thread = Thread(target=server.serve_forever,daemon=True)
        thread.start()
        def cleanup():
            release.set(); server.shutdown(); server.server_close(); thread.join(timeout=2)
        self.addCleanup(cleanup)
        return AgentClient(f'http://127.0.0.1:{server.server_port}','b'*32,token),observed

    def test_valid_signed_response_ignores_proxy_dns_and_never_sends_raw_token(self):
        client,observed = self.server('valid')
        with patch.dict('os.environ',{'HTTP_PROXY':'http://127.0.0.1:1','ALL_PROXY':'http://127.0.0.1:1'}), \
                patch('socket.getaddrinfo',side_effect=AssertionError('DNS forbidden')), \
                patch('socket.socket.bind',side_effect=AssertionError('Agent listener forbidden')):
            self.assertEqual(client.call('/agent/poll',{}),{'work':None})
        self.assertNotIn('a'*43,str(observed))
        self.assertEqual(len(observed),1)

    def test_redirect_and_invalid_response_signature_fail_without_retry(self):
        for mode in ('redirect','unsigned'):
            client,observed = self.server(mode)
            with self.assertRaises(AgentTransportError):
                client.call('/agent/poll',{})
            self.assertEqual(len(observed),1)

    def test_slow_body_is_interrupted_by_total_socket_deadline(self):
        client,observed = self.server('stall')
        start = monotonic()
        with self.assertRaises(AgentTransportError):
            client.call('/agent/poll',{})
        self.assertLess(monotonic()-start,6.5)
        self.assertEqual(len(observed),1)
