"""Local-only provider contract tests; no model download or inference required."""

import json
import unittest
from unittest.mock import Mock, patch

from adaptive_qa.ai_models import AiBudget
from adaptive_qa.ai_validation import reduce_ai_input
from adaptive_qa.discovery import PageSnapshot
from adaptive_qa.ollama_provider import OllamaProvider, request_ollama


class OllamaProviderTests(unittest.TestCase):
    def setUp(self):
        self.budget = AiBudget()
        self.reduced = reduce_ai_input(PageSnapshot('https://example.test/private'), self.budget)
        self.provider = OllamaProvider()
        self.connection = Mock()
        self.response = self.connection.getresponse.return_value
        self.response.status = 200
        self.response.getheader.side_effect = lambda key, default='': {
            'Content-Type': 'application/json', 'Content-Encoding': 'identity'}.get(key, default)
        self.envelope = {'model': 'qwen3:4b', 'done': True, 'done_reason': 'stop',
                         'message': {'role': 'assistant', 'content': '{}'}}
        self.response.read.return_value = json.dumps(self.envelope).encode()
        factory = patch('adaptive_qa.ollama_provider.http.client.HTTPConnection', return_value=self.connection)
        self.factory = factory.start()
        self.addCleanup(factory.stop)

    def call(self):
        return request_ollama(self.provider, self.reduced, (), self.budget)

    def test_local_numeric_endpoint_has_no_credentials_tools_or_streaming(self):
        self.assertEqual(self.call(), '{}')
        self.assertEqual(self.factory.call_args.args, ('127.0.0.1', 11434))
        args = self.connection.request.call_args
        self.assertEqual(args.args, ('POST', '/api/chat'))
        self.assertNotIn('Authorization', args.kwargs['headers'])
        payload = json.loads(args.kwargs['body'])
        self.assertFalse(payload['stream'])
        self.assertFalse(payload['think'])
        self.assertEqual(payload['keep_alive'], 0)
        self.assertNotIn('tools', payload)
        self.connection.close.assert_called_once()

    def test_cloud_urls_aliases_and_cloud_models_are_rejected(self):
        for model in ('qwen3:4b-cloud', 'https://ollama.com/qwen3', 'other-model', ''):
            with self.subTest(model=model), self.assertRaises(ValueError):
                OllamaProvider(model)

    def test_redirects_and_error_statuses_are_not_followed_or_retried(self):
        for status in (307, 401, 404, 500):
            self.response.status = status
            self.connection.reset_mock()
            with self.assertRaises(ValueError):
                self.call()
            self.assertEqual(self.connection.request.call_count, 1)
            self.response.read.assert_not_called()

    def test_incomplete_mismatched_and_tool_messages_are_rejected(self):
        for update in ({'done': False}, {'done_reason': 'length'}, {'model': 'cloud-model'},
                       {'message': {'role': 'assistant', 'content': '{}', 'tool_calls': [{}]}},
                       {'message': {'role': 'assistant', 'content': '{}', 'thinking': 'private-thought'}}):
            self.response.read.return_value = json.dumps(self.envelope | update).encode()
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.call()

    def test_body_text_and_encoding_limits_reject_unsupported_output(self):
        self.response.read.return_value = b'x' * 131073
        with self.assertRaises(ValueError):
            self.call()
        self.response.getheader.side_effect = lambda key, default='': {
            'Content-Type': 'application/json', 'Content-Encoding': 'gzip'}.get(key, default)
        with self.assertRaises(ValueError):
            self.call()

    def test_socket_errors_always_close_connection(self):
        self.connection.request.side_effect = OSError('controlled failure')
        with self.assertRaises(OSError):
            self.call()
        self.connection.close.assert_called_once()

    def test_token_budget_is_bounded_and_typed(self):
        for tokens in (True, 0, 2049):
            with self.assertRaises(ValueError):
                OllamaProvider(max_output_tokens=tokens)
