"""Read-only login/search form checks independent of sample URLs and test IDs."""

from contextlib import ExitStack, contextmanager

from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy, MatchStatus, ProjectElementMappings
from adaptive_qa.element_matching import match_element
from adaptive_qa.ui_bindings import ElementBindingError


def _labels(key, *names):
    return ElementMapping(key, tuple(LocatorSpec(LocatorStrategy.LABEL, name) for name in names))


def _buttons(key, *names):
    return ElementMapping(key, tuple(LocatorSpec(LocatorStrategy.ROLE, name, 'button') for name in names))


FORM_DEFAULTS = {
    'login.username': _labels('login.username', 'Username', 'Email', 'Email address', 'Kullanıcı adı', 'E-posta'),
    'login.password': _labels('login.password', 'Password', 'Şifre', 'Parola'),
    'login.submit': _buttons('login.submit', 'Sign in', 'Log in', 'Login', 'Giriş yap', 'Oturum aç'),
    'search.query': _labels('search.query', 'Search', 'Search products', 'Search query', 'Ara', 'Ürün ara'),
    'search.submit': _buttons('search.submit', 'Search', 'Ara', 'Find'),
}


@contextmanager
def _controls(page, keys, *, project_id, mappings):
    if mappings is not None and not isinstance(mappings, ProjectElementMappings):
        raise ValueError('Typed project mappings are required.')
    with ExitStack() as stack:
        handles = {}
        anchor = 'login.password' if 'login.password' in keys else keys[0]
        order = (anchor,) + tuple(key for key in keys if key != anchor)
        form = None
        for key in order:
            mapping = FORM_DEFAULTS[key]
            if mappings is not None:
                mapping = mappings.resolve(mapping, project_id=project_id)
            bound = match_element(page, mapping, within_form=form)
            stack.callback(bound.close)
            if bound.result.status != MatchStatus.MATCHED:
                raise ElementBindingError(bound.result)
            handles[key] = bound.handle
            if key == anchor:
                form_handle = bound.handle.evaluate_handle('el => el.form')
                stack.callback(form_handle.dispose)
                form = form_handle.as_element()
                assert form is not None, 'The bound input must belong to a connected form.'
        ordered = [handles[key] for key in keys]
        # Avoid combining unrelated sign-up/login/search controls from distinct forms.
        assert page.evaluate('''elements => elements.every(el => el.isConnected && el.form) &&
            elements.every(el => el.form === elements[0].form)''', ordered), 'Controls must belong to one connected form.'
        yield ordered


def check_login_form(page, *, project_id=None, mappings=None):
    with _controls(page, ('login.username', 'login.password', 'login.submit'),
                   project_id=project_id, mappings=mappings) as (username, password, submit):
        assert username.evaluate("el => el.tagName === 'INPUT' && ['text', 'email'].includes(el.type)"), 'A username input is required.'
        assert password.evaluate("el => el.tagName === 'INPUT' && el.type === 'password'"), 'A masked password input is required.'
        assert submit.evaluate("el => ['BUTTON', 'INPUT'].includes(el.tagName) && el.type === 'submit'"), 'A submit control is required.'
        assert username.is_enabled() and password.is_enabled() and submit.is_enabled(), 'Login controls must be enabled.'


def check_search_form(page, *, project_id=None, mappings=None):
    with _controls(page, ('search.query', 'search.submit'),
                   project_id=project_id, mappings=mappings) as (query, submit):
        assert query.evaluate("el => el.tagName === 'INPUT' && ['text', 'search'].includes(el.type)"), 'A search input is required.'
        assert submit.evaluate("el => ['BUTTON', 'INPUT'].includes(el.tagName) && el.type === 'submit'"), 'A submit control is required.'
        assert query.is_enabled() and submit.is_enabled(), 'Search controls must be enabled.'


FORM_CHECKS = {'LOGIN-001': check_login_form, 'SEARCH-001': check_search_form}

# Existing catalog IDs gain a reusable, non-submitting browser validity contract.
from adaptive_qa.native_form_checks import NATIVE_FORM_CHECKS
FORM_CHECKS.update(NATIVE_FORM_CHECKS)
