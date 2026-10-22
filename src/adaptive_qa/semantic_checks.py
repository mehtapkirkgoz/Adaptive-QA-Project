"""Read-only semantic rules with feature prerequisites and fixed assertions."""

import re
from playwright.sync_api import expect
from adaptive_qa.models import TestCase, TestType


def _named_visible_roles(page, roles):
    for role in roles:
        controls = page.get_by_role(role)
        count = controls.count()
        if count > 500:
            raise RuntimeError('Semantic inspection exceeds the per-role element budget.')
        for index in range(count):
            control = controls.nth(index)
            if control.is_visible():
                expect(control).to_have_accessible_name(re.compile(r'\S'), timeout=1000)


def check_button_names(page):
    _named_visible_roles(page, ('button',))


def check_field_names(page):
    _named_visible_roles(page, ('textbox', 'searchbox', 'combobox', 'listbox',
                               'spinbutton', 'checkbox', 'radio', 'switch', 'slider'))


def check_link_names(page):
    _named_visible_roles(page, ('link',))


def check_label_targets(page):
    assert page.evaluate('''() => [...document.querySelectorAll('label[for]')].every(label => {
        const target = document.getElementById(label.htmlFor);
        return target && label.control === target;
    })'''), 'Explicit labels must reference an existing labelable control.'


def check_zoom_policy(page):
    assert page.evaluate('''() => [...document.querySelectorAll('meta[name]')]
        .filter(meta => meta.name.toLowerCase() === 'viewport').every(meta => {
            const directives = meta.content.toLowerCase().split(/[,;]/).map(item => item.trim().split(/\\s*=\\s*/));
            return directives.every(([key, value]) => {
                if (key === 'user-scalable') return !['no', '0'].includes(value);
                if (key === 'maximum-scale') return !value || !Number.isFinite(Number(value)) || Number(value) >= 2;
                return true;
            });
        })'''), 'Viewport directives must not disable zoom or cap scaling below two.'


def check_no_meta_refresh(page):
    assert page.evaluate('''() => ![...document.querySelectorAll('meta[http-equiv]')]
        .some(meta => meta.httpEquiv.trim().toLowerCase() === 'refresh')'''), 'Automatic meta refresh must not replace the document.'


_SPECS = (
    ('A11Y-001', 'Visible buttons have accessible names', (), check_button_names,
     'Inspect visible button roles', 'Every visible button has a non-whitespace accessible name.'),
    ('A11Y-002', 'Visible form controls have accessible names', ('forms',), check_field_names,
     'Inspect visible input and selection roles', 'Every visible form control has a non-whitespace accessible name.'),
    ('NAV-007', 'Visible links have accessible names', ('navigation',), check_link_names,
     'Inspect visible link roles', 'Every visible link has a non-whitespace accessible name.'),
    ('FORM-017', 'Explicit labels target labelable controls', ('forms',), check_label_targets,
     'Resolve label for attributes', 'Every explicit label targets an existing labelable control.'),
    ('DOC-006', 'Viewport preserves zoom', (), check_zoom_policy,
     'Inspect declared viewport directives', 'No viewport directive disables zoom or caps maximum scale below two.'),
    ('DOC-007', 'Document does not force meta refresh', (), check_no_meta_refresh,
     'Inspect meta refresh directives', 'No meta refresh directive replaces the page automatically.'),
)
SEMANTIC_CHECKS = {case_id: check for case_id, _, _, check, _, _ in _SPECS}
SEMANTIC_CASES = tuple(TestCase(case_id, name, TestType.UI, prerequisites,
    ('Inspect an authorized HTML document', step), expected)
    for case_id, name, prerequisites, _, step, expected in _SPECS)
