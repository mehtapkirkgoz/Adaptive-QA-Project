"""Tests for test case validation."""

import unittest

from adaptive_qa.models import TestCase, TestType


class TestCaseValidationTests(unittest.TestCase):
    def make_case(self, **overrides: object) -> TestCase:
        values = {
            "case_id": "LOGIN-001",
            "name": "Login form is visible",
            "test_type": TestType.UI,
            "required_features": ("login",),
            "steps": ("Open the login page", "Check the form fields"),
            "expected_result": "Username and password fields are visible",
            "changes_data": False,
        }
        values.update(overrides)
        return TestCase(**values)

    def test_valid_case_is_created(self) -> None:
        case = self.make_case()

        self.assertEqual(case.case_id, "LOGIN-001")
        self.assertFalse(case.changes_data)

    def test_required_text_fields_reject_blank_values(self) -> None:
        for field_name in ("case_id", "name", "expected_result"):
            with self.subTest(field=field_name):
                with self.assertRaisesRegex(
                    ValueError,
                    f"{field_name} must be a non-empty string",
                ):
                    self.make_case(**{field_name: "   "})

    def test_steps_cannot_be_empty(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "A test case must contain at least one step",
        ):
            self.make_case(steps=())

    def test_required_features_can_be_empty(self) -> None:
        case = self.make_case(required_features=())

        self.assertEqual(case.required_features, ())

    def test_test_type_rejects_plain_strings(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "test_type must be a TestType value",
        ):
            self.make_case(test_type="ui")

    def test_collections_reject_lists(self) -> None:
        for field_name in ("required_features", "steps"):
            with self.subTest(field=field_name):
                with self.assertRaisesRegex(
                    ValueError,
                    f"{field_name} must be a tuple",
                ):
                    self.make_case(**{field_name: ["example"]})

    def test_collections_reject_blank_items(self) -> None:
        for field_name in ("required_features", "steps"):
            with self.subTest(field=field_name):
                with self.assertRaisesRegex(
                    ValueError,
                    f"{field_name} must contain only non-empty strings",
                ):
                    self.make_case(**{field_name: ("",)})

    def test_changes_data_rejects_non_boolean_values(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "changes_data must be a bool",
        ):
            self.make_case(changes_data="false")


if __name__ == "__main__":
    unittest.main()