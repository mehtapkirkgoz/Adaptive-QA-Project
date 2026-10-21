"""Preparation, failure cleanup, and mutation-policy boundaries."""

from dataclasses import FrozenInstanceError, replace
from unittest.mock import Mock, patch
import unittest

from playwright.sync_api import Error

from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.local_browser import run_sample_test
from adaptive_qa.models import TestStatus
from adaptive_qa.sample_data import FixtureCleanupError, sample_test_data


class SampleDataTests(unittest.TestCase):
    def page(self):
        page = Mock()
        page.url = 'http://127.0.0.1:8000/variants/english.html'
        return page

    def test_preparation_and_cleanup_run_on_success(self):
        page = self.page()
        with sample_test_data(page) as data:
            self.assertEqual(data.email, 'qa@example.test')
            with self.assertRaises(FrozenInstanceError):
                data.username = 'changed'
        self.assertEqual(page.evaluate.call_count, 2)
        self.assertEqual(page.context.clear_cookies.call_count, 2)

    def test_assertion_failure_still_cleans_state(self):
        page = self.page()
        with self.assertRaises(AssertionError):
            with sample_test_data(page):
                raise AssertionError('Controlled failure')
        self.assertEqual(page.context.clear_cookies.call_count, 2)

    def test_external_or_unregistered_origin_is_rejected_before_evaluation(self):
        for url in ('https://example.com/', 'http://127.0.0.1:8001/', 'http://127.0.0.1:8000/unknown'):
            page = self.page()
            page.url = url
            with self.subTest(url=url), self.assertRaises(ValueError):
                with sample_test_data(page):
                    pass
            page.evaluate.assert_not_called()

    def test_cleanup_error_is_explicit_and_not_reported_as_a_pass(self):
        page = self.page()
        page.evaluate.side_effect = [None, Error('Page closed')]
        with self.assertRaises(FixtureCleanupError):
            with sample_test_data(page):
                pass
        with patch('adaptive_qa.local_browser._verify_sample_page', side_effect=FixtureCleanupError('Cleanup failed')):
            self.assertEqual(run_sample_test('LOGIN-005').status, TestStatus.ERROR)

    def test_data_changing_case_is_blocked_before_browser_preparation(self):
        definition = next(case for case in TEST_CASES if case.case_id == 'LOGIN-005')
        with patch('adaptive_qa.local_browser.TEST_CASES', (replace(definition, changes_data=True),)), \
             patch('adaptive_qa.local_browser._verify_sample_page') as verify:
            result = run_sample_test('LOGIN-005', site='english')
        self.assertEqual(result.status, TestStatus.BLOCKED)
        verify.assert_not_called()
