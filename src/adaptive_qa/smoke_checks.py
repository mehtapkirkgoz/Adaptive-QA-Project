"""Explicit browser assertions for the controlled sample application."""

from collections.abc import Callable

from playwright.sync_api import Page, expect


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


SMOKE_CHECKS: dict[str, Callable[[Page], None]] = {
    "LOGIN-001": check_login_form,
    "SEARCH-001": check_search_form,
    "SEARCH-002": check_search_result,
}
