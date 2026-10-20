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

SEARCH_FORM_VISIBLE = TestCase(
    case_id="SEARCH-001",
    name="Search form is available",
    test_type=TestType.UI,
    required_features=("search",),
    steps=("Open the sample page", "Locate the search field and submit button"),
    expected_result="The search field is visible and the Search button is enabled.",
)

SEARCH_NO_RESULTS = TestCase(
    case_id="SEARCH-002",
    name="Search displays the no-results message",
    test_type=TestType.UI,
    required_features=("search",),
    steps=("Open the sample page", "Search for sample book", "Read the result message"),
    expected_result='The status message is: No products found for "sample book".',
)

TEST_CASES: tuple[TestCase, ...] = (
    LOGIN_FORM_VISIBLE,
    SEARCH_FORM_VISIBLE,
    SEARCH_NO_RESULTS,
)
