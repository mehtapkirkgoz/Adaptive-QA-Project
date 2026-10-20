"""Bound local browser execution with an isolated child process."""

import argparse
import json
import math
import os
import signal
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from adaptive_qa.local_browser import run_sample_test
from adaptive_qa.smoke_checks import SMOKE_CHECKS
from adaptive_qa.models import TestResult, TestStatus


def _terminate_process_tree(process: subprocess.Popen) -> None:
    """Stop the child and its browser descendants after a timeout."""
    if os.name == "nt":
        taskkill = Path(os.environ["SystemRoot"]) / "System32" / "taskkill.exe"
        stopped = subprocess.run(
            [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=10, check=False,
        )
        if stopped.returncode != 0 and process.poll() is None:
            raise RuntimeError("Browser process tree termination failed.")
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=5)


def _read_result(path: Path, expected_case_id: str = "LOGIN-001") -> TestResult:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = TestStatus(payload["status"])
    payload["evidence_paths"] = tuple(payload.get("evidence_paths", ()))
    result = TestResult(**payload)
    if result.case_id != expected_case_id:
        raise ValueError("Unexpected browser result case identifier.")
    return result


def run_isolated_sample_test(
    case_id: str, timeout_seconds: float = 30, *, should_cancel: Callable[[], bool] | None = None
) -> TestResult:
    """Return a result, terminating the child tree if its deadline expires."""
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be a positive finite number.")

    if case_id not in SMOKE_CHECKS:
        return TestResult(case_id, TestStatus.BLOCKED, 0.0, "No sample executor is registered.")

    started = perf_counter()
    if should_cancel is not None and should_cancel():
        return TestResult(case_id, TestStatus.CANCELLED, 0.0, "Execution was cancelled.")
    with TemporaryDirectory(prefix="adaptive-qa-browser-") as temporary:
        output = Path(temporary) / "result.json"
        options = {"start_new_session": True} if os.name != "nt" else {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        }
        process = subprocess.Popen(
            [sys.executable, "-m", "adaptive_qa.browser_process", "--child-result", str(output), "--case", case_id],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options,
        )
        try:
            while True:
                if should_cancel is not None and should_cancel():
                    _terminate_process_tree(process)
                    return TestResult(
                        case_id, TestStatus.CANCELLED, perf_counter() - started,
                        "Browser execution was cancelled by request.",
                    )
                remaining = timeout_seconds - (perf_counter() - started)
                if remaining <= 0:
                    _terminate_process_tree(process)
                    return TestResult(
                        case_id, TestStatus.ERROR, perf_counter() - started,
                        "Browser execution exceeded its total time limit.",
                    )
                try:
                    process.wait(timeout=min(0.2, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode != 0:
                return TestResult(
                    case_id, TestStatus.ERROR, perf_counter() - started,
                    "The isolated browser process exited unexpectedly.",
                )
            try:
                return _read_result(output, expected_case_id=case_id)
            except (OSError, ValueError, TypeError, KeyError):
                return TestResult(
                    case_id, TestStatus.ERROR, perf_counter() - started,
                    "The isolated browser process returned an invalid result.",
                )
        finally:
            if process.poll() is None:
                _terminate_process_tree(process)


def run_isolated_login_test(
    timeout_seconds: float = 30, *, should_cancel: Callable[[], bool] | None = None
) -> TestResult:
    """Compatibility wrapper for the original isolated login check."""
    return run_isolated_sample_test(
        "LOGIN-001", timeout_seconds, should_cancel=should_cancel
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Internal local browser child process.")
    parser.add_argument("--child-result", type=Path, required=True)
    parser.add_argument("--case", choices=sorted(SMOKE_CHECKS), default="LOGIN-001")
    args = parser.parse_args()
    result = run_sample_test(args.case)
    args.child_result.write_text(json.dumps(asdict(result)), encoding="utf-8")


if __name__ == "__main__":
    main()
