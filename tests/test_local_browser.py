"""Tests for local browser execution result classification."""

import unittest
from unittest.mock import Mock, patch

from playwright.sync_api import Error

from adaptive_qa.local_browser import run_login_form_test
from adaptive_qa.models import TestStatus


class LoginFormResultTests(unittest.TestCase):
    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_successful_verification_returns_passed(
        self,
        verify: Mock,
    ) -> None:
        result = run_login_form_test()

        verify.assert_called_once_with()
        self.assertEqual(result.case_id, "LOGIN-001")
        self.assertEqual(result.status, TestStatus.PASSED)
        self.assertGreaterEqual(result.duration_seconds, 0)

    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_assertion_failure_returns_failed(
        self,
        verify: Mock,
    ) -> None:
        verify.side_effect = AssertionError("Simulated assertion failure")

        result = run_login_form_test()

        self.assertEqual(result.status, TestStatus.FAILED)

    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_playwright_error_returns_error(
        self,
        verify: Mock,
    ) -> None:
        verify.side_effect = Error("Simulated browser failure")

        result = run_login_form_test()

        self.assertEqual(result.status, TestStatus.ERROR)
        self.assertNotIn("Simulated browser failure", result.message)

    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_page_loading_error_returns_error(
        self,
        verify: Mock,
    ) -> None:
        verify.side_effect = RuntimeError("Simulated loading failure")

        result = run_login_form_test()

        self.assertEqual(result.status, TestStatus.ERROR)

    @patch("adaptive_qa.local_browser.perf_counter")
    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_duration_measures_elapsed_time(
        self,
        verify: Mock,
        clock: Mock,
    ) -> None:
        clock.side_effect = [10.0, 10.75]

        result = run_login_form_test()

        verify.assert_called_once_with()
        self.assertEqual(result.duration_seconds, 0.75)


if __name__ == "__main__":
    unittest.main()