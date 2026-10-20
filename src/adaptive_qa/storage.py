"""Persist test results as individual JSON files."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from adaptive_qa.models import TestResult


def save_result(
    result: TestResult,
    directory: Path = Path("artifacts/results"),
    *,
    job_id: str | None = None,
) -> Path:
    """Save a test result and return its file path."""
    if not isinstance(result, TestResult):
        raise ValueError("result must be a TestResult instance.")

    if job_id is not None and (not isinstance(job_id, str) or not job_id.strip()):
        raise ValueError("job_id must be a non-empty string when provided.")

    directory.mkdir(parents=True, exist_ok=True)

    result_id = uuid4().hex
    destination = directory / f"{result_id}.json"

    payload = {
        "schema_version": 1,
        "result_id": result_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "result": asdict(result),
    }

    if job_id is not None:
        payload["job_id"] = job_id

    with destination.open("x", encoding="utf-8") as output:
        json.dump(
            payload,
            output,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        output.write("\n")

    return destination