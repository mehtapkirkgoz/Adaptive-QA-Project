"""Tests for persistence and transactional SQLite job claims."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from adaptive_qa.jobs import JobStatus
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.sqlite_queue import SQLiteJobQueue


class SQLiteJobQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / "queue.sqlite3"
        self.queue = SQLiteJobQueue(self.database)

    def test_pending_jobs_survive_reopening_in_fifo_order(self) -> None:
        first = self.queue.submit("LOGIN-001")
        second = self.queue.submit("SEARCH-001")
        reopened = SQLiteJobQueue(self.database)
        self.assertEqual(reopened.claim_next().job_id, first.job_id)
        self.assertEqual(reopened.claim_next().job_id, second.job_id)
        self.assertIsNone(reopened.claim_next())

    def test_cancelled_job_remains_cancelled_after_reopening(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.cancel(job.job_id)
        reopened = SQLiteJobQueue(self.database)
        self.assertEqual(reopened.get(job.job_id).status, JobStatus.CANCELLED)
        self.assertIsNone(reopened.claim_next())

    def test_completed_result_and_evidence_survive_reopening(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        result = TestResult("LOGIN-001", TestStatus.FAILED, 0.2, "Failed.", ("image.png",))
        self.queue.complete(job.job_id, result)
        saved = SQLiteJobQueue(self.database).get(job.job_id)
        self.assertEqual(saved.status, JobStatus.COMPLETED)
        self.assertEqual(saved.result, result)

    def test_concurrent_connections_do_not_claim_the_same_job(self) -> None:
        jobs = [self.queue.submit("LOGIN-001") for _ in range(12)]
        queues = [SQLiteJobQueue(self.database) for _ in range(4)]
        with ThreadPoolExecutor(max_workers=4) as executor:
            claims = list(executor.map(lambda i: queues[i % 4].claim_next(), range(20)))
        identifiers = [job.job_id for job in claims if job is not None]
        self.assertEqual(len(identifiers), len(jobs))
        self.assertEqual(set(identifiers), {job.job_id for job in jobs})

    def test_invalid_transitions_and_result_mismatch_are_rejected(self) -> None:
        job = self.queue.submit("LOGIN-001")
        result = TestResult("OTHER-001", TestStatus.PASSED, 0, "Passed.")
        with self.assertRaisesRegex(ValueError, "Only running jobs"):
            self.queue.complete(job.job_id, result)
        self.queue.claim_next()
        with self.assertRaisesRegex(ValueError, "Result case_id must match"):
            self.queue.complete(job.job_id, result)
        with self.assertRaisesRegex(ValueError, "Only queued jobs"):
            self.queue.cancel(job.job_id)
        self.assertEqual(self.queue.get(job.job_id).status, JobStatus.RUNNING)

    def test_running_jobs_are_not_automatically_replayed(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        reopened = SQLiteJobQueue(self.database)
        self.assertIsNone(reopened.claim_next())
        self.assertEqual(reopened.get(job.job_id).status, JobStatus.RUNNING)

    def test_unknown_jobs_and_blank_case_ids_are_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.queue.get("missing")
        for case_id in (None, "", "   "):
            with self.subTest(case_id=case_id):
                with self.assertRaises(ValueError):
                    self.queue.submit(case_id)


if __name__ == "__main__":
    unittest.main()
