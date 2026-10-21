"""Offline provider wire contracts; no credentials resolved and no HTTP calls."""

from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from adaptive_qa.ai_models import AiBudget
from adaptive_qa.ai_validation import reduce_ai_input
from adaptive_qa.discovery import FormSnapshot, PageSnapshot
from adaptive_qa.openai_contract import OpenAiConfiguration, build_openai_request, extract_openai_text
from adaptive_qa.secrets import SecretReference


class OpenAiContractTests(unittest.TestCase):
    def setUp(self):
        self.budget = AiBudget()
        self.page = PageSnapshot('https://example.test/private?secret=private-token',
            forms=(FormSnapshot(buttons=('Sign in',)),), collection_complete=False)
        self.reduced = reduce_ai_input(self.page, self.budget)
        self.config = OpenAiConfiguration('explicit-test-model', SecretReference('QA_OPENAI_KEY'))
        self.envelope = {'status': 'completed', 'output': [{'type': 'message', 'role': 'assistant',
            'status': 'completed', 'content': [{'type': 'output_text', 'text': '{}'}]}]}

    def test_builder_is_pure_and_omits_secrets_and_raw_urls(self):
        with patch.object(SecretReference, 'resolve', side_effect=AssertionError('Unexpected resolution')):
            payload = build_openai_request(self.config, self.reduced, ('login.submit',), self.budget)
        text = json.dumps(payload)
        self.assertNotIn('QA_OPENAI_KEY', text)
        self.assertNotIn('private-token', text)
        self.assertNotIn('example.test', text)
        self.assertFalse(payload['store'])
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['tools'], [])
        self.assertEqual(payload['tool_choice'], 'none')

    def test_schema_is_closed_and_limits_references_and_absence(self):
        payload = build_openai_request(self.config, self.reduced, ('login.submit',), self.budget)
        schema = payload['text']['format']['schema']
        self.assertFalse(schema['additionalProperties'])
        feature = schema['properties']['features']['items']
        self.assertNotIn('absent', feature['properties']['status']['enum'])
        self.assertEqual(feature['properties']['evidence_ids']['items']['enum'], ['form_0'])
        element = schema['properties']['elements']['items']
        self.assertEqual(element['properties']['candidate_id']['enum'], ['button_0_0'])

    def test_empty_collections_cannot_request_uncollected_references(self):
        reduced = reduce_ai_input(PageSnapshot('https://example.test'), self.budget)
        schema = build_openai_request(self.config, reduced, (), self.budget)['text']['format']['schema']
        self.assertEqual(schema['properties']['features']['maxItems'], 0)
        self.assertEqual(schema['properties']['elements']['maxItems'], 0)

    def test_explicit_model_secret_reference_and_token_limits_are_required(self):
        for values in ({'model': ''}, {'model': '../model'}, {'api_key': 'raw-key'},
                       {'max_output_tokens': True}, {'max_output_tokens': 4097}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(self.config, **values)

    def test_completed_single_text_is_extracted_without_trusting_inner_json(self):
        self.assertEqual(extract_openai_text(json.dumps(self.envelope).encode(), self.budget), '{}')

    def test_refusal_tools_incomplete_and_multiple_messages_are_rejected(self):
        for mode in ('incomplete', 'refusal', 'tool', 'multiple', 'error'):
            raw = json.loads(json.dumps(self.envelope))
            if mode == 'incomplete': raw['status'] = 'incomplete'
            elif mode == 'refusal': raw['output'][0]['content'][0] = {'type': 'refusal', 'refusal': 'private-reason'}
            elif mode == 'tool': raw['output'][0]['type'] = 'function_call'
            elif mode == 'multiple': raw['output'] *= 2
            else: raw['error'] = {'message': 'private-error'}
            with self.subTest(mode=mode), self.assertRaises(ValueError) as error:
                extract_openai_text(json.dumps(raw).encode(), self.budget)
            self.assertNotIn('private', str(error.exception))

    def test_envelope_and_text_byte_caps_are_enforced(self):
        for body, budget in ((b'x' * 262145, self.budget),
                             (json.dumps(self.envelope).encode(), replace(self.budget, max_output_bytes=1))):
            with self.assertRaises(ValueError):
                extract_openai_text(body, budget)
