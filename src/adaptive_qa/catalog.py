"""Reusable test case definitions."""

from adaptive_qa.models import TestCase, TestType


LOGIN_FORM_VISIBLE = TestCase(
    case_id="LOGIN-001",
    name="Login form is visible",
    test_type=TestType.UI,
    required_features=("login",),
    steps=(
        "Open the discovered login page",
        "Locate the user identifier field",
        "Locate the password field",
        "Locate the login submit button",
    ),
    expected_result=(
        "The user identifier field, password field, "
        "and login submit button are visible."
    ),
    changes_data=False,
)

TEST_CASES: tuple[TestCase, ...] = (
    LOGIN_FORM_VISIBLE,
)