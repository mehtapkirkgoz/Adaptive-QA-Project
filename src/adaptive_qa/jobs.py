"""In-memory job lifecycle for local development, not production dispatch."""

from collections import deque
from dataclasses import dataclass, replace
from enum import StrEnum
from threading import Lock
from uuid import uuid4

from adaptive_qa.models import TestResult


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Job:
    job_id: str
    case_id: str
    status: JobStatus = JobStatus.QUEUED
    result: TestResult | None = None
    retry_of: str | None = None


class LocalJobQueue:
    """Coordinate local jobs within one process using immutable snapshots."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._pending: deque[str] = deque()
        self._lock = Lock()

    def submit(self, case_id: str) -> Job:
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_id must be a non-empty string.")
        job = Job(job_id=uuid4().hex, case_id=case_id)
        with self._lock:
            self._jobs[job.job_id] = job
            self._pending.append(job.job_id)
        return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            return self._jobs[job_id]

    def claim_next(self) -> Job | None:
        with self._lock:
            while self._pending:
                job_id = self._pending.popleft()
                job = self._jobs[job_id]
                if job.status == JobStatus.CANCELLED:
                    continue
                running = replace(job, status=JobStatus.RUNNING)
                self._jobs[job_id] = running
                return running
        return None

    def cancel(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs[job_id]
            if job.status == JobStatus.CANCELLED:
                return job
            if job.status != JobStatus.QUEUED:
                raise ValueError("Only queued jobs can be cancelled locally.")
            cancelled = replace(job, status=JobStatus.CANCELLED)
            self._jobs[job_id] = cancelled
            return cancelled

    def complete(self, job_id: str, result: TestResult) -> Job:
        if not isinstance(result, TestResult):
            raise ValueError("result must be a TestResult instance.")
        with self._lock:
            job = self._jobs[job_id]
            if job.status != JobStatus.RUNNING:
                raise ValueError("Only running jobs can be completed.")
            if result.case_id != job.case_id:
                raise ValueError("Result case_id must match the job.")
            completed = replace(job, status=JobStatus.COMPLETED, result=result)
            self._jobs[job_id] = completed
            return completed
