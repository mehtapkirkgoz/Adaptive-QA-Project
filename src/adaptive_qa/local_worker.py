"""Execute local jobs through a persistent SQLite queue."""

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

from adaptive_qa.jobs import Job, JobStatus, LocalJobQueue
from adaptive_qa.local_browser import run_login_form_test
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.storage import save_result
from adaptive_qa.sqlite_queue import SQLiteJobQueue


@dataclass(frozen=True)
class ProcessedJob:
    job: Job
    result_path: Path | None


def process_next(queue: LocalJobQueue | SQLiteJobQueue) -> ProcessedJob | None:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage local SQLite browser jobs.")
    parser.add_argument(
        "--database", type=Path, default=Path("artifacts/jobs.sqlite3"),
        help="Local SQLite queue file (default: artifacts/jobs.sqlite3)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    submit = commands.add_parser("submit", help="Queue a test case without executing it")
    submit.add_argument("case_id")
    commands.add_parser("run-next", help="Execute at most one queued job")
    listing = commands.add_parser("list", help="List persisted jobs in submission order")
    listing.add_argument("--status", type=JobStatus, choices=list(JobStatus))
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--offset", type=int, default=0)
    for name in ("status", "cancel", "retry"):
        command = commands.add_parser(name)
        command.add_argument("job_id")
    args = parser.parse_args(argv)

    try:
        queue = SQLiteJobQueue(args.database)
        if args.command == "submit":
            print(json.dumps(asdict(queue.submit(args.case_id))))
        elif args.command == "list":
            jobs = queue.list_jobs(status=args.status, limit=args.limit, offset=args.offset)
            print(json.dumps([asdict(job) for job in jobs]))
        elif args.command == "status":
            print(json.dumps(asdict(queue.get(args.job_id))))
        elif args.command == "retry":
            print(json.dumps(asdict(queue.retry(args.job_id))))
        elif args.command == "cancel":
            print(json.dumps(asdict(queue.cancel(args.job_id))))
        else:
            processed = process_next(queue)
            if processed is None:
                print("No queued jobs available.")
                return 0
            print(json.dumps(asdict(processed.job)))
            if processed.result_path is not None:
                print(f"Result saved to: {processed.result_path}")
            else:
                print("Result was not saved.")
            return 0 if processed.job.result.status == TestStatus.PASSED else 1
    except KeyError:
        print("Job was not found in this database.", file=sys.stderr)
        return 1
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, sqlite3.Error):
        print("Local queue or result storage is unavailable.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
