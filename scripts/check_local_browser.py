"""Run the local browser check with an automatically managed sample server."""

import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread


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
            completed = subprocess.run(
                [sys.executable, "-m", "adaptive_qa.local_browser"],
                cwd=root,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print("Local browser check exceeded 60 seconds.", file=sys.stderr)
            return 1
        return completed.returncode
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
