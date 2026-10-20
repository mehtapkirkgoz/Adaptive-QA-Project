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


if __name__ == "__main__":
    unittest.main()
