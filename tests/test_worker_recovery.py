"""Tests for exclusive local execution and explicit interrupted-job recovery."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from adaptive_qa.jobs import JobStatus
from adaptive_qa.local_worker import process_next
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.sqlite_queue import SQLiteJobQueue
from adaptive_qa.worker_lock import worker_lock


class WorkerRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / "queue.sqlite3"
        self.queue = SQLiteJobQueue(self.database)

    def test_active_worker_lock_blocks_recovery_and_second_executor(self) -> None:
        job = self.queue.submit("LOGIN-001")
        with worker_lock(self.database):
            with self.assertRaisesRegex(ValueError, "worker lock"):
                self.queue.recover_interrupted()
            with self.assertRaisesRegex(ValueError, "worker lock"):
                process_next(SQLiteJobQueue(self.database))
        self.assertEqual(self.queue.get(job.job_id).status, JobStatus.QUEUED)

    def test_recovery_handles_each_interrupted_state(self) -> None:
        running = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        requested = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        self.queue.request_cancel(requested.job_id)
        finalizing = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        self.queue.begin_completion(
            finalizing.job_id,
            TestResult("LOGIN-001", TestStatus.PASSED, 0.5, "Passed.", ("image.png",)),
        )
        jobs = SQLiteJobQueue(self.database).recover_interrupted()
        self.assertEqual({job.job_id for job in jobs}, {running.job_id, requested.job_id, finalizing.job_id})
        for job in jobs:
            self.assertEqual(job.status, JobStatus.COMPLETED)
            self.assertEqual(job.result.status, TestStatus.ERROR)
        self.assertEqual(self.queue.get(finalizing.job_id).result.evidence_paths, ("image.png",))
        self.assertIsNone(self.queue.claim_next())

    def test_recovery_leaves_pending_and_terminal_jobs_unchanged(self) -> None:
        completed = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        self.queue.complete(completed.job_id, TestResult("LOGIN-001", TestStatus.PASSED, 0, "Passed."))
        pending = self.queue.submit("LOGIN-001")
        cancelled = self.queue.submit("LOGIN-001")
        self.queue.cancel(cancelled.job_id)
        before = self.queue.list_jobs()
        self.assertEqual(self.queue.recover_interrupted(), ())
        self.assertEqual(self.queue.list_jobs(), before)
        self.assertEqual(self.queue.get(pending.job_id).status, JobStatus.QUEUED)

    def test_recovery_is_idempotent(self) -> None:
        self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        self.assertEqual(len(self.queue.recover_interrupted()), 1)
        self.assertEqual(self.queue.recover_interrupted(), ())

    def test_lock_is_released_after_exception(self) -> None:
        with self.assertRaises(RuntimeError):
            with worker_lock(self.database):
                raise RuntimeError("Simulated interruption")
        with worker_lock(self.database):
            pass


if __name__ == "__main__":
    unittest.main()
