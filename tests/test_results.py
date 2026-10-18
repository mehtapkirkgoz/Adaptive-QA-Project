"""Tests for execution result validation."""

import unittest

from adaptive_qa.models import TestResult, TestStatus


class TestResultValidationTests(unittest.TestCase):
    def make_result(self, **overrides: object) -> TestResult:
        values = {
            "case_id": "LOGIN-001",
            "status": TestStatus.PASSED,
            "duration_seconds": 0.25,
            "message": "Login form fields are visible.",
        }
        values.update(overrides)
        return TestResult(**values)

    def test_valid_result_is_created(self) -> None:
        result = self.make_result()

        self.assertEqual(result.case_id, "LOGIN-001")
        self.assertEqual(result.status, TestStatus.PASSED)
        self.assertEqual(result.duration_seconds, 0.25)

    def test_required_text_fields_reject_invalid_values(self) -> None:
        for field_name in ("case_id", "message"):
            for value in ("", "   ", None, 123):
                with self.subTest(field=field_name, value=value):
                    with self.assertRaisesRegex(
                        ValueError,
                        f"{field_name} must be a non-empty string",
                    ):
                        self.make_result(**{field_name: value})

    def test_all_status_values_are_accepted(self) -> None:
        for status in TestStatus:
            with self.subTest(status=status):
                result = self.make_result(status=status)

                self.assertEqual(result.status, status)

    def test_status_rejects_plain_strings(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "status must be a TestStatus value",
        ):
            self.make_result(status="passed")

    def test_zero_duration_is_accepted(self) -> None:
        result = self.make_result(duration_seconds=0)

        self.assertEqual(result.duration_seconds, 0)

    def test_duration_rejects_non_numeric_values(self) -> None:
        for value in (True, False, "0.25", None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError,
                    "duration_seconds must be a number",
                ):
                    self.make_result(duration_seconds=value)

    def test_duration_rejects_non_finite_values(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError,
                    "duration_seconds must be finite",
                ):
                    self.make_result(duration_seconds=value)

    def test_duration_rejects_negative_values(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "duration_seconds must not be negative",
        ):
            self.make_result(duration_seconds=-0.1)


if __name__ == "__main__":
    unittest.main()