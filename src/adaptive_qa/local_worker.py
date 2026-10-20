"""Execute claimed jobs locally; no durable or distributed dispatch yet."""

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from adaptive_qa.jobs import Job, LocalJobQueue
from adaptive_qa.local_browser import run_login_form_test
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.storage import save_result


@dataclass(frozen=True)
class ProcessedJob:
    job: Job
    result_path: Path | None


def process_next(queue: LocalJobQueue) -> ProcessedJob | None:
    """Execute at most one pending job and persist its correlated result."""
    job = queue.claim_next()
    if job is None:
        return None

    started_at = perf_counter()
    try:
        if job.case_id != "LOGIN-001":
            result = TestResult(
                job.case_id, TestStatus.BLOCKED, 0.0,
                "No local executor is registered for this test case.",
            )
        else:
            result = run_login_form_test()
        if not isinstance(result, TestResult) or result.case_id != job.case_id:
            raise ValueError("Executor returned an invalid result.")
    except Exception:
        result = TestResult(
            job.case_id, TestStatus.ERROR, perf_counter() - started_at,
            "The local executor failed unexpectedly.",
        )

    try:
        result_path = save_result(result, job_id=job.job_id)
    except (OSError, ValueError, TypeError):
        result_path = None
        result = TestResult(
            job.case_id, TestStatus.ERROR, perf_counter() - started_at,
            "The execution result could not be persisted.",
            evidence_paths=result.evidence_paths,
        )

    return ProcessedJob(queue.complete(job.job_id, result), result_path)


def main() -> int:
    queue = LocalJobQueue()
    submitted = queue.submit("LOGIN-001")
    print(f"Job queued: {submitted.job_id}")
    processed = process_next(queue)
    if processed is None:
        return 1
    print(processed.job.result)
    if processed.result_path is not None:
        print(f"Result saved to: {processed.result_path}")
    else:
        print("Result was not saved.")
    return 0 if processed.job.result.status == TestStatus.PASSED else 1


if __name__ == "__main__":
    raise SystemExit(main())
