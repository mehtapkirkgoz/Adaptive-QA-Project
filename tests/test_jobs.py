"""Tests for local queue ordering, cancellation, and result ownership."""

import unittest
from concurrent.futures import ThreadPoolExecutor

from adaptive_qa.jobs import JobStatus, LocalJobQueue
from adaptive_qa.models import TestResult, TestStatus


class LocalJobQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.queue = LocalJobQueue()

    def test_jobs_are_claimed_in_submission_order(self) -> None:
        first = self.queue.submit("LOGIN-001")
        second = self.queue.submit("SEARCH-001")
        self.assertEqual(self.queue.claim_next().job_id, first.job_id)
        self.assertEqual(self.queue.claim_next().job_id, second.job_id)
        self.assertIsNone(self.queue.claim_next())
        self.assertEqual(first.status, JobStatus.QUEUED)
        self.assertEqual(self.queue.get(first.job_id).status, JobStatus.RUNNING)

    def test_cancelled_jobs_are_skipped(self) -> None:
        first = self.queue.submit("LOGIN-001")
        second = self.queue.submit("SEARCH-001")
        self.queue.cancel(first.job_id)
        self.assertEqual(self.queue.claim_next().job_id, second.job_id)
        self.assertIsNone(self.queue.claim_next())
        self.assertEqual(self.queue.cancel(first.job_id).status, JobStatus.CANCELLED)

    def test_running_job_cannot_be_cancelled_by_pending_cancel(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        with self.assertRaisesRegex(ValueError, "Only queued jobs"):
            self.queue.cancel(job.job_id)

    def test_failed_test_can_complete_a_job(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        result = TestResult("LOGIN-001", TestStatus.FAILED, 0.1, "Check failed.")
        completed = self.queue.complete(job.job_id, result)
        self.assertEqual(completed.status, JobStatus.COMPLETED)
        self.assertEqual(completed.result.status, TestStatus.FAILED)
        with self.assertRaisesRegex(ValueError, "Only running jobs"):
            self.queue.complete(job.job_id, result)

    def test_result_must_belong_to_claimed_job(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        result = TestResult("OTHER-001", TestStatus.PASSED, 0.1, "Passed.")
        with self.assertRaisesRegex(ValueError, "Result case_id must match"):
            self.queue.complete(job.job_id, result)
        self.assertEqual(self.queue.get(job.job_id).status, JobStatus.RUNNING)

    def test_unclaimed_job_cannot_be_completed(self) -> None:
        job = self.queue.submit("LOGIN-001")
        result = TestResult("LOGIN-001", TestStatus.PASSED, 0.1, "Passed.")
        with self.assertRaisesRegex(ValueError, "Only running jobs"):
            self.queue.complete(job.job_id, result)

    def test_concurrent_claims_do_not_duplicate_jobs(self) -> None:
        submitted = [self.queue.submit("LOGIN-001") for _ in range(20)]
        with ThreadPoolExecutor(max_workers=4) as executor:
            claimed = list(executor.map(lambda _: self.queue.claim_next(), range(30)))
        identifiers = [job.job_id for job in claimed if job is not None]
        self.assertEqual(len(identifiers), 20)
        self.assertEqual(set(identifiers), {job.job_id for job in submitted})

    def test_invalid_case_ids_are_rejected(self) -> None:
        for case_id in (None, "", "   "):
            with self.subTest(case_id=case_id):
                with self.assertRaises(ValueError):
                    self.queue.submit(case_id)


if __name__ == "__main__":
    unittest.main()
