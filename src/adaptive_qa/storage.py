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
) -> Path:
    """Save a test result and return its file path."""
    if not isinstance(result, TestResult):
        raise ValueError("result must be a TestResult instance.")

    directory.mkdir(parents=True, exist_ok=True)

    result_id = uuid4().hex
    destination = directory / f"{result_id}.json"

    payload = {
        "schema_version": 1,
        "result_id": result_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "result": asdict(result),
    }

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