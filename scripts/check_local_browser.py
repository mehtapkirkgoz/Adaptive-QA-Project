"""Run the local browser check with an automatically managed sample server."""

import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from tempfile import TemporaryDirectory

from adaptive_qa.catalog import TEST_CASES


def main() -> int:
    root = Path(__file__).resolve().parents[1]
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
