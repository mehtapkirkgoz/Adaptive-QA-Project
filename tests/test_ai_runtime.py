"""Actual child deadlines, concurrency admission, and safe offline fallback."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from time import monotonic
import unittest
from unittest.mock import patch

from adaptive_qa.ai_models import AiBudget
from adaptive_qa.ai_runtime import AiSession, OfflineAiProvider
from adaptive_qa.discovery import PageSnapshot


class AiRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.page = PageSnapshot('https://example.test/private', collection_complete=True)
        self.provider = OfflineAiProvider(json.dumps({'website_kind': 'unknown', 'confidence': 0,
                                                     'features': [], 'elements': []}))

    def test_real_scripted_child_returns_advice_without_authorization(self):
        result = AiSession(AiBudget()).suggest(self.page, (), self.provider)
        self.assertEqual(result.status, 'accepted')
        self.assertFalse(result.advice.execution_authorized)

    def test_disabled_provider_never_spawns(self):
        with patch('adaptive_qa.ai_runtime.subprocess.Popen') as popen:
            result = AiSession(AiBudget()).suggest(self.page, (), None)
        self.assertEqual(result.status, 'unavailable')
        popen.assert_not_called()

    def test_failed_attempt_consumes_request_budget_without_leaking_response(self):
        session = AiSession(AiBudget())
        failed = session.suggest(self.page, (), OfflineAiProvider('private-secret', fail=True))
        self.assertEqual(failed.status, 'unavailable')
        self.assertNotIn('private-secret', repr(failed))
        self.assertEqual(session.suggest(self.page, (), self.provider).status, 'budget_exhausted')

    def test_real_stalled_child_is_terminated_by_session_deadline(self):
        session = AiSession(AiBudget(timeout_seconds=0.3))
        started = monotonic()
        result = session.suggest(self.page, (), replace(self.provider, delay_seconds=5))
        self.assertEqual(result.status, 'timeout')
        self.assertLess(monotonic() - started, 4)
        self.assertEqual(session.suggest(self.page, (), self.provider).status, 'budget_exhausted')

    def test_concurrent_calls_share_one_request_slot(self):
        session = AiSession(AiBudget())
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: session.suggest(self.page, (), self.provider), range(2)))
        self.assertEqual(sorted(r.status for r in results), ['accepted', 'budget_exhausted'])

    def test_oversized_invalid_and_authorizing_outputs_fall_back(self):
        for response in ('x' * 200, 'not-json', self.provider.response[:-1] + ',"execute":true}'):
            with self.subTest(response=response[:15]):
                result = AiSession(AiBudget(max_output_bytes=128)).suggest(self.page, (), OfflineAiProvider(response))
                self.assertEqual(result.status, 'rejected')
                self.assertIsNone(result.advice)

    def test_input_rejection_does_not_spawn_or_consume_request_slot(self):
        session = AiSession(AiBudget(max_input_bytes=1))
        with patch('adaptive_qa.ai_runtime.subprocess.Popen') as popen:
            self.assertEqual(session.suggest(self.page, (), self.provider).status, 'rejected')
        popen.assert_not_called()

    def test_cost_admission_rejects_amount_above_configured_cap(self):
        session = AiSession(AiBudget(max_cost_microusd=1))
        self.assertFalse(session._reserve(2))
        self.assertTrue(session._reserve(1))
