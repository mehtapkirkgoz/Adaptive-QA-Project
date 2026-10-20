"""Transactional SQLite queue for local development on one machine."""

import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from adaptive_qa.jobs import Job, JobStatus
from adaptive_qa.models import TestResult, TestStatus


class SQLiteJobQueue:
    """Persist job snapshots; interrupted running jobs are not auto-retried."""

    def __init__(self, database: Path) -> None:
        self.database = database.resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS jobs ("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
                "job_id TEXT NOT NULL UNIQUE, case_id TEXT NOT NULL, "
                "status TEXT NOT NULL, result_json TEXT)"
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(jobs)")
            }
            if "retry_of" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN retry_of TEXT")

    @contextmanager
    def _transaction(self):
        with closing(sqlite3.connect(self.database, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                yield connection

    @staticmethod
    def _read(connection: sqlite3.Connection, job_id: str) -> Job:
        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        result = None
        if row["result_json"] is not None:
            data = json.loads(row["result_json"])
            data["status"] = TestStatus(data["status"])
            data["evidence_paths"] = tuple(data.get("evidence_paths", ()))
            result = TestResult(**data)
        return Job(
            row["job_id"], row["case_id"], JobStatus(row["status"]), result,
            retry_of=row["retry_of"],
        )

    def submit(self, case_id: str) -> Job:
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_id must be a non-empty string.")
        job = Job(job_id=uuid4().hex, case_id=case_id)
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO jobs (job_id, case_id, status) VALUES (?, ?, ?)",
                (job.job_id, job.case_id, job.status),
            )
        return job

    def retry(self, job_id: str) -> Job:
        """Explicitly create a new attempt while preserving the failed attempt."""
        with self._transaction() as connection:
            previous = self._read(connection, job_id)
            if (
                previous.status != JobStatus.COMPLETED
                or previous.result is None
                or previous.result.status not in (TestStatus.FAILED, TestStatus.ERROR)
            ):
                raise ValueError("Only completed failed or error jobs can be retried.")
            job = Job(job_id=uuid4().hex, case_id=previous.case_id, retry_of=job_id)
            connection.execute(
                "INSERT INTO jobs (job_id, case_id, status, retry_of) VALUES (?, ?, ?, ?)",
                (job.job_id, job.case_id, job.status, job.retry_of),
            )
            return job

    def get(self, job_id: str) -> Job:
        with self._transaction() as connection:
            return self._read(connection, job_id)

    def list_jobs(
        self, *, status: JobStatus | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[Job, ...]:
        """Read bounded history in submission order without changing job state."""
        if status is not None and not isinstance(status, JobStatus):
            raise ValueError("status must be a JobStatus value when provided.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer from 1 to 500.")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer.")
        with self._transaction() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT job_id FROM jobs ORDER BY sequence LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT job_id FROM jobs WHERE status = ? "
                    "ORDER BY sequence LIMIT ? OFFSET ?",
                    (status, limit, offset),
                ).fetchall()
            return tuple(self._read(connection, row["job_id"]) for row in rows)

    def claim_next(self) -> Job | None:
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT job_id FROM jobs WHERE status = ? ORDER BY sequence LIMIT 1",
                (JobStatus.QUEUED,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE jobs SET status = ? WHERE job_id = ?",
                (JobStatus.RUNNING, row["job_id"]),
            )
            return self._read(connection, row["job_id"])

    def cancel(self, job_id: str) -> Job:
        with self._transaction() as connection:
            job = self._read(connection, job_id)
            if job.status == JobStatus.CANCELLED:
                return job
            if job.status != JobStatus.QUEUED:
                raise ValueError("Only queued jobs can be cancelled locally.")
            connection.execute(
                "UPDATE jobs SET status = ? WHERE job_id = ?",
                (JobStatus.CANCELLED, job_id),
            )
            return self._read(connection, job_id)

    def complete(self, job_id: str, result: TestResult) -> Job:
        if not isinstance(result, TestResult):
            raise ValueError("result must be a TestResult instance.")
        with self._transaction() as connection:
            job = self._read(connection, job_id)
            if job.status != JobStatus.RUNNING:
                raise ValueError("Only running jobs can be completed.")
            if result.case_id != job.case_id:
                raise ValueError("Result case_id must match the job.")
            connection.execute(
                "UPDATE jobs SET status = ?, result_json = ? WHERE job_id = ?",
                (JobStatus.COMPLETED, json.dumps(asdict(result), allow_nan=False), job_id),
            )
            return self._read(connection, job_id)
