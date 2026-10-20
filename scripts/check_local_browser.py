"""Run the local browser check with an automatically managed sample server."""

import json
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from tempfile import TemporaryDirectory

from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.jobs import JobStatus
from adaptive_qa.models import TestStatus
from adaptive_qa.sqlite_queue import SQLiteJobQueue


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    result_directory = root / "artifacts/results"
    previous_results = set(result_directory.glob("*.json"))
    handler = partial(SimpleHTTPRequestHandler, directory=str(root / "samples/web"))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
    except OSError:
        print("Cannot start sample server. Ensure port 8000 is available.", file=sys.stderr)
        return 1

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            with TemporaryDirectory(prefix="adaptive-qa-check-") as temporary:
                command = [
                    sys.executable, "-m", "adaptive_qa.local_worker",
                    "--database", str(Path(temporary) / "jobs.sqlite3"),
                ]
                for case in TEST_CASES:
                    submitted = subprocess.run(
                        command + ["submit", case.case_id],
                        cwd=root, timeout=10, check=False,
                    )
                    if submitted.returncode != 0:
                        return submitted.returncode
                outcome = 0
                for _ in TEST_CASES:
                    completed = subprocess.run(
                        command + ["run-next"],
                        cwd=root, timeout=60, check=False,
                    )
                    if completed.returncode != 0:
                        outcome = 1
                jobs = SQLiteJobQueue(Path(temporary) / "jobs.sqlite3").list_jobs(limit=500)
                saved = {}
                for path in set(result_directory.glob("*.json")) - previous_results:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    saved[payload.get("job_id")] = payload
                if len(jobs) != len(TEST_CASES):
                    raise RuntimeError("Smoke job count does not match the catalog.")
                for job in jobs:
                    if job.status != JobStatus.COMPLETED or job.result is None:
                        raise RuntimeError("A smoke job did not produce a completed result.")
                    if job.job_id not in saved:
                        raise RuntimeError("A smoke job has no JSON evidence record.")
                    if saved[job.job_id]["result"]["status"] != job.result.status:
                        raise RuntimeError("Stored JSON and queue result disagree.")
                    if job.result.status != TestStatus.PASSED:
                        outcome = 1
                    if job.result.status == TestStatus.PASSED and not job.result.evidence_paths:
                        raise RuntimeError("A passed smoke job has no screenshot evidence.")
                    for evidence in job.result.evidence_paths:
                        if not Path(evidence).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                            raise RuntimeError("Screenshot evidence is not a PNG file.")
                report = root / "artifacts/smoke/report.json"
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text(json.dumps({
                    "cases": len(jobs),
                    "passed": sum(job.result.status == TestStatus.PASSED for job in jobs),
                    "results": [{"job_id": job.job_id, "case_id": job.case_id,
                                 "status": job.result.status} for job in jobs],
                }, indent=2) + "\n", encoding="utf-8")
        except subprocess.TimeoutExpired:
            print("Local browser check exceeded 60 seconds.", file=sys.stderr)
            return 1
        return outcome
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
