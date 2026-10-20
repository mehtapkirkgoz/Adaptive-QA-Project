"""Tests for persistent queue CLI commands across separate invocations."""

import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from adaptive_qa.local_worker import main
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.sqlite_queue import SQLiteJobQueue


class WorkerCLITests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.args = ["--database", str(Path(temporary.name) / "jobs.sqlite3")]

    def command(self, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            code = main(self.args + list(args))
        return code, output.getvalue()

    def submit(self) -> str:
        code, output = self.command("submit", "LOGIN-001")
        self.assertEqual(code, 0)
        return json.loads(output)["job_id"]

    def test_job_can_be_read_in_a_later_invocation(self) -> None:
        job_id = self.submit()
        code, output = self.command("status", job_id)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["status"], "queued")

    @patch("adaptive_qa.local_worker.run_login_form_test")
    @patch("adaptive_qa.local_worker.save_result")
    def test_run_next_persists_completion_for_later_status(self, save, run) -> None:
        run.return_value = TestResult("LOGIN-001", TestStatus.PASSED, 0.1, "Passed.")
        save.return_value = Path("result.json")
        job_id = self.submit()
        self.assertEqual(self.command("run-next")[0], 0)
        _, output = self.command("status", job_id)
        job = json.loads(output)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result"]["status"], "passed")

    @patch("adaptive_qa.local_worker.run_login_form_test")
    def test_cancelled_job_is_not_run(self, run) -> None:
        job_id = self.submit()
        self.assertEqual(self.command("cancel", job_id)[0], 0)
        self.assertEqual(self.command("run-next")[0], 0)
        run.assert_not_called()
        _, output = self.command("status", job_id)
        self.assertEqual(json.loads(output)["status"], "cancelled")

    @patch("adaptive_qa.local_worker.run_login_form_test")
    @patch("adaptive_qa.local_worker.save_result")
    def test_failed_test_returns_nonzero(self, save, run) -> None:
        run.return_value = TestResult("LOGIN-001", TestStatus.FAILED, 0.1, "Failed.")
        save.return_value = Path("result.json")
        self.submit()
        self.assertEqual(self.command("run-next")[0], 1)

    def test_unknown_job_returns_nonzero(self) -> None:
        self.assertEqual(self.command("status", "missing")[0], 1)

    def test_list_filters_cancelled_jobs_across_invocations(self) -> None:
        cancelled = self.submit()
        self.submit()
        self.command("cancel", cancelled)
        code, output = self.command("list", "--status", "cancelled")
        self.assertEqual(code, 0)
        self.assertEqual([job["job_id"] for job in json.loads(output)], [cancelled])

    def test_list_invalid_limit_returns_nonzero(self) -> None:
        self.assertEqual(self.command("list", "--limit", "0")[0], 1)

    @patch("adaptive_qa.local_worker.run_login_form_test")
    @patch("adaptive_qa.local_worker.save_result")
    def test_retry_command_returns_linked_pending_attempt(self, save, run) -> None:
        run.return_value = TestResult("LOGIN-001", TestStatus.FAILED, 0.1, "Failed.")
        save.return_value = Path("result.json")
        original = self.submit()
        self.command("run-next")
        code, output = self.command("retry", original)
        self.assertEqual(code, 0)
        retry = json.loads(output)
        self.assertEqual(retry["retry_of"], original)
        self.assertEqual(retry["status"], "queued")

    def test_cancel_command_records_request_for_running_job(self) -> None:
        job_id = self.submit()
        queue = SQLiteJobQueue(Path(self.args[1]))
        queue.claim_next()
        code, output = self.command("cancel", job_id)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["status"], "cancel_requested")

    @patch("adaptive_qa.local_worker.run_login_form_test")
    @patch("adaptive_qa.local_worker.save_result")
    def test_cancel_request_wins_before_result_persistence(self, save, run) -> None:
        job_id = self.submit()
        queue = SQLiteJobQueue(Path(self.args[1]))
        def execute(*, should_cancel):
            queue.request_cancel(job_id)
            self.assertTrue(should_cancel())
            return TestResult("LOGIN-001", TestStatus.PASSED, 0.1, "Passed.")
        run.side_effect = execute
        save.return_value = Path("result.json")
        self.assertEqual(self.command("run-next")[0], 1)
        self.assertEqual(save.call_args.args[0].status, TestStatus.CANCELLED)
        _, output = self.command("status", job_id)
        self.assertEqual(json.loads(output)["status"], "cancelled")

    def test_recover_command_repairs_interrupted_job_without_requeue(self) -> None:
        job_id = self.submit()
        queue = SQLiteJobQueue(Path(self.args[1]))
        queue.claim_next()
        code, output = self.command("recover-interrupted")
        self.assertEqual(code, 0)
        recovered = json.loads(output)
        self.assertEqual(recovered[0]["job_id"], job_id)
        self.assertEqual(recovered[0]["result"]["status"], "error")
        self.assertIsNone(queue.claim_next())


if __name__ == "__main__":
    unittest.main()
