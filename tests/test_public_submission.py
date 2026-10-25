"""Internal HTTPS transport proof on owned TLS sockets, never public endpoints."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import ssl
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from adaptive_qa.config import ProjectConfig
from adaptive_qa.egress import DestinationGuard
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.local_form_binding import LocalBooleanResponse
from adaptive_qa.owned_submission import CONTENT_TYPE, OwnedSubmissionGate
from adaptive_qa.public_form_proposal import PublicFormProposal
from adaptive_qa.public_submission import ReviewedPublicForm, PublicSubmissionGate, PublicSubmissionTransport
from adaptive_qa.secrets import SecretReference


class PublicSubmissionTests(unittest.TestCase):
    def setUp(self):
        form = InteractiveFormContract('a'*32, 'b'*64, FormOperation.SEARCH,
            (SecretReference('OWNED_QUERY'),),
            ElementMapping('search.results', (LocatorSpec(LocatorStrategy.TEST_ID, 'results-ready'),)))
        self.proposal = PublicFormProposal(form, 'https://qa.example.test/search',
            'https://qa.example.test/search/execute', ('query',),
            LocalBooleanResponse(200, 'found', True), LocalBooleanResponse(404, 'found', False))
        self.review = ReviewedPublicForm(self.proposal, self.proposal.fingerprint())
        self.project = ProjectConfig('a'*32, 'Owned TLS proof', self.proposal.document_url,
                                     ('qa.example.test',), True)
        self.request = dict(url=self.proposal.endpoint_url, method='POST', content_type=CONTENT_TYPE,
                            body=b'query=OWNED_INPUT_CANARY')

    def gate(self):
        return PublicSubmissionGate(self.review, self.project, current_fingerprint='b'*64)

    def transport(self):
        return PublicSubmissionTransport(self.review, self.project, current_fingerprint='b'*64)

    def test_confirmation_permission_and_local_type_boundaries_are_offline(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
                patch.object(SecretReference, 'resolve', side_effect=AssertionError('No values')):
            with self.assertRaises(ValueError):
                ReviewedPublicForm(self.proposal, 'c'*64)
            with self.assertRaises(ValueError):
                PublicSubmissionGate(self.proposal, self.project, current_fingerprint='b'*64)
            with self.assertRaises(ValueError):
                PublicSubmissionGate(self.review, replace(self.project, allow_data_changes=False), current_fingerprint='b'*64)
            with self.assertRaises(ValueError):
                PublicSubmissionGate(self.review, self.project, current_fingerprint='c'*64)
            with self.assertRaises(ValueError):
                OwnedSubmissionGate(self.review, self.project, current_fingerprint='b'*64)
            self.assertTrue(self.gate().admit(**self.request))
            self.assertFalse(self.proposal.execution_authorized)

    def test_invalid_attempt_is_consumed_and_inputs_are_exactly_bounded(self):
        changes = ({'url':'https://other.example.test/search/execute'}, {'method':'GET'},
            {'content_type':'application/json'}, {'body':'query=value'}, {'body':b''},
            {'body':b'x'*8193}, {'body':b'query='}, {'body':b'password=value'},
            {'body':b'query=one&query=two'}, {'body':b'query=value&extra=field'},
            {'body':b'query=%FF'}, {'body':b'query=%0A'}, {'body':b'query=%ZZ'},
            {'body':b'query='+b'x'*513})
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')):
            for change in changes:
                gate = self.gate()
                self.assertFalse(gate.admit(**{**self.request, **change}), change)
                self.assertFalse(gate.admit(**self.request))
            self.assertTrue(self.gate().admit(**{**self.request, 'body':b'query=%C3%BCr%C3%BCn'}))

    def test_concurrent_attempts_admit_exactly_once(self):
        gate = self.gate()
        with ThreadPoolExecutor(max_workers=8) as pool:
            admitted = list(pool.map(lambda _:gate.admit(**self.request), range(32)))
        self.assertEqual(sum(admitted), 1)

    def test_rejected_transport_request_never_resolves_or_connects(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
                patch.object(DestinationGuard, 'authorize') as authorize, \
                patch.object(DestinationGuard, 'connect') as connect:
            transport = self.transport()
            result = transport.submit(**{**self.request, 'body': b'wrong=value'})
            self.assertEqual((result.outcome, result.attempted_submissions), ('blocked', 0))
            self.assertEqual(transport.submit(**self.request).outcome, 'blocked')
            authorize.assert_not_called(); connect.assert_not_called()

    def tls_harness(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name); key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'qa.example.test')])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
            .not_valid_after(now+timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('qa.example.test')]),False)
            .add_extension(x509.BasicConstraints(ca=True,path_length=None),True).sign(key,hashes.SHA256()))
        cert_path, key_path = root/'ca.pem', root/'key.pem'
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()))
        state = dict(contacts=[], status=200, body=b'{"found":true}', headers={}, drop=False)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                state['contacts'].append(dict(path=self.path, body=body, host=self.headers.get('Host'),
                    cookie=self.headers.get('Cookie'), authorization=self.headers.get('Authorization')))
                if state['drop']:
                    self.close_connection=True
                    return
                self.send_response(state['status'])
                self.send_header('Content-Type','application/json')
                for key,value in state['headers'].items(): self.send_header(key,value)
                self.end_headers()
                try:self.wfile.write(state['body'])
                except OSError:pass
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cert_path,key_path)
        server.socket = context.wrap_socket(server.socket,server_side=True)
        thread = Thread(target=server.serve_forever,daemon=True); thread.start()
        def close():server.shutdown();server.server_close();thread.join(timeout=5)
        self.addCleanup(close)
        trusted = ssl.create_default_context(cafile=str(cert_path))
        def owned_connect(guard,target,**kwargs):
            self.assertFalse(guard.local_sample)
            self.assertEqual(target.port,443)
            self.assertEqual(target.addresses,('93.184.216.34',))
            return socket.create_connection(('127.0.0.1',server.server_port),timeout=2)
        return trusted,owned_connect,state

    def test_real_tls_posts_once_with_exact_assertions_and_no_ambient_headers(self):
        trusted,connect,state=self.tls_harness()
        with patch('adaptive_qa.egress.resolve_with_deadline',return_value=('93.184.216.34','93.184.216.35')), \
                patch.object(DestinationGuard,'connect',connect), \
                patch('adaptive_qa.public_submission.ssl.create_default_context',return_value=trusted), \
                patch.dict('os.environ',{'HTTPS_PROXY':'http://127.0.0.1:1','HTTP_PROXY':'http://127.0.0.1:1'}):
            transport=self.transport()
            result=transport.submit(**self.request)
            self.assertEqual((result.outcome,result.attempted_submissions),('accepted',1))
            self.assertEqual(transport.submit(**self.request).outcome,'blocked')
            state.update(status=404,body=b'{"found":false}')
            self.assertEqual(self.transport().submit(**self.request).outcome,'rejected')
        self.assertEqual(len(state['contacts']),2)
        for contact in state['contacts']:
            self.assertEqual(contact['host'],'qa.example.test')
            self.assertEqual(contact['path'],'/search/execute')
            self.assertEqual(contact['body'],self.request['body'])
            self.assertIsNone(contact['cookie']);self.assertIsNone(contact['authorization'])
        self.assertNotIn('OWNED_INPUT_CANARY',repr(result))

    def test_redirect_echo_duplicate_and_oversized_responses_are_never_accepted(self):
        trusted,connect,state=self.tls_harness()
        cases=((302,b'{"found":true}',{'Location':'https://127.0.0.1/private'}),
            (200,b'{"found":true,"query":"OWNED_INPUT_CANARY"}',{}),
            (200,b'{"found":false,"found":true}',{}), (200,b'{"found":"true"}',{}),
            (200,b'x'*1025,{}), (200,b'{"found":true}',{'Content-Encoding':'gzip'}),
            (200,b'{"found":true}',{'Transfer-Encoding':'chunked'}))
        with patch('adaptive_qa.egress.resolve_with_deadline',return_value=('93.184.216.34',)) as resolver, \
                patch.object(DestinationGuard,'connect',connect), \
                patch('adaptive_qa.public_submission.ssl.create_default_context',return_value=trusted):
            for status,body,headers in cases:
                state.update(status=status,body=body,headers=headers)
                result=self.transport().submit(**self.request)
                self.assertEqual((result.outcome,result.attempted_submissions),('error',1))
                self.assertNotIn('OWNED_INPUT_CANARY',repr(result))
            self.assertEqual(resolver.call_count,len(cases))
        self.assertEqual(len(state['contacts']),len(cases))

    def test_private_or_mixed_dns_never_connects_and_cannot_retry(self):
        for addresses in (('127.0.0.1',),('93.184.216.34','10.0.0.1')):
            with patch('adaptive_qa.egress.resolve_with_deadline',return_value=addresses), \
                    patch.object(DestinationGuard,'connect') as connect:
                transport=self.transport()
                self.assertEqual(transport.submit(**self.request).outcome,'blocked')
                self.assertEqual(transport.submit(**self.request).outcome,'blocked')
                connect.assert_not_called()

    def test_tls_failures_send_no_post_and_no_connection_fallback_occurs(self):
        trusted,connect,state=self.tls_harness()
        with patch('adaptive_qa.egress.resolve_with_deadline',return_value=('93.184.216.34',)), \
                patch.object(DestinationGuard,'connect',connect):
            result=self.transport().submit(**self.request)
            self.assertEqual((result.outcome,result.attempted_submissions),('error',0))
        wrong=replace(self.proposal,document_url='https://wrong.example.test/search',
                      endpoint_url='https://wrong.example.test/search/execute')
        review=ReviewedPublicForm(wrong,wrong.fingerprint())
        project=replace(self.project,base_url=wrong.document_url,allowed_hosts=('wrong.example.test',))
        with patch('adaptive_qa.egress.resolve_with_deadline',return_value=('93.184.216.34',)), \
                patch.object(DestinationGuard,'connect',connect), \
                patch('adaptive_qa.public_submission.ssl.create_default_context',return_value=trusted):
            result=PublicSubmissionTransport(review,project,current_fingerprint='b'*64).submit(
                **{**self.request,'url':wrong.endpoint_url})
            self.assertEqual((result.outcome,result.attempted_submissions),('error',0))
        self.assertEqual(state['contacts'],[])
        with patch('adaptive_qa.egress.resolve_with_deadline',return_value=('93.184.216.34','93.184.216.35')), \
                patch.object(DestinationGuard,'connect',side_effect=OSError('PRIVATE_EXCEPTION_CANARY')) as connect:
            transport=self.transport()
            result=transport.submit(**self.request)
            self.assertEqual((result.outcome,result.attempted_submissions),('error',0))
            self.assertEqual(transport.submit(**self.request).outcome,'blocked')
            self.assertEqual(connect.call_count,1)
            self.assertEqual(connect.call_args.args[0].addresses,('93.184.216.34',))
            self.assertNotIn('PRIVATE_EXCEPTION_CANARY',repr(result))

    def test_lost_response_is_uncertain_and_never_resubmitted(self):
        trusted,connect,state=self.tls_harness();state['drop']=True
        with patch('adaptive_qa.egress.resolve_with_deadline',return_value=('93.184.216.34',)), \
                patch.object(DestinationGuard,'connect',connect), \
                patch('adaptive_qa.public_submission.ssl.create_default_context',return_value=trusted):
            transport=self.transport()
            result=transport.submit(**self.request)
            self.assertEqual(result.outcome,'error');self.assertIsNone(result.attempted_submissions)
            self.assertEqual(transport.submit(**self.request).outcome,'blocked')
        self.assertEqual(len(state['contacts']),1)
