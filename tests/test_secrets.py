"""Tests for environment-based secret references."""

import os
import unittest
from unittest.mock import patch

from adaptive_qa.secrets import SecretReference


class SecretReferenceTests(unittest.TestCase):
    def test_secret_is_resolved_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {"QA_TEST_SECRET": "example-secret"},
            clear=True,
        ):
            secret = SecretReference("QA_TEST_SECRET").resolve()

            self.assertEqual(secret.value, "example-secret")

    def test_secret_output_is_masked(self) -> None:
        with patch.dict(
            os.environ,
            {"QA_TEST_SECRET": "example-secret"},
            clear=True,
        ):
            secret = SecretReference("QA_TEST_SECRET").resolve()

            self.assertEqual(str(secret), "[REDACTED]")
            self.assertNotIn("example-secret", repr(secret))

    def test_missing_secret_is_rejected(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                ValueError,
                "Required secret is missing: QA_TEST_SECRET",
            ):
                SecretReference("QA_TEST_SECRET").resolve()

    def test_blank_secret_is_rejected(self) -> None:
        for value in ("", "   "):
            with self.subTest(value=value):
                with patch.dict(
                    os.environ,
                    {"QA_TEST_SECRET": value},
                    clear=True,
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "Required secret is missing: QA_TEST_SECRET",
                    ):
                        SecretReference("QA_TEST_SECRET").resolve()

    def test_invalid_variable_names_are_rejected(self) -> None:
        for name in ("", "lowercase", "QA-SECRET", "1_SECRET", "QA SECRET"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    ValueError,
                    "environment_variable must be a valid uppercase variable name",
                ):
                    SecretReference(name)

    def test_non_string_variable_name_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "environment_variable must be a string",
        ):
            SecretReference(None)

    def test_secret_whitespace_is_preserved(self) -> None:
        with patch.dict(
            os.environ,
            {"QA_TEST_SECRET": " example-secret "},
            clear=True,
        ):
            secret = SecretReference("QA_TEST_SECRET").resolve()

            self.assertEqual(secret.value, " example-secret ")


if __name__ == "__main__":
    unittest.main()