"""Reusable test case definitions."""

from adaptive_qa.models import TestCase, TestType
from adaptive_qa.extra_ui_checks import EXTRA_CASES
from adaptive_qa.document_checks import DOCUMENT_CASES


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

def _sample_case(
    case_id: str, name: str, feature: str, steps: tuple[str, ...], expected: str
) -> TestCase:
    return TestCase(case_id, name, TestType.UI, (feature,), steps, expected)


TEST_CASES: tuple[TestCase, ...] = (
    LOGIN_FORM_VISIBLE,
    _sample_case("LOGIN-002", "Username is required", "login",
                 ("Open the sample page", "Submit an empty login form"),
                 "Username validation blocks submission and no result is displayed."),
    _sample_case("LOGIN-003", "Password is required", "login",
                 ("Enter a demo username", "Submit without a password"),
                 "Password validation blocks submission and no result is displayed."),
    _sample_case("LOGIN-004", "Demo login submission displays its status", "login",
                 ("Fill fake demo credentials", "Submit the login form"),
                 "The demo-only authentication status is displayed without network submission."),
    SEARCH_FORM_VISIBLE,
    SEARCH_NO_RESULTS,
    _sample_case("SEARCH-003", "Search query is required", "search",
                 ("Open the sample page", "Submit an empty search form"),
                 "Query validation blocks submission and no result is displayed."),
    _sample_case("SEARCH-004", "Whitespace search displays a prompt", "search",
                 ("Enter whitespace into search", "Submit the search form"),
                 "The result status asks the user to enter a search term."),
    _sample_case("NAV-001", "Login link navigates to its section", "navigation",
                 ("Open the sample page", "Click the Sign in navigation link"),
                 "The URL ends with #login and the login section is in the viewport."),
    _sample_case("NAV-002", "Search link navigates to its section", "navigation",
                 ("Open the sample page", "Click the Search navigation link"),
                 "The URL ends with #search and the search section is in the viewport."),
)

TEST_CASES += EXTRA_CASES
TEST_CASES += DOCUMENT_CASES
