"""Smoke-check only the explicitly owner-published static GitHub Pages demo."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


URL = 'https://mehtapkirkgoz.github.io/Adaptive-QA-Project/'


def main():
    output = Path('artifacts/demo')
    output.mkdir(parents=True, exist_ok=True)
    forbidden, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1080})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: forbidden.append(request.url)
                    if not request.url.startswith(URL) or '/api/' in request.url else None)
            response = page.goto(URL, wait_until='networkidle', timeout=30000)
            assert response is not None and response.status == 200
            expect(page.get_by_role('heading', name='A clearer view of quality.')).to_be_visible()
            expect(page.get_by_text('Sample projects and illustrative results only.', exact=False)).to_be_visible()
            page.screenshot(path=str(output / 'live-desktop.png'), full_page=True)
            page.get_by_role('button', name='Test catalog', exact=True).click()
            expect(page.get_by_role('status')).to_have_text('100 definitions')
            page.get_by_label('Testing layer').select_option('api')
            expect(page.get_by_role('status')).to_have_text('34 definitions')
            page.get_by_role('button', name='Example report', exact=True).click()
            expect(page.get_by_text('Synthetic data · no run performed')).to_be_visible()
            page.get_by_role('button', name='Overview', exact=True).click()
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.screenshot(path=str(output / 'live-mobile.png'), full_page=True)
            assert not errors, errors
            assert not forbidden, forbidden
        finally:
            browser.close()
    report = {'url': URL, 'https_status': 200, 'catalog': 100, 'api_filter': 34,
              'illustrative_report_verified': True, 'mobile_overflow': False,
              'api_or_external_requests': len(forbidden), 'page_errors': errors,
              'test_engine_execution': False}
    (output / 'live-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
