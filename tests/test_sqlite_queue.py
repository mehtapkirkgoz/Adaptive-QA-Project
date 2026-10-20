"""Tests for persistence and transactional SQLite job claims."""

import sqlite3
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

    def test_list_returns_empty_history(self) -> None:
        self.assertEqual(self.queue.list_jobs(), ())

    def test_list_survives_reopen_and_preserves_order(self) -> None:
        jobs = [self.queue.submit("LOGIN-001") for _ in range(3)]
        reopened = SQLiteJobQueue(self.database)
        self.assertEqual(reopened.list_jobs(), tuple(jobs))

    def test_list_filters_without_claiming_jobs(self) -> None:
        running = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        pending = self.queue.submit("LOGIN-001")
        self.assertEqual(
            [job.job_id for job in self.queue.list_jobs(status=JobStatus.RUNNING)],
            [running.job_id],
        )
        self.assertEqual(self.queue.get(pending.job_id).status, JobStatus.QUEUED)

    def test_list_pagination_has_no_duplicates(self) -> None:
        jobs = [self.queue.submit("LOGIN-001") for _ in range(4)]
        first = self.queue.list_jobs(limit=2)
        second = self.queue.list_jobs(limit=2, offset=2)
        self.assertEqual(first + second, tuple(jobs))

    def test_invalid_list_parameters_are_rejected(self) -> None:
        parameters = (
            {"limit": 0}, {"limit": 501}, {"limit": True},
            {"offset": -1}, {"offset": False}, {"status": "running"},
        )
        for values in parameters:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    self.queue.list_jobs(**values)

    def test_retry_preserves_original_and_links_new_attempt(self) -> None:
        for status in (TestStatus.FAILED, TestStatus.ERROR):
            with self.subTest(status=status):
                original = self.queue.submit("LOGIN-001")
                self.queue.claim_next()
                result = TestResult("LOGIN-001", status, 0.1, "Original outcome.")
                completed = self.queue.complete(original.job_id, result)
                retry = self.queue.retry(original.job_id)
                self.assertNotEqual(retry.job_id, original.job_id)
                self.assertEqual(retry.status, JobStatus.QUEUED)
                self.assertIsNone(retry.result)
                reopened = SQLiteJobQueue(self.database)
                self.assertEqual(reopened.get(retry.job_id).retry_of, original.job_id)
                self.assertEqual(reopened.get(original.job_id), completed)
                self.assertEqual(reopened.claim_next().job_id, retry.job_id)
                reopened.complete(retry.job_id, result)

    def test_retry_rejects_pending_running_and_cancelled_jobs(self) -> None:
        job = self.queue.submit("LOGIN-001")
        with self.assertRaises(ValueError):
            self.queue.retry(job.job_id)
        self.queue.cancel(job.job_id)
        with self.assertRaises(ValueError):
            self.queue.retry(job.job_id)
        running = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        with self.assertRaises(ValueError):
            self.queue.retry(running.job_id)

    def test_retry_rejects_successful_and_non_executed_results(self) -> None:
        for status in (TestStatus.PASSED, TestStatus.SKIPPED, TestStatus.BLOCKED):
            with self.subTest(status=status):
                job = self.queue.submit("LOGIN-001")
                self.queue.claim_next()
                self.queue.complete(job.job_id, TestResult("LOGIN-001", status, 0, "Outcome."))
                with self.assertRaises(ValueError):
                    self.queue.retry(job.job_id)

    def test_old_schema_is_migrated_without_losing_jobs(self) -> None:
        old_database = self.database.with_name("old.sqlite3")
        with sqlite3.connect(old_database) as connection:
            connection.execute(
                "CREATE TABLE jobs (sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
                "job_id TEXT NOT NULL UNIQUE, case_id TEXT NOT NULL, "
                "status TEXT NOT NULL, result_json TEXT)"
            )
            connection.execute(
                "INSERT INTO jobs (job_id, case_id, status) VALUES (?, ?, ?)",
                ("old-job", "LOGIN-001", "queued"),
            )
        connection.close()
        reopened = SQLiteJobQueue(old_database)
        self.assertIsNone(reopened.get("old-job").retry_of)
        self.assertEqual(reopened.claim_next().job_id, "old-job")

    def test_running_cancel_request_survives_reopen(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        self.queue.request_cancel(job.job_id)
        reopened = SQLiteJobQueue(self.database)
        self.assertEqual(reopened.get(job.job_id).status, JobStatus.CANCEL_REQUESTED)
        self.assertEqual(reopened.request_cancel(job.job_id).status, JobStatus.CANCEL_REQUESTED)

    def test_cancellation_race_freezes_cancelled_outcome_before_storage(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        self.queue.request_cancel(job.job_id)
        result = TestResult("LOGIN-001", TestStatus.PASSED, 0.1, "Passed.")
        finalizing = self.queue.begin_completion(job.job_id, result)
        self.assertEqual(finalizing.status, JobStatus.FINALIZING)
        self.assertEqual(finalizing.result.status, TestStatus.CANCELLED)
        final = self.queue.complete(job.job_id, finalizing.result)
        self.assertEqual(final.status, JobStatus.CANCELLED)

    def test_finalization_rejects_late_cancellation(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        result = TestResult("LOGIN-001", TestStatus.PASSED, 0.1, "Passed.")
        self.queue.begin_completion(job.job_id, result)
        with self.assertRaisesRegex(ValueError, "finalization"):
            self.queue.request_cancel(job.job_id)
        self.assertEqual(self.queue.complete(job.job_id, result).result, result)

    def test_execution_error_is_not_hidden_by_cancel_request(self) -> None:
        job = self.queue.submit("LOGIN-001")
        self.queue.claim_next()
        self.queue.request_cancel(job.job_id)
        result = TestResult("LOGIN-001", TestStatus.ERROR, 0.1, "Termination failed.")
        prepared = self.queue.begin_completion(job.job_id, result)
        self.assertEqual(prepared.result.status, TestStatus.ERROR)


if __name__ == "__main__":
    unittest.main()
