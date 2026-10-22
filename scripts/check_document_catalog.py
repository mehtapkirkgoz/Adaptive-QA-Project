"""Verify reusable document rules on contrasting offline HTML and real defects."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from adaptive_qa.document_checks import DOCUMENT_CHECKS
from adaptive_qa.semantic_checks import SEMANTIC_CHECKS


def main():
    fixtures = {
        'information': '<h1 id="intro">Information</h1><a href="#intro">Read introduction</a><button aria-label="Open menu"></button>',
        'commerce': '<h1 id="product">Product</h1><p id="price">25</p><article aria-labelledby="product" aria-describedby="price">Book</article><button aria-labelledby="product"></button><a href="#product">Product</a>',
        'account': '''<h1 id="account">Account</h1><form aria-labelledby="account">
            <label for="user">User</label><input id="user"><button>Continue</button>
            <label>Search <input type="search"></label><label>Country <select><option>TR</option></select></label>
            <label>Topics <select multiple><option>QA</option></select></label>
            <label>Quantity <input type="number"></label><label>Accept <input type="checkbox"></label>
            <label>Delivery <input type="radio"></label><label>Scale <input type="range"></label>
            <button role="switch" aria-checked="false" aria-label="Notifications"></button></form>''',
    }
    defects = {
        'DOC-001': '<html lang="en"><head><title> </title></head><body>Content</body></html>',
        'DOC-002': '<html><head><title>Content</title></head><body>Content</body></html>',
        'DOC-003': '<html lang="en"><title>Content</title><p id="same">One</p><p id="same">Two</p></html>',
        'DOC-004': '<html lang="en"><title>Content</title><main aria-labelledby="missing">Content</main></html>',
        'DOC-005': '<html lang="en"><title>Content</title><a href="#missing">Missing target</a></html>',
        'A11Y-001': '<button></button>',
        'A11Y-002': '<input type="text">',
        'NAV-007': '<a href="#target" style="display:inline-block;width:30px;height:20px"></a><p id="target">Target</p>',
        'FORM-017': '<label for="missing">Name</label><input id="actual">',
        'DOC-006': '<meta name="viewport" content="user-scalable=no">',
        'DOC-007': '<meta http-equiv="refresh" content="9999">',
    }
    checks = {**DOCUMENT_CHECKS, **SEMANTIC_CHECKS}
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(service_workers='block')
            requests = []
            context.route('**/*', lambda route: (requests.append(True), route.abort()))
            context.route_web_socket('**/*', lambda socket: socket.close())
            for name, body in fixtures.items():
                for case_id, check in checks.items():
                    page = context.new_page()
                    try:
                        page.set_content(f'<!doctype html><html lang="en"><title>{name}</title><body>{body}</body></html>')
                        check(page)
                        results.append({'fixture': name, 'case_id': case_id, 'outcome': 'passed'})
                    finally:
                        page.close()
            for case_id, html in defects.items():
                page = context.new_page()
                try:
                    page.set_content(html)
                    try:
                        checks[case_id](page)
                    except AssertionError:
                        results.append({'fixture': 'negative', 'case_id': case_id, 'outcome': 'defect_detected'})
                    else:
                        raise RuntimeError(f'{case_id} accepted its negative fixture.')
                finally:
                    page.close()
            assert not requests, 'Offline checks must not request network access.'
            context.close()
        finally:
            browser.close()
    output = Path(__file__).resolve().parents[1] / 'artifacts/matching/document-catalog.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'status': 'passed', 'unique_cases': len(checks), 'positive_checks': len(checks) * len(fixtures),
        'negative_checks': len(defects), 'external_requests': 0, 'results': results}, indent=2) + '\n', encoding='utf-8')
    print(f'{len(checks)} document/semantic scenarios passed {len(checks) * len(fixtures)} contrasting checks and detected {len(defects)} real defects.')


if __name__ == '__main__':
    main()
