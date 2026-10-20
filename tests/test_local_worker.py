"""Tests for queued local execution and persistence failures."""

import unittest
from pathlib import Path
from unittest.mock import patch

from adaptive_qa.jobs import JobStatus, LocalJobQueue
from adaptive_qa.local_worker import process_next
from adaptive_qa.models import TestResult, TestStatus


class LocalWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.queue = LocalJobQueue()
        runner_patch = patch("adaptive_qa.local_worker.run_login_form_test")
        self.runner = runner_patch.start()
        self.addCleanup(runner_patch.stop)
        self.runner.return_value = TestResult("LOGIN-001", TestStatus.PASSED, 0.1, "Passed.")
        save_patch = patch("adaptive_qa.local_worker.save_result", return_value=Path("result.json"))
        self.save = save_patch.start()
        self.addCleanup(save_patch.stop)

    def test_empty_queue_does_not_execute(self) -> None:
        self.assertIsNone(process_next(self.queue))
        self.runner.assert_not_called()
        self.save.assert_not_called()

    def test_claimed_job_is_executed_and_saved_with_job_id(self) -> None:
        job = self.queue.submit("LOGIN-001")
        processed = process_next(self.queue)
        self.runner.assert_called_once_with()
        self.save.assert_called_once_with(self.runner.return_value, job_id=job.job_id)
        self.assertEqual(processed.job.status, JobStatus.COMPLETED)
        self.assertEqual(processed.result_path, Path("result.json"))

    def test_cancelled_job_is_not_executed(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.cancel(job.job_id)
        self.assertIsNone(process_next(self.queue))
        self.runner.assert_not_called()
        self.save.assert_not_called()

    def test_unregistered_case_is_blocked(self) -> None:
        self.queue.submit("UNKNOWN-001")
        processed = process_next(self.queue)
        self.runner.assert_not_called()
        self.assertEqual(processed.job.result.status, TestStatus.BLOCKED)

    def test_unexpected_execution_error_completes_with_error(self) -> None:
        self.queue.submit("LOGIN-001")
        self.runner.side_effect = RuntimeError("Do not expose details")
        processed = process_next(self.queue)
        self.assertEqual(processed.job.status, JobStatus.COMPLETED)
        self.assertEqual(processed.job.result.status, TestStatus.ERROR)
        self.assertNotIn("Do not expose", processed.job.result.message)

    def test_storage_failure_is_not_reported_as_saved(self) -> None:
        self.queue.submit("LOGIN-001")
        self.save.side_effect = OSError("Disk unavailable")
        processed = process_next(self.queue)
        self.assertIsNone(processed.result_path)
        self.assertEqual(processed.job.result.status, TestStatus.ERROR)
        self.assertEqual(processed.job.status, JobStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
