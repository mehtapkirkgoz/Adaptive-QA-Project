"""Distinct native-control, keyboard, reset, and navigation scenarios."""

from contextlib import ExitStack
from functools import partial

from playwright.sync_api import Error

from adaptive_qa.models import TestCase, TestType
from adaptive_qa.ui_bindings import control
from adaptive_qa.sample_data import SampleData


# Each row is one behavior, not one language or visual variation.
SPECS = (
    ('LOGIN-005', 'Username rejects invalid characters', 'login', 'patternMismatch'),
    ('LOGIN-006', 'Short password blocks submission', 'login', 'tooShort'),
    ('LOGIN-007', 'Enter submits the demo login', 'login', 'keyboard submission'),
    ('LOGIN-008', 'Login reset clears inputs and result', 'login', 'reset state'),
    ('LOGIN-009', 'Login reset preserves independent search state', 'login', 'independent state'),
    ('LOGIN-010', 'Password visibility toggle restores masking', 'login', 'visibility toggle'),
    ('SEARCH-005', 'Enter submits search', 'search', 'keyboard submission'),
    ('SEARCH-006', 'Search reset clears query and result', 'search', 'reset state'),
    ('SEARCH-007', 'Search enforces its input length limit', 'search', 'maxlength enforcement'),
    ('SEARCH-008', 'Search renders markup as literal text', 'search', 'text rendering'),
    ('FORM-001', 'Email rejects malformed addresses', 'forms', 'typeMismatch'),
    ('FORM-002', 'Email accepts a valid address', 'forms', 'valid email'),
    ('FORM-003', 'Required agreement blocks submission', 'forms', 'required agreement'),
    ('FORM-004', 'Agreement checkbox toggles', 'forms', 'checkbox state'),
    ('FORM-005', 'Delivery radio choices are exclusive', 'forms', 'radio exclusivity'),
    ('FORM-006', 'Country selection persists', 'forms', 'selection state'),
    ('FORM-007', 'Notes retain multiple lines', 'forms', 'multiline input'),
    ('FORM-008', 'Quantity rejects values below minimum', 'forms', 'rangeUnderflow'),
    ('FORM-009', 'Quantity rejects values above maximum', 'forms', 'rangeOverflow'),
    ('FORM-010', 'Quantity rejects a fractional step', 'forms', 'stepMismatch'),
    ('FORM-011', 'Quantity accepts an in-range integer', 'forms', 'valid quantity'),
    ('FORM-012', 'Disabled input rejects editing', 'forms', 'disabled editing'),
    ('FORM-013', 'Read-only input rejects editing', 'forms', 'readonly editing'),
    ('FORM-014', 'Reset restores native control defaults', 'forms', 'reset defaults'),
    ('FORM-015', 'Invalid submission leaves result empty', 'forms', 'invalid submission'),
    ('FORM-016', 'Valid control form publishes its result', 'forms', 'valid submission'),
    ('NAV-003', 'Enter activates the login link', 'navigation', 'keyboard navigation'),
    ('NAV-004', 'Navigation exposes named visible links', 'navigation', 'navigation semantics'),
    ('NAV-005', 'Section navigation preserves form input', 'navigation', 'same-document state'),
    ('NAV-006', 'Back restores the previous section', 'navigation', 'history navigation'),
)
EXPECTED = {
    'LOGIN-005': 'A username containing spaces has patternMismatch=true.',
    'LOGIN-006': 'A five-character password has tooShort=true and no login result is displayed.',
    'LOGIN-007': 'Enter in the password field publishes the fixed demo-only login status.',
    'LOGIN-008': 'Login reset empties both credentials and the prior result.',
    'LOGIN-009': 'Login reset preserves the existing search query.',
    'LOGIN-010': 'The toggle reveals then masks the password without changing its value.',
    'SEARCH-005': 'Enter publishes the literal no-results message for sample book.',
    'SEARCH-006': 'Search reset empties the query and previous result.',
    'SEARCH-007': 'Inserting 70 characters retains exactly the configured 64-character maximum.',
    'SEARCH-008': 'Markup is displayed literally in the result and creates no image element.',
    'FORM-001': 'A malformed email has typeMismatch=true.',
    'FORM-002': 'qa@example.test has valid=true in the email control.',
    'FORM-003': 'Unchecked required agreement has valueMissing=true and prevents a result.',
    'FORM-004': 'Checking then unchecking updates the agreement checkbox state.',
    'FORM-005': 'Selecting express delivery unchecks standard delivery.',
    'FORM-006': 'Selecting Turkey retains the tr option value.',
    'FORM-007': 'The textarea preserves both entered lines and their newline.',
    'FORM-008': 'A detached editable number control reports rangeUnderflow for a value below its declared finite minimum.',
    'FORM-009': 'A detached editable number control reports rangeOverflow for a value above its declared finite maximum.',
    'FORM-010': 'Quantity 1.5 has stepMismatch=true for integer steps.',
    'FORM-011': 'Quantity 5 has valid=true.',
    'FORM-012': 'Disabled input rejects fill and preserves its initial value.',
    'FORM-013': 'Read-only input rejects fill and preserves its initial value.',
    'FORM-014': 'Reset restores unchecked agreement, standard delivery, gb, quantity 1, and empty notes.',
    'FORM-015': 'Empty email prevents submission and leaves the result empty.',
    'FORM-016': 'Valid email and agreement produce exactly Demo controls submitted.',
    'NAV-003': 'Enter on the login link navigates to the login fragment.',
    'NAV-004': 'Both visible navigation links have names and the expected fragment targets.',
    'NAV-005': 'Navigating to search preserves the entered username.',
    'NAV-006': 'Back from search restores the previous login fragment.',
}
EXTRA_CASES = tuple(TestCase(case_id, name, TestType.UI,
    ('login', 'search') if case_id == 'LOGIN-009' else
    ('navigation', 'login') if case_id == 'NAV-005' else (feature,),
    (('Inspect the authorized initial HTML', 'Probe a detached native field with scripts disabled and no submission', name)
     if case_id in ('FORM-001','FORM-002','FORM-008','FORM-009') else
     ('Open a fresh controlled fixture', name, 'Check the explicit browser outcome')),
    EXPECTED[case_id])
    for case_id, name, feature, behavior in SPECS)


