"""Ephemeral test data and cleanup for registered local fixtures only."""

from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlsplit

from playwright.sync_api import Error

from adaptive_qa.ui_bindings import SITE_PATHS


@dataclass(frozen=True)
class SampleData:
    username: str = 'demo-user'
    password: str = 'fake-demo-password'
    email: str = 'qa@example.test'
    search_query: str = 'sample book'


class FixtureCleanupError(RuntimeError):
    pass


def _reset(page):
    page.evaluate("""() => {
        for (const form of document.forms) form.reset();
        for (const status of document.querySelectorAll('[role="status"]')) status.textContent = '';
        localStorage.clear(); sessionStorage.clear();
    }""")
    page.context.clear_cookies()


@contextmanager
def sample_test_data(page):
    """Prepare/clean browser-local state; never perform backend deletion or writes.

    Cleanup failure invalidates the run even if the assertion itself passed.
    Browser context/process teardown remains mandatory after this scope.
    """
    parsed = urlsplit(page.url)
    if parsed.scheme != 'http' or parsed.netloc != '127.0.0.1:8000' or parsed.path not in SITE_PATHS.values():
        raise ValueError('Sample data may only be used on registered controlled fixtures.')
    _reset(page)
    try:
        yield SampleData()
    finally:
        try:
            _reset(page)
        except Error as error:
            raise FixtureCleanupError('Controlled fixture cleanup failed; browser teardown is required.') from error
