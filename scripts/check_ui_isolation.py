"""Verify cleanup, context separation, and reverse-order independent runs."""

from dataclasses import asdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

from adaptive_qa.browser_process import run_isolated_sample_test
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.config import ProjectConfig
from adaptive_qa.egress import DestinationGuard, EgressProxy, chromium_proxy_options
from adaptive_qa.models import TestStatus
from adaptive_qa.sample_data import sample_test_data
from adaptive_qa.targets import validate_local_sample_target


def check_contexts():
    project = ProjectConfig('isolation', 'Isolation', 'http://127.0.0.1:8000', ('127.0.0.1',))
    with EgressProxy(DestinationGuard(project, local_sample=True)) as proxy, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**chromium_proxy_options(proxy.url))
        try:
            context = browser.new_context(service_workers='block', accept_downloads=False)
            def guard(route):
                try:
                    if route.request.method not in ('GET', 'HEAD'):
                        raise ValueError('Only read requests are allowed.')
                    validate_local_sample_target(route.request.url, project)
                except ValueError:
                    route.abort('blockedbyclient')
                else:
                    route.continue_()
            context.route('**/*', guard)
            context.route_web_socket('**/*', lambda connection: connection.close())
            page = context.new_page()
            page.goto(project.base_url, wait_until='domcontentloaded', timeout=10000)
            try:
                with sample_test_data(page):
                    page.locator('#username').fill('temporary-user')
                    page.evaluate("localStorage.setItem('isolation', 'temporary'); sessionStorage.setItem('isolation', 'temporary')")
                    context.add_cookies([{'name': 'isolation', 'value': 'temporary', 'url': project.base_url}])
                    raise AssertionError('Exercise failure cleanup')
            except AssertionError as error:
                assert str(error) == 'Exercise failure cleanup'
            assert page.locator('#username').input_value() == ''
            assert page.evaluate('localStorage.length + sessionStorage.length') == 0
            assert context.cookies() == []
            page.evaluate("localStorage.setItem('first-context', 'retained')")
            second = browser.new_context(service_workers='block', accept_downloads=False)
            second.route('**/*', guard)
            second.route_web_socket('**/*', lambda connection: connection.close())
            other = second.new_page()
            other.goto(project.base_url, wait_until='domcontentloaded', timeout=10000)
            assert other.evaluate('localStorage.length + sessionStorage.length') == 0
            assert other.locator('#username').input_value() == ''
            second.close()
            context.close()
        finally:
            browser.close()


def main():
    root = Path(__file__).resolve().parents[1]
    server = ThreadingHTTPServer(('127.0.0.1', 8000), partial(SimpleHTTPRequestHandler, directory=str(root / 'samples/web')))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        check_contexts()
        for definition in reversed(TEST_CASES):
            result = run_isolated_sample_test(definition.case_id)
            assert result.status == TestStatus.PASSED, result
            results.append(asdict(result))
        path = root / 'artifacts/matching/isolation.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'cleanup_passed': True, 'context_separation_passed': True,
            'order': 'reversed_catalog', 'runs': len(results), 'passed': True, 'results': results}, indent=2), encoding='utf-8')
        print(f'Cleanup/context separation and {len(results)} reverse-order runs passed.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