def _check(page, case_id):
    with ExitStack() as stack:
        data = SampleData()
        cached = {}
        def get(key):
            if key not in cached:
                cached[key] = stack.enter_context(control(page, key))
            return cached[key]
        def value(key):
            return get(key).input_value()
        def validity(key, flag):
            return get(key).evaluate('(el, flag) => el.validity[flag]', flag)
        def login():
            get('login.username').fill(data.username)
            get('login.password').fill(data.password)
        login_result = page.locator('#login-result')
        search_result = page.locator('#search-result')
        form_result = page.locator('#controls-result')
        if case_id == 'LOGIN-005':
            get('login.username').fill('bad user')
            assert validity('login.username', 'patternMismatch')
        elif case_id == 'LOGIN-006':
            login()
            get('login.password').fill('short')
            get('login.submit').click()
            assert validity('login.password', 'tooShort') and login_result.inner_text() == ''
        elif case_id == 'LOGIN-007':
            login()
            get('login.password').press('Enter')
            assert login_result.inner_text() == 'Demo only: authentication is not connected.'
        elif case_id == 'LOGIN-008':
            login()
            get('login.submit').click()
            get('login.reset').click()
            assert value('login.username') == value('login.password') == login_result.inner_text() == ''
        elif case_id == 'LOGIN-009':
            get('search.query').fill('retained')
            login()
            get('login.reset').click()
            assert value('search.query') == 'retained'
        elif case_id == 'LOGIN-010':
            get('login.password').fill('fake-demo-password')
            get('login.toggle').click()
            assert get('login.password').get_attribute('type') == 'text'
            get('login.toggle').click()
            assert get('login.password').get_attribute('type') == 'password'
            assert value('login.password') == 'fake-demo-password'
        elif case_id == 'SEARCH-005':
            get('search.query').fill('sample book')
            get('search.query').press('Enter')
            assert search_result.inner_text() == 'No products found for "sample book".'
        elif case_id == 'SEARCH-006':
            get('search.query').fill('sample book')
            get('search.submit').click()
            get('search.reset').click()
            assert value('search.query') == search_result.inner_text() == ''
        elif case_id == 'SEARCH-007':
            get('search.query').fill('x' * 70)
            assert len(value('search.query')) == 64
        elif case_id == 'SEARCH-008':
            markup = '<img src=x onerror=alert(1)>'
            get('search.query').fill(markup)
            get('search.submit').click()
            assert search_result.inner_text() == f'No products found for "{markup}".'
            assert search_result.locator('img').count() == 0
        elif case_id in ('FORM-001', 'FORM-002'):
            get('forms.email').fill('invalid' if case_id == 'FORM-001' else 'qa@example.test')
            assert validity('forms.email', 'typeMismatch' if case_id == 'FORM-001' else 'valid')
        elif case_id == 'FORM-003':
            get('forms.email').fill('qa@example.test')
            get('forms.submit').click()
            assert validity('forms.terms', 'valueMissing') and form_result.inner_text() == ''
        elif case_id == 'FORM-004':
            get('forms.terms').check()
            assert get('forms.terms').is_checked()
            get('forms.terms').uncheck()
            assert not get('forms.terms').is_checked()
        elif case_id == 'FORM-005':
            get('forms.express').check()
            assert get('forms.express').is_checked() and not get('forms.standard').is_checked()
        elif case_id == 'FORM-006':
            get('forms.country').select_option('tr')
            assert value('forms.country') == 'tr'
        elif case_id == 'FORM-007':
            get('forms.notes').fill('first line\nsecond line')
            assert value('forms.notes') == 'first line\nsecond line'
        elif case_id in ('FORM-008', 'FORM-009', 'FORM-010', 'FORM-011'):
            number, flag = {'FORM-008': ('0', 'rangeUnderflow'), 'FORM-009': ('11', 'rangeOverflow'),
                            'FORM-010': ('1.5', 'stepMismatch'), 'FORM-011': ('5', 'valid')}[case_id]
            get('forms.quantity').fill(number)
            assert validity('forms.quantity', flag)
        elif case_id in ('FORM-012', 'FORM-013'):
            key = 'forms.disabled' if case_id == 'FORM-012' else 'forms.readonly'
            assert not get(key).is_editable()
            original = value(key)
            try:
                get(key).fill('changed', timeout=200)
            except Error:
                pass
            else:
                raise AssertionError('Protected input unexpectedly accepted editing.')
            assert value(key) == original
        elif case_id == 'FORM-014':
            get('forms.terms').check()
            get('forms.express').check()
            get('forms.country').select_option('tr')
            get('forms.quantity').fill('5')
            get('forms.notes').fill('temporary')
            get('forms.reset').click()
            assert not get('forms.terms').is_checked() and get('forms.standard').is_checked()
            assert value('forms.country') == 'gb' and value('forms.quantity') == '1' and value('forms.notes') == ''
        elif case_id == 'FORM-015':
            get('forms.submit').click()
            assert form_result.inner_text() == '' and validity('forms.email', 'valueMissing')
        elif case_id == 'FORM-016':
            get('forms.email').fill('qa@example.test')
            get('forms.terms').check()
            get('forms.submit').click()
            assert form_result.inner_text() == 'Demo controls submitted.'
        elif case_id == 'NAV-003':
            get('navigation.login').press('Enter')
            assert page.url.endswith('#login')
        elif case_id == 'NAV-004':
            for key, target in (('navigation.login', '#login'), ('navigation.search', '#search')):
                assert get(key).is_visible() and get(key).get_attribute('href') == target
                assert get(key).inner_text().strip()
        elif case_id == 'NAV-005':
            get('login.username').fill('retained-user')
            get('navigation.search').click()
            assert page.url.endswith('#search') and value('login.username') == 'retained-user'
        elif case_id == 'NAV-006':
            get('navigation.login').click()
            get('navigation.search').click()
            page.go_back()
            assert page.url.endswith('#login')
        else:
            raise ValueError('No UI scenario is registered.')


EXTRA_CHECKS = {case_id: partial(_check, case_id=case_id) for case_id, *_ in SPECS}
