"""Tests for JSON result persistence."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.storage import save_result


class ResultStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = TestResult(
            case_id="LOGIN-001",
            status=TestStatus.PASSED,
            duration_seconds=0.25,
            message="Login form checks passed.",
            evidence_paths=("artifacts/screenshots/example.png",),
        )

    def test_result_is_saved_as_json(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "results"
            path = save_result(self.result, directory)

            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["result"]["evidence_paths"], ["artifacts/screenshots/example.png"])
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["result_id"], path.stem)
            self.assertIn("recorded_at", payload)
            self.assertEqual(payload["result"]["case_id"], "LOGIN-001")
            self.assertEqual(payload["result"]["status"], "passed")
            self.assertEqual(payload["result"]["duration_seconds"], 0.25)
            self.assertEqual(
                payload["result"]["message"],
                "Login form checks passed.",
            )

    def test_repeated_saves_create_separate_files(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)

            first = save_result(self.result, directory)
            second = save_result(self.result, directory)

            self.assertNotEqual(first, second)
            self.assertTrue(first.is_file())
            self.assertTrue(second.is_file())

    def test_invalid_result_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                ValueError,
                "result must be a TestResult instance",
            ):
                save_result(None, Path(temporary))

    def test_job_identifier_is_persisted(self) -> None:
        with TemporaryDirectory() as temporary:
            path = save_result(self.result, Path(temporary), job_id="job-123")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["job_id"], "job-123")

    def test_invalid_job_identifier_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            for job_id in ("", "   ", 123):
                with self.subTest(job_id=job_id):
                    with self.assertRaises(ValueError):
                        save_result(self.result, Path(temporary), job_id=job_id)


if __name__ == "__main__":
    unittest.main()