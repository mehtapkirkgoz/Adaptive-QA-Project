"""Real browser checks for the static demo under a GitHub project-site subpath."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from threading import Thread

from playwright.sync_api import sync_playwright, expect


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    output = Path('artifacts/demo')
    output.mkdir(parents=True, exist_ok=True)
    errors, forbidden = [], []
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        shutil.copytree('frontend/dist-demo', root / 'Adaptive-QA-Project')
        server = ThreadingHTTPServer(('127.0.0.1', 8791), partial(QuietHandler, directory=str(root)))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={'width': 1440, 'height': 1080})
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    prefix = 'http://127.0.0.1:8791/Adaptive-QA-Project/'
                    page.on('request', lambda request: forbidden.append(request.url)
                            if not request.url.startswith(prefix) or '/api/' in request.url else None)
                    page.goto(prefix)
                    expect(page.get_by_role('heading', name='A clearer view of quality.')).to_be_visible()
                    expect(page.get_by_text('Sample projects and illustrative results only.', exact=False)).to_be_visible()
                    page.get_by_role('button', name='Editorial Studio Content website').click()
                    expect(page.get_by_text('journal.example.test')).to_be_visible()
                    page.get_by_role('button', name='Northstar Store E-commerce').click()
                    page.screenshot(path=str(output / 'desktop.png'), full_page=True)
                    page.get_by_role('button', name='Test catalog', exact=True).click()
                    expect(page.get_by_role('status')).to_have_text('100 definitions')
                    page.get_by_label('Testing layer').select_option('ui')
                    expect(page.get_by_role('status')).to_have_text('51 definitions')
                    page.get_by_label('Testing layer').select_option('api')
                    expect(page.get_by_role('status')).to_have_text('34 definitions')
                    page.get_by_label('Testing layer').select_option('database')
                    expect(page.get_by_role('status')).to_have_text('15 definitions')
                    page.get_by_label('Testing layer').select_option('all')
                    page.get_by_label('Search scenarios').fill('LOGIN-001')
                    expect(page.get_by_role('status')).to_have_text('1 definitions')
                    page.get_by_label('Search scenarios').fill('no-matching-fixture')
                    expect(page.get_by_role('status')).to_have_text('0 definitions')
                    expect(page.get_by_text('No matching scenarios.', exact=False)).to_be_visible()
                    page.get_by_role('button', name='Example report', exact=True).click()
                    expect(page.get_by_text('Synthetic data · no run performed')).to_be_visible()
                    page.get_by_role('button', name='Overview', exact=True).click()
                    page.reload()
                    expect(page.get_by_role('heading', name='A clearer view of quality.')).to_be_visible()
                    for width in (390, 768, 1440):
                        page.set_viewport_size({'width': width, 'height': 1000})
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                    page.set_viewport_size({'width': 390, 'height': 844})
                    page.screenshot(path=str(output / 'mobile.png'), full_page=True)
                    assert not errors, errors
                    assert not forbidden, forbidden
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    report = {'demo_only': True, 'catalog': {'ui': 51, 'api': 34, 'database': 15},
              'project_subpath_verified': True, 'catalog_search_and_filters': True,
              'synthetic_report_label_verified': True, 'responsive_widths': [390, 768, 1440],
              'api_or_external_requests': len(forbidden), 'page_errors': errors,
              'credentials_required': False, 'execution_enabled': False}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
