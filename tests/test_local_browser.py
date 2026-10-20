"""Tests for local browser execution result classification."""

import unittest
from unittest.mock import Mock, patch

from playwright.sync_api import Error, TimeoutError as PlaywrightTimeoutError

from adaptive_qa.local_browser import _capture_evidence, _verify_sample_page, run_login_form_test
from adaptive_qa.models import TestStatus
from pathlib import Path
from tempfile import TemporaryDirectory


class LoginFormResultTests(unittest.TestCase):
    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_successful_verification_returns_passed(
        self,
        verify: Mock,
    ) -> None:
        result = run_login_form_test()

        verify.assert_called_once()
        evidence_path = verify.call_args.args[0]
        self.assertIsInstance(evidence_path, Path)
        self.assertEqual(evidence_path.suffix, ".png")
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

        verify.assert_called_once()
        evidence_path = verify.call_args.args[0]
        self.assertIsInstance(evidence_path, Path)
        self.assertEqual(evidence_path.suffix, ".png")
        self.assertEqual(result.duration_seconds, 0.75)
    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_existing_screenshot_is_linked(self, verify: Mock) -> None:
        verify.side_effect = lambda path: path.write_bytes(b"sample-evidence")

        result = run_login_form_test()

        evidence_path = verify.call_args.args[0]
        self.assertEqual(result.evidence_paths, (evidence_path.as_posix(),))

    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_missing_screenshot_is_not_linked(self, verify: Mock) -> None:
        verify.side_effect = Error("Simulated browser failure")

        result = run_login_form_test()

        self.assertEqual(result.evidence_paths, ())

    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        directory_patch = patch(
            "adaptive_qa.local_browser.Path",
            return_value=Path(temporary.name),
        )
        directory_patch.start()
        self.addCleanup(directory_patch.stop)


class EvidenceCaptureTests(unittest.TestCase):
    def test_screenshot_error_does_not_escape(self) -> None:
        page = Mock()
        page.screenshot.side_effect = Error("Screenshot unavailable")
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.png"
            _capture_evidence(page, path)
            self.assertFalse(path.exists())

    def test_write_error_removes_partial_evidence(self) -> None:
        page = Mock()
        page.screenshot.return_value = b"image"
        path = Mock(spec=Path)
        temporary_path = path.with_suffix.return_value
        temporary_path.write_bytes.side_effect = OSError("Disk unavailable")
        _capture_evidence(page, path)
        temporary_path.unlink.assert_called_once_with(missing_ok=True)
        temporary_path.replace.assert_not_called()

    @patch("adaptive_qa.local_browser.sync_playwright")
    @patch("adaptive_qa.local_browser.expect")
    def test_assertion_failure_keeps_original_error_and_captures_evidence(
        self, expect_mock: Mock, playwright_mock: Mock
    ) -> None:
        browser = playwright_mock.return_value.__enter__.return_value.chromium.launch.return_value
        context = browser.new_context.return_value
        page = context.new_page.return_value
        page.goto.return_value.status = 200
        original = AssertionError("Original assertion failure")
        expect_mock.return_value.to_have_title.side_effect = original
        page.screenshot.return_value = b"image"

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.png"
            with self.assertRaises(AssertionError) as raised:
                _verify_sample_page(path)
            self.assertIs(raised.exception, original)
            self.assertEqual(path.read_bytes(), b"image")
        context.close.assert_called_once()
        browser.close.assert_called_once()

    @patch("adaptive_qa.local_browser.sync_playwright")
    @patch("adaptive_qa.local_browser.expect")
    def test_screenshot_failure_does_not_replace_assertion(
        self, expect_mock: Mock, playwright_mock: Mock
    ) -> None:
        browser = playwright_mock.return_value.__enter__.return_value.chromium.launch.return_value
        page = browser.new_context.return_value.new_page.return_value
        page.goto.return_value.status = 200
        original = AssertionError("Original assertion failure")
        expect_mock.return_value.to_have_title.side_effect = original
        page.screenshot.side_effect = Error("Screenshot unavailable")

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.png"
            with self.assertRaises(AssertionError) as raised:
                _verify_sample_page(path)
            self.assertIs(raised.exception, original)
            self.assertFalse(path.exists())


class BrowserLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.evidence_path = Path(temporary.name) / "evidence.png"

        playwright_patch = patch("adaptive_qa.local_browser.sync_playwright")
        self.playwright_mock = playwright_patch.start()
        self.addCleanup(playwright_patch.stop)
        expect_patch = patch("adaptive_qa.local_browser.expect")
        expect_patch.start()
        self.addCleanup(expect_patch.stop)
        smoke_expect_patch = patch("adaptive_qa.smoke_checks.expect")
        smoke_expect_patch.start()
        self.addCleanup(smoke_expect_patch.stop)

        self.browser = (
            self.playwright_mock.return_value.__enter__.return_value
            .chromium.launch.return_value
        )
        self.context = self.browser.new_context.return_value
        self.page = self.context.new_page.return_value
        self.page.goto.return_value.status = 200
        self.page.screenshot.return_value = b"sample-image"

    def test_success_closes_context_and_browser(self) -> None:
        _verify_sample_page(self.evidence_path)

        self.context.close.assert_called_once_with()
        self.browser.close.assert_called_once_with()
        self.playwright_mock.return_value.__exit__.assert_called_once()

    def test_context_creation_failure_closes_browser(self) -> None:
        original = Error("Context creation failed")
        self.browser.new_context.side_effect = original

        with self.assertRaises(Error) as raised:
            _verify_sample_page(self.evidence_path)

        self.assertIs(raised.exception, original)
        self.browser.close.assert_called_once_with()
        self.context.close.assert_not_called()

    def test_page_creation_failure_closes_context_and_browser(self) -> None:
        original = Error("Page creation failed")
        self.context.new_page.side_effect = original

        with self.assertRaises(Error) as raised:
            _verify_sample_page(self.evidence_path)

        self.assertIs(raised.exception, original)
        self.context.close.assert_called_once_with()
        self.browser.close.assert_called_once_with()
        self.page.screenshot.assert_not_called()

    def test_navigation_timeout_captures_evidence_and_closes_resources(self) -> None:
        original = PlaywrightTimeoutError("Navigation timed out")
        self.page.goto.side_effect = original

        with self.assertRaises(PlaywrightTimeoutError) as raised:
            _verify_sample_page(self.evidence_path)

        self.assertIs(raised.exception, original)
        self.assertEqual(self.evidence_path.read_bytes(), b"sample-image")
        self.context.close.assert_called_once_with()
        self.browser.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()