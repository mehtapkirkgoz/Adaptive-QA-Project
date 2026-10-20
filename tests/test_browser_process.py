"""Tests for isolated browser deadlines and result transport."""

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from adaptive_qa.browser_process import _read_result, run_isolated_login_test
from adaptive_qa.models import TestResult, TestStatus


class BrowserProcessTests(unittest.TestCase):
    @patch("adaptive_qa.browser_process.subprocess.Popen")
    def test_invalid_deadlines_are_rejected_before_launch(self, launch: Mock) -> None:
        for timeout in (0, -1, True, None, float("nan"), float("inf")):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    run_isolated_login_test(timeout)
        launch.assert_not_called()

    @patch("adaptive_qa.browser_process._terminate_process_tree")
    @patch("adaptive_qa.browser_process.subprocess.Popen")
    def test_timeout_terminates_tree_and_returns_error(self, launch, terminate) -> None:
        process = launch.return_value
        process.wait.side_effect = subprocess.TimeoutExpired("browser", 30)
        process.poll.return_value = -1
        with patch("adaptive_qa.browser_process.perf_counter", side_effect=[0, 31, 32]):
            result = run_isolated_login_test()
        terminate.assert_called_once_with(process)
        self.assertEqual(result.status, TestStatus.ERROR)
        self.assertIn("time limit", result.message)
        self.assertEqual(result.evidence_paths, ())

    @patch("adaptive_qa.browser_process.subprocess.Popen")
    def test_nonzero_child_exit_returns_error(self, launch) -> None:
        launch.return_value.returncode = 1
        launch.return_value.poll.return_value = 1
        result = run_isolated_login_test()
        self.assertEqual(result.status, TestStatus.ERROR)
        self.assertIn("exited unexpectedly", result.message)

    @patch("adaptive_qa.browser_process._read_result")
    @patch("adaptive_qa.browser_process.subprocess.Popen")
    def test_child_result_is_preserved(self, launch, read) -> None:
        launch.return_value.returncode = 0
        launch.return_value.poll.return_value = 0
        expected = TestResult("LOGIN-001", TestStatus.FAILED, 0.1, "Failed.")
        read.return_value = expected
        self.assertEqual(run_isolated_login_test(), expected)

    @patch("adaptive_qa.browser_process._read_result")
    @patch("adaptive_qa.browser_process.subprocess.Popen")
    def test_invalid_transport_result_returns_error(self, launch, read) -> None:
        launch.return_value.returncode = 0
        launch.return_value.poll.return_value = 0
        read.side_effect = ValueError("Invalid result")
        self.assertEqual(run_isolated_login_test().status, TestStatus.ERROR)

    def test_read_result_restores_types_and_rejects_wrong_case(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            payload = dict(case_id="LOGIN-001", status="passed", duration_seconds=0.1,
                           message="Passed.", evidence_paths=["image.png"])
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(_read_result(path).evidence_paths, ("image.png",))
            payload["case_id"] = "OTHER-001"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                _read_result(path)

    @patch("adaptive_qa.browser_process.subprocess.Popen")
    def test_cancellation_before_launch_does_not_start_browser(self, launch) -> None:
        result = run_isolated_login_test(should_cancel=lambda: True)
        self.assertEqual(result.status, TestStatus.CANCELLED)
        launch.assert_not_called()

    @patch("adaptive_qa.browser_process._terminate_process_tree")
    @patch("adaptive_qa.browser_process.subprocess.Popen")
    def test_active_cancellation_terminates_process_tree(self, launch, terminate) -> None:
        launch.return_value.poll.return_value = -1
        cancel = Mock(side_effect=[False, True])
        result = run_isolated_login_test(should_cancel=cancel)
        terminate.assert_called_once_with(launch.return_value)
        self.assertEqual(result.status, TestStatus.CANCELLED)

    @patch("adaptive_qa.browser_process._terminate_process_tree")
    @patch("adaptive_qa.browser_process.subprocess.Popen")
    def test_failed_termination_is_not_reported_as_cancelled(self, launch, terminate) -> None:
        launch.return_value.poll.return_value = -1
        terminate.side_effect = RuntimeError("Termination failed")
        with self.assertRaises(RuntimeError):
            run_isolated_login_test(should_cancel=Mock(side_effect=[False, True]))


if __name__ == "__main__":
    unittest.main()
