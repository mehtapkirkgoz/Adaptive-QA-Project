"""Read-only HTML quality checks independent of login, commerce and button names."""

from adaptive_qa.models import TestCase, TestType


def check_title(page):
    assert page.title().strip(), 'The document must have a non-empty title.'


def check_language(page):
    # Presence is checked, not language correctness inferred from page content.
    assert (page.locator('html').get_attribute('lang', timeout=3000) or '').strip(), 'The document language must be declared.'


def check_unique_ids(page):
    assert page.evaluate('''() => {
        const ids = [...document.querySelectorAll('[id]')].map(node => node.id);
        return ids.every(id => id.trim().length > 0) && new Set(ids).size === ids.length;
    }'''), 'Document IDs must be non-empty and unique.'


def check_accessibility_references(page):
    assert page.evaluate('''() => [...document.querySelectorAll('[aria-labelledby], [aria-describedby]')].every(node =>
        ['aria-labelledby', 'aria-describedby'].every(name => {
            if (!node.hasAttribute(name)) return true;
            const ids = node.getAttribute(name).trim().split(/\\s+/);
            return ids.every(id => id && document.getElementById(id));
        }))'''), 'ARIA naming and description references must resolve in the document.'


def check_fragment_targets(page):
    assert page.evaluate('''() => [...document.querySelectorAll('a[href^="#"]')].every(link => {
        const href = link.getAttribute('href');
        if (href === '#') return true;
        let id;
        try { id = decodeURIComponent(href.slice(1)); } catch { return false; }
        return !!document.getElementById(id) || [...document.getElementsByName(id)].some(node => node.tagName === 'A');
    })'''), 'Same-document fragment links must resolve to an ID or named anchor.'


DOCUMENT_CHECKS = {
    'DOC-001': check_title,
    'DOC-002': check_language,
    'DOC-003': check_unique_ids,
    'DOC-004': check_accessibility_references,
    'DOC-005': check_fragment_targets,
}
_DESCRIPTIONS = (
    ('Document title is non-empty', 'Read the document title', 'The title contains non-whitespace text.'),
    ('Document language is declared', 'Read the html lang attribute', 'The language attribute contains non-whitespace text.'),
    ('Document IDs are unique', 'Collect document ID attributes', 'All IDs are non-empty and unique.'),
    ('ARIA references resolve', 'Resolve naming and description ID references', 'Every declared ARIA reference resolves to an element.'),
    ('Fragment links resolve', 'Resolve local fragment targets without following links', 'Each non-empty local fragment has an ID or named anchor target.'),
)
DOCUMENT_CASES = tuple(TestCase(case_id, name, TestType.UI, (),
    ('Inspect an authorized HTML document', step), expected)
    for case_id, (name, step, expected) in zip(DOCUMENT_CHECKS, _DESCRIPTIONS, strict=True))
