"""Control fixture dispatch and binding failure classification."""

import unittest
from unittest.mock import patch

from adaptive_qa.element_models import MatchResult, MatchStatus
from adaptive_qa.local_browser import run_sample_test
from adaptive_qa.models import TestStatus
from adaptive_qa.ui_bindings import ElementBindingError


class FixtureBindingTests(unittest.TestCase):
    def test_unknown_fixture_is_blocked_before_browser_launch(self):
        with patch('adaptive_qa.local_browser._verify_sample_page') as verify:
            self.assertEqual(run_sample_test('LOGIN-001', site='customer').status, TestStatus.BLOCKED)
            verify.assert_not_called()

    def test_unregistered_variant_case_is_blocked(self):
        with patch('adaptive_qa.local_browser._verify_sample_page') as verify:
            self.assertEqual(run_sample_test('LOGIN-002', site='turkish').status, TestStatus.BLOCKED)
            verify.assert_not_called()

    def test_missing_and_ambiguous_controls_are_blocked(self):
        for status, count, indexes in ((MatchStatus.MISSING, 0, ()), (MatchStatus.AMBIGUOUS, 2, (0,))):
            with self.subTest(status=status):
                error = ElementBindingError(MatchResult('login.submit', status, count, 'No unique control.', indexes))
                with patch('adaptive_qa.local_browser._verify_sample_page', side_effect=error):
                    result = run_sample_test('LOGIN-001', site='english')
                self.assertEqual(result.status, TestStatus.BLOCKED)
                self.assertIn(status.value, result.message)

    def test_matching_runtime_error_remains_execution_error(self):
        error = ElementBindingError(MatchResult('login.submit', MatchStatus.ERROR, 0, 'Browser unavailable.'))
        with patch('adaptive_qa.local_browser._verify_sample_page', side_effect=error):
            self.assertEqual(run_sample_test('LOGIN-001', site='english').status, TestStatus.ERROR)
