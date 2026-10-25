"""Public HTTPS contracts verified offline and against an owned local TLS harness."""
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

from adaptive_qa.api_models import ApiConfiguration, ApiRequest, HttpMethod
from adaptive_qa.api_process import decode_api_input, encode_api_input
from adaptive_qa.api_transport import ApiPolicyError, perform_request, run_api_case
from adaptive_qa.models import TestStatus
from adaptive_qa.config import ProjectConfig
from adaptive_qa.egress import DestinationGuard
from adaptive_qa.local_api_review import review_local_api, run_reviewed_local_api
from adaptive_qa.local_api_settings import saved_api_case


class HttpsApiTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectConfig('a'*32, 'HTTPS API', 'https://api.example.test', ('api.example.test',))
        local = replace(self.project, base_url='http://127.0.0.1:8000', allowed_hosts=('127.0.0.1',))
        self.case = saved_api_case(dict(path='/ready', expected_status=200, json_field='ready', expected_boolean=True), local)
        self.config = ApiConfiguration(self.project, execution_profile='public_https')

    def test_review_is_offline_explicit_and_private_transport_preserves_profile(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
                patch('adaptive_qa.secrets.SecretReference.resolve', side_effect=AssertionError('No secrets')):
            review = review_local_api(self.project, self.case, profile='public_https')
        with self.assertRaises(ValueError):review_local_api(self.project, self.case)
        _, decoded = decode_api_input(encode_api_input(self.case, self.config))
        self.assertEqual(decoded, self.config)
        with patch('adaptive_qa.api_process.run_isolated_api_case') as child:
            run_reviewed_local_api(review, self.project, confirmed_fingerprint=review.fingerprint)
            self.assertEqual(child.call_args.args[1].execution_profile, 'public_https')
            self.assertEqual(child.call_args.kwargs['timeout_seconds'], 15)
            with self.assertRaises(ValueError):
                run_reviewed_local_api(review, replace(self.project, name='Changed'), confirmed_fingerprint=review.fingerprint)

    def test_plain_http_private_literals_nonstandard_ports_and_paths_are_not_public_profiles(self):
        for origin in ('http://api.example.test', 'https://127.0.0.1', 'https://10.0.0.1',
                       'https://localhost', 'https://api.example.test:8443', 'https://api.example.test/path'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                from urllib.parse import urlsplit
                ApiConfiguration(replace(self.project, base_url=origin, allowed_hosts=(urlsplit(origin).hostname,)), execution_profile='public_https')

    def test_authentication_query_and_writes_never_connect(self):
        requests = (ApiRequest('/ready', use_authentication=True), ApiRequest('/ready', query=(('q','value'),)),
                    ApiRequest('/ready', HttpMethod.POST, body_json='{}'))
        with patch('adaptive_qa.api_transport.DestinationGuard') as guard:
            for request in requests:
                with self.assertRaises(ApiPolicyError):perform_request(self.config, request)
                with self.assertRaises(ValueError):review_local_api(self.project, replace(self.case, request=request), profile='public_https')
            guard.assert_not_called()

    def test_mixed_or_private_dns_answers_are_denied_before_connect(self):
        for addresses in (('127.0.0.1',), ('93.184.216.34','10.0.0.1'), ('169.254.169.254',)):
            with patch('adaptive_qa.egress.resolve_with_deadline', return_value=addresses), \
                    patch.object(DestinationGuard, 'connect') as connect:
                with self.assertRaises(ValueError):perform_request(self.config, self.case.request)
                self.assertEqual(run_api_case(self.case,self.config).status,TestStatus.BLOCKED)
                connect.assert_not_called()

    def tls_harness(self):
        temporary = TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root = Path(temporary.name); key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'api.example.test')])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
            .not_valid_after(now+timedelta(hours=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName('api.example.test')]),False)
            .add_extension(x509.BasicConstraints(ca=True,path_length=None),True).sign(key,hashes.SHA256()))
        cert_path=root/'ca.pem';key_path=root/'key.pem'
        cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        contacts=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                contacts.append(self.path)
                self.send_response(302 if self.path=='/redirect' else 200)
                if self.path=='/redirect':self.send_header('Location','https://127.0.0.1/private')
                self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{"ready":true}')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert_path,key_path)
        server.socket=context.wrap_socket(server.socket,server_side=True)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        def close():server.shutdown();server.server_close();thread.join(timeout=5)
        self.addCleanup(close)
        trusted=ssl.create_default_context(cafile=str(cert_path))
        def owned_connect(guard,target,**kwargs):
            self.assertFalse(guard.local_sample);self.assertEqual(target.port,443)
            self.assertEqual(target.addresses,('93.184.216.34',))
            return socket.create_connection(('127.0.0.1',server.server_port),timeout=2)
        return trusted,owned_connect,contacts

    def test_real_tls_verifies_hostname_and_does_not_follow_redirect(self):
        trusted,connect,contacts=self.tls_harness()
        with patch('adaptive_qa.egress.resolve_with_deadline',return_value=('93.184.216.34',)), \
                patch.object(DestinationGuard,'connect',connect), \
                patch('adaptive_qa.api_transport.ssl.create_default_context',return_value=trusted):
            response=perform_request(self.config,self.case.request)
            self.assertEqual(response.payload,{'ready':True})
            response=perform_request(self.config,ApiRequest('/redirect'))
            self.assertEqual(response.status,302)
            wrong=ApiConfiguration(replace(self.project,base_url='https://wrong.example.test',allowed_hosts=('wrong.example.test',)),execution_profile='public_https')
            with self.assertRaises(ssl.SSLCertVerificationError):perform_request(wrong,self.case.request)
        self.assertEqual(contacts,['/ready','/redirect'])

    def test_untrusted_certificate_is_not_accepted(self):
        _,connect,contacts=self.tls_harness()
        with patch('adaptive_qa.egress.resolve_with_deadline',return_value=('93.184.216.34',)), \
                patch.object(DestinationGuard,'connect',connect):
            with self.assertRaises(ssl.SSLCertVerificationError):perform_request(self.config,self.case.request)
        self.assertEqual(contacts,[])


if __name__=='__main__':unittest.main()
