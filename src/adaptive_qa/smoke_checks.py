"""Explicit browser assertions for the controlled sample application."""

from collections.abc import Callable

from playwright.sync_api import Page, expect
from adaptive_qa.extra_ui_checks import EXTRA_CHECKS
from adaptive_qa.document_checks import DOCUMENT_CHECKS
from adaptive_qa.semantic_checks import SEMANTIC_CHECKS


def check_login_form(page: Page) -> None:
    form = page.locator("#login-form")
    expect(form.get_by_label("Username", exact=True)).to_be_visible()
    password = form.get_by_label("Password", exact=True)
    expect(password).to_be_visible()
    expect(password).to_have_attribute("type", "password")
    expect(form.get_by_role("button", name="Sign in", exact=True)).to_be_visible()


def check_search_form(page: Page) -> None:
    form = page.get_by_role("search")
    expect(form.get_by_label("Search products", exact=True)).to_be_visible()
    expect(form.get_by_role("button", name="Search", exact=True)).to_be_enabled()


def check_search_result(page: Page) -> None:
    form = page.get_by_role("search")
    form.get_by_label("Search products", exact=True).fill("sample book")
    form.get_by_role("button", name="Search", exact=True).click()
    expect(form.get_by_role("status")).to_have_text(
        'No products found for "sample book".'
    )


def check_login_required_username(page: Page) -> None:
    form = page.locator("#login-form")
    form.get_by_role("button", name="Sign in", exact=True).click()
    missing = form.get_by_label("Username", exact=True).evaluate(
        "element => element.validity.valueMissing"
    )
    assert missing, "Empty username must prevent submission."
    expect(form.get_by_role("status")).to_have_text("")


def check_login_required_password(page: Page) -> None:
    form = page.locator("#login-form")
    form.get_by_label("Username", exact=True).fill("demo-user")
    form.get_by_role("button", name="Sign in", exact=True).click()
    missing = form.get_by_label("Password", exact=True).evaluate(
        "element => element.validity.valueMissing"
    )
    assert missing, "Empty password must prevent submission."
    expect(form.get_by_role("status")).to_have_text("")


def check_demo_login_submission(page: Page) -> None:
    form = page.locator("#login-form")
    form.get_by_label("Username", exact=True).fill("demo-user")
    form.get_by_label("Password", exact=True).fill("fake-demo-password")
    form.get_by_role("button", name="Sign in", exact=True).click()
    expect(form.get_by_role("status")).to_have_text(
        "Demo only: authentication is not connected."
    )


def check_search_required_query(page: Page) -> None:
    form = page.get_by_role("search")
    form.get_by_role("button", name="Search", exact=True).click()
    missing = form.get_by_label("Search products", exact=True).evaluate(
        "element => element.validity.valueMissing"
    )
    assert missing, "An empty query must prevent submission."
    expect(form.get_by_role("status")).to_have_text("")


def check_search_whitespace(page: Page) -> None:
    form = page.get_by_role("search")
    form.get_by_label("Search products", exact=True).fill("   ")
    form.get_by_role("button", name="Search", exact=True).click()
    expect(form.get_by_role("status")).to_have_text("Enter a search term.")


def check_login_navigation(page: Page) -> None:
    page.get_by_role("navigation").get_by_role("link", name="Sign in", exact=True).click()
    expect(page).to_have_url("http://127.0.0.1:8000/#login")
    expect(page.locator("#login")).to_be_in_viewport()


def check_search_navigation(page: Page) -> None:
    page.get_by_role("navigation").get_by_role("link", name="Search", exact=True).click()
    expect(page).to_have_url("http://127.0.0.1:8000/#search")
    expect(page.locator("#search")).to_be_in_viewport()


SMOKE_CHECKS: dict[str, Callable[[Page], None]] = {
    "LOGIN-001": check_login_form,
    "LOGIN-002": check_login_required_username,
    "LOGIN-003": check_login_required_password,
    "LOGIN-004": check_demo_login_submission,
    "SEARCH-001": check_search_form,
    "SEARCH-002": check_search_result,
    "SEARCH-003": check_search_required_query,
    "SEARCH-004": check_search_whitespace,
    "NAV-001": check_login_navigation,
    "NAV-002": check_search_navigation,
}
SMOKE_CHECKS.update(EXTRA_CHECKS)
SMOKE_CHECKS.update(DOCUMENT_CHECKS)
SMOKE_CHECKS.update(SEMANTIC_CHECKS)
