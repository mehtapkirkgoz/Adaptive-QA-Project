"""Explicit bindings for controlled local fixture variants."""

from contextlib import contextmanager
from urllib.parse import urlsplit

from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy, MatchStatus, ProjectElementMappings
from adaptive_qa.element_matching import match_element


SITE_PATHS = {'root': '/', 'english': '/variants/english.html',
              'turkish': '/variants/turkish.html', 'mapped': '/variants/mapped.html'}


def _labels(key, scope, *names):
    return ElementMapping(key, tuple(LocatorSpec(LocatorStrategy.LABEL, name) for name in names), scope)


def _buttons(key, scope, *names):
    return ElementMapping(key, tuple(LocatorSpec(LocatorStrategy.ROLE, name, 'button') for name in names), scope)


DEFAULTS = {
    'login.username': _labels('login.username', 'login-form', 'Username', 'Kullanıcı adı'),
    'login.password': _labels('login.password', 'login-form', 'Password', 'Şifre'),
    'login.submit': _buttons('login.submit', 'login-form', 'Sign in', 'Giriş yap'),
    'search.query': _labels('search.query', 'search-form', 'Search products', 'Ürün ara'),
    'search.submit': _buttons('search.submit', 'search-form', 'Search', 'Ara'),
}
for key, scope, identifier in (
    ('login.reset', 'login-form', 'login-reset'), ('login.toggle', 'login-form', 'login-toggle'),
    ('search.reset', 'search-form', 'search-reset'),
    *tuple(('forms.' + name, 'controls-form', 'control-' + name) for name in
           ('email', 'terms', 'standard', 'express', 'country', 'notes', 'quantity',
            'disabled', 'readonly', 'submit', 'reset')),
    ('navigation.login', 'navigation', 'nav-login'), ('navigation.search', 'navigation', 'nav-search'),
):
    DEFAULTS[key] = ElementMapping(key, (LocatorSpec(LocatorStrategy.TEST_ID, identifier),), scope)
OVERRIDES = ProjectElementMappings('local-demo', tuple(
    ElementMapping(key, (LocatorSpec(LocatorStrategy.TEST_ID, 'mapped-' + key.replace('.', '-')),),
                   mapping.scope_test_id) for key, mapping in DEFAULTS.items()))


class ElementBindingError(RuntimeError):
    def __init__(self, result):
        super().__init__(result.reason)
        self.result = result


@contextmanager
def control(page, key):
    parsed = urlsplit(page.url)
    if parsed.scheme != 'http' or parsed.netloc != '127.0.0.1:8000' or parsed.path not in SITE_PATHS.values():
        raise RuntimeError('No controlled fixture binding exists for this page.')
    mapping = DEFAULTS[key]
    if parsed.path == SITE_PATHS['mapped']:
        mapping = OVERRIDES.resolve(mapping, project_id='local-demo')
    bound = match_element(page, mapping)
    try:
        if bound.result.status != MatchStatus.MATCHED:
            raise ElementBindingError(bound.result)
        if not bound.handle.evaluate('el => el.isConnected'):
            raise RuntimeError('Bound element was detached.')
        yield bound.handle
    finally:
        bound.close()


def check_login_form(page):
    with control(page, 'login.username') as username, control(page, 'login.password') as password, control(page, 'login.submit') as submit:
        assert username.is_visible() and password.is_visible() and submit.is_visible()
        assert password.get_attribute('type') == 'password'


def check_search_form(page):
    with control(page, 'search.query') as query, control(page, 'search.submit') as submit:
        assert query.is_visible() and submit.is_enabled()


REUSABLE_CHECKS = {'LOGIN-001': check_login_form, 'SEARCH-001': check_search_form}
