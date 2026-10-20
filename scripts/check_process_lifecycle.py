"""Exercise real OS process trees, persistent cancellation, and worker locks."""

import argparse
import ctypes
import json
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch

from adaptive_qa.browser_process import run_isolated_sample_test
from adaptive_qa.jobs import JobStatus
from adaptive_qa.local_worker import process_next
from adaptive_qa.models import TestStatus
from adaptive_qa.sqlite_queue import SQLiteJobQueue
from adaptive_qa.storage import save_result
from adaptive_qa.worker_lock import worker_lock


def hidden_options() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def fixture_tree(ready: Path) -> None:
    options = hidden_options() if os.name == "nt" else {"start_new_session": True}
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options,
    )
    ready.write_text(json.dumps([os.getpid(), child.pid]), encoding="utf-8")
    try:
        child.wait(timeout=120)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)


def alive(pid: int) -> bool:
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:
                return False
            raise OSError("Cannot inspect test process state.")
        try:
            status = ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(status)):
                raise OSError("Cannot inspect test process exit code.")
            return status.value == 259
        finally:
            kernel.CloseHandle(handle)
    stat = Path(f"/proc/{pid}/stat")
    try:
        if stat.read_text().rpartition(")")[2].split()[0] == "Z":
            return False
    except FileNotFoundError:
        pass
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


class ProcessLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory(prefix="adaptive-qa-lifecycle-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.ready = self.directory / "ready.json"
        self.database = self.directory / "jobs.sqlite3"
        self.processes = []
        self.addCleanup(self.cleanup_processes)
        original = subprocess.Popen

        def launch(command, **options):
            if "--child-result" in command:
                command = [sys.executable, str(Path(__file__).resolve()),
                           "--fixture-tree", str(self.ready)]
            process = original(command, **options)
            if "--fixture-tree" in command:
                self.processes.append(process)
            return process

        launcher = patch("adaptive_qa.browser_process.subprocess.Popen", side_effect=launch)
        launcher.start()
        self.addCleanup(launcher.stop)

    def cleanup_processes(self) -> None:
        identifiers = json.loads(self.ready.read_text()) if self.ready.exists() else []
        for pid in reversed(identifiers):
            if alive(pid):
                if os.name == "nt":
                    subprocess.run(
                        [str(Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"),
                         "/PID", str(pid), "/T", "/F"], timeout=10,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        check=False, **hidden_options(),
                    )
                else:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)

    def assert_tree_stopped(self) -> None:
        self.assertTrue(self.ready.exists(), "The descendant fixture never started.")
        identifiers = json.loads(self.ready.read_text())
        deadline = time.monotonic() + 3
        while any(alive(pid) for pid in identifiers) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertFalse(any(alive(pid) for pid in identifiers), "A test descendant is still running.")

    def test_total_deadline_stops_parent_and_descendant(self) -> None:
        result = run_isolated_sample_test("LOGIN-001", timeout_seconds=3)
        self.assertEqual(result.status, TestStatus.ERROR)
        self.assertIn("time limit", result.message)
        self.assert_tree_stopped()

    def test_cli_cancellation_stops_tree_and_persists_cancelled_result(self) -> None:
        queue = SQLiteJobQueue(self.database)
        job = queue.submit("LOGIN-001")
        errors = []

        def request() -> None:
            try:
                deadline = time.monotonic() + 10
                while not self.ready.exists():
                    if time.monotonic() > deadline:
                        raise RuntimeError("The cancellation fixture did not start.")
                    time.sleep(0.05)
                command = subprocess.run(
                    [sys.executable, "-m", "adaptive_qa.local_worker", "--database",
                     str(self.database), "cancel", job.job_id],
                    capture_output=True, text=True, timeout=10, check=False, **hidden_options(),
                )
                if command.returncode != 0 or json.loads(command.stdout)["status"] != "cancel_requested":
                    raise RuntimeError("The CLI cancellation request failed.")
            except Exception as error:
                errors.append(error)

        requester = Thread(target=request, daemon=True)
        requester.start()
        try:
            with patch("adaptive_qa.local_worker.save_result", side_effect=lambda result, job_id:
                       save_result(result, self.directory / "results", job_id=job_id)):
                processed = process_next(queue)
        finally:
            requester.join(timeout=15)
        self.assertFalse(requester.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(processed.job.status, JobStatus.CANCELLED)
        self.assertEqual(queue.get(job.job_id).result.status, TestStatus.CANCELLED)
        payload = json.loads(processed.result_path.read_text())
        self.assertEqual(payload["result"]["status"], "cancelled")
        self.assert_tree_stopped()

    def test_abrupt_lock_owner_exit_allows_explicit_recovery(self) -> None:
        queue = SQLiteJobQueue(self.database)
        job = queue.submit("LOGIN-001")
        marker = self.directory / "lock-ready"
        owner = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--fixture-lock",
             str(self.database), "--ready", str(marker)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **hidden_options(),
        )
        try:
            deadline = time.monotonic() + 10
            while not marker.exists():
                if time.monotonic() > deadline:
                    self.fail("Lock owner did not start.")
                time.sleep(0.05)
            with self.assertRaises(ValueError):
                queue.recover_interrupted()
            owner.terminate()
            owner.wait(timeout=5)
            recovered = queue.recover_interrupted()
            self.assertEqual(len(recovered), 1)
            self.assertEqual(recovered[0].job_id, job.job_id)
            self.assertEqual(recovered[0].result.status, TestStatus.ERROR)
            self.assertIsNone(queue.claim_next())
        finally:
            if owner.poll() is None:
                owner.kill()
            owner.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify OS process lifecycle behavior.")
    parser.add_argument("--fixture-tree", type=Path)
    parser.add_argument("--fixture-lock", type=Path)
    parser.add_argument("--ready", type=Path)
    args = parser.parse_args()
    if args.fixture_tree is not None:
        fixture_tree(args.fixture_tree)
        return 0
    if args.fixture_lock is not None:
        if args.ready is None:
            parser.error("--ready is required with --fixture-lock")
        with worker_lock(args.fixture_lock):
            SQLiteJobQueue(args.fixture_lock).claim_next()
            args.ready.touch()
            time.sleep(120)
        return 0
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProcessLifecycleTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"platform": sys.platform, "checks": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "passed": result.wasSuccessful()}
    output = Path(__file__).resolve().parents[1] / "artifacts/processes/report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
