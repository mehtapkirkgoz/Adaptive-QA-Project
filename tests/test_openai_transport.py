"""Mocked HTTPS boundaries only; never contact a model or resolve real keys."""

from dataclasses import replace
import json
import os
import unittest
from unittest.mock import Mock, patch

from adaptive_qa.ai_models import AiBudget
from adaptive_qa.ai_validation import reduce_ai_input
from adaptive_qa.discovery import PageSnapshot
from adaptive_qa.openai_contract import OpenAiConfiguration
from adaptive_qa.openai_transport import OpenAiTransportError, _perform_openai_request
from adaptive_qa.secrets import SecretReference


class OpenAiTransportTests(unittest.TestCase):
    def setUp(self):
        self.budget = AiBudget(max_cost_microusd=10)
        self.config = OpenAiConfiguration('explicit-test-model', SecretReference('QA_TEST_AI_KEY'))
        self.reduced = reduce_ai_input(PageSnapshot('https://example.test'), self.budget)
        self.connection = Mock()
        self.response = self.connection.getresponse.return_value
        self.response.status = 200
        self.response.getheader.side_effect = lambda name, default='': {'Content-Type': 'application/json',
                                                                       'Content-Encoding': 'identity'}.get(name, default)
        text = json.dumps({'website_kind': 'unknown', 'confidence': 0, 'features': [], 'elements': []})
        self.response.read.return_value = json.dumps({'status': 'completed', 'output': [
            {'type': 'message', 'role': 'assistant', 'status': 'completed',
             'content': [{'type': 'output_text', 'text': text}]}]}).encode()
        environment = patch.dict(os.environ, {'QA_TEST_AI_KEY': 'private-test-key'})
        environment.start()
        self.addCleanup(environment.stop)
        self.factory_patch = patch('adaptive_qa.openai_transport.http.client.HTTPSConnection', return_value=self.connection)
        self.factory = self.factory_patch.start()
        self.addCleanup(self.factory_patch.stop)

    def call(self, **kwargs):
        return _perform_openai_request(self.config, self.reduced, (), self.budget,
            **({'remote_enabled': True, 'reserved_cost_microusd': 10} | kwargs))

    def test_default_disabled_and_zero_or_excessive_reservation_never_resolve_or_connect(self):
        with patch.object(SecretReference, 'resolve', side_effect=AssertionError('Unexpected key read')):
            for values in ({'remote_enabled': False}, {'reserved_cost_microusd': 0},
                           {'reserved_cost_microusd': 11}, {'reserved_cost_microusd': True}):
                with self.subTest(values=values), self.assertRaises(OpenAiTransportError):
                    self.call(**values)
        self.factory.assert_not_called()

    def test_fixed_https_endpoint_validated_output_and_connection_cleanup(self):
        advice = self.call()
        self.assertFalse(advice.execution_authorized)
        self.assertEqual(self.factory.call_args.args, ('api.openai.com', 443))
        self.assertEqual(self.connection.request.call_args.args[:2], ('POST', '/v1/responses'))
        payload = json.loads(self.connection.request.call_args.kwargs['body'])
        self.assertFalse(payload['store'])
        self.assertEqual(payload['tools'], [])
        self.connection.close.assert_called_once()

    def test_redirect_auth_and_rate_limit_errors_never_retry_or_read_body(self):
        for status in (301, 307, 401, 429, 500):
            self.connection.reset_mock()
            self.response.status = status
            with self.subTest(status=status), self.assertRaises(OpenAiTransportError):
                self.call()
            self.assertEqual(self.connection.request.call_count, 1)
            self.response.read.assert_not_called()
            self.connection.close.assert_called_once()

    def test_missing_or_header_injected_secret_never_connects(self):
        for value in ('', 'invalid\r\nHeader: secret', 'token with space', 'ünicode'):
            with patch.dict(os.environ, {'QA_TEST_AI_KEY': value}), self.assertRaises(OpenAiTransportError):
                self.call()
        self.factory.assert_not_called()

    def test_bad_media_or_encoding_closes_without_processing_body(self):
        for media, encoding in (('text/html', 'identity'), ('application/json', 'gzip')):
            self.response.getheader.side_effect = lambda name, default='': {
                'Content-Type': media, 'Content-Encoding': encoding}.get(name, default)
            with self.subTest(media=media), self.assertRaises(OpenAiTransportError):
                self.call()
        self.response.read.assert_not_called()

    def test_oversized_and_malformed_bodies_are_safe_failures(self):
        for body in (b'x' * 262145, b'private-body-not-json'):
            self.response.read.return_value = body
            with self.subTest(length=len(body)), self.assertRaises(OpenAiTransportError) as failure:
                self.call()
            self.assertNotIn('private', str(failure.exception))

    def test_socket_failures_hide_private_details_and_close_connection(self):
        self.connection.connect.side_effect = OSError('private-test-key private OS details')
        with self.assertRaises(OpenAiTransportError) as failure:
            self.call()
        self.assertNotIn('private', str(failure.exception))
        self.connection.close.assert_called_once()

    def test_zero_budget_cannot_be_enabled_by_caller_flags(self):
        with self.assertRaises(OpenAiTransportError):
            _perform_openai_request(self.config, self.reduced, (), AiBudget(),
                                   remote_enabled=True, reserved_cost_microusd=1)
        self.factory.assert_not_called()
