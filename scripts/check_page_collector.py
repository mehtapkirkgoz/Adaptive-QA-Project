"""Verify snapshot collection in Chromium using offline controlled documents."""

from dataclasses import asdict
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

from adaptive_qa.discovery import detect_page_features
from adaptive_qa.models import FeatureStatus
from adaptive_qa.page_collector import collect_page_snapshot
from adaptive_qa.config import ProjectConfig
from adaptive_qa.egress import DestinationGuard, EgressProxy, chromium_proxy_options
from adaptive_qa.targets import validate_local_sample_target


def check_guarded_sample(playwright):
    project = ProjectConfig('discovery-demo', 'Discovery Sample',
                            'http://127.0.0.1:8000', ('127.0.0.1',))
    handler = partial(SimpleHTTPRequestHandler,
                      directory=str(Path(__file__).resolve().parents[1] / 'samples/web'))
    server = ThreadingHTTPServer(('127.0.0.1', 8000), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with EgressProxy(DestinationGuard(project, local_sample=True)) as proxy:
            browser = playwright.chromium.launch(**chromium_proxy_options(proxy.url))
            try:
                context = browser.new_context(service_workers='block', accept_downloads=False)
                def handle_request(route):
                    try:
                        if route.request.method not in ('GET', 'HEAD'):
                            raise ValueError('Only read requests are allowed.')
                        validate_local_sample_target(route.request.url, project)
                    except ValueError:
                        route.abort('blockedbyclient')
                    else:
                        route.continue_()
                context.route('**/*', handle_request)
                context.route_web_socket('**/*', lambda connection: connection.close())
                page = context.new_page()
                response = page.goto(project.base_url, wait_until='domcontentloaded', timeout=10000)
                assert response is not None and response.status == 200
                snapshot = collect_page_snapshot(page)
                assert snapshot.collection_complete
                assert all(item.status == FeatureStatus.PRESENT
                           for item in detect_page_features(snapshot))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main():
    with sync_playwright() as playwright:
        check_guarded_sample(playwright)
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(service_workers='block')
            context.route('**/*', lambda route: route.fulfill(
                status=200, content_type='text/html', body='<html><body></body></html>'))
            page = context.new_page()
            page.goto('http://127.0.0.1:8000/?token=secret-token')
            page.set_content('''<form id="login"><label for="user">Email</label>
                <input id="user" type="email" value="private-user">
                <input type="password" value="private-password">
                <button>Sign in</button><button hidden>Search</button></form>
                <input form="login" type="text" aria-label="External field">
                <form hidden><input type="search"><button>Search</button></form>
                <a href="/login?token=private-token#secret">Account</a>
                <a href="javascript:alert(1)">Ignored</a>''')
            snapshot = collect_page_snapshot(page)
            payload = json.dumps(asdict(snapshot))
            assert not any(secret in payload for secret in (
                'private-user', 'private-password', 'private-token', 'secret-token'))
            assert snapshot.url == 'http://127.0.0.1:8000/'
            assert len(snapshot.forms) == 1 and len(snapshot.forms[0].fields) == 3
            assert snapshot.forms[0].fields[0].label == 'Email'
            assert snapshot.forms[0].buttons == ('Sign in',)
            assert snapshot.links[0].href == 'http://127.0.0.1:8000/login'
            assert len(snapshot.links) == 1 and snapshot.collection_complete
            assert detect_page_features(snapshot)[0].status == FeatureStatus.PRESENT
            for html in ('<iframe></iframe>', '<custom-login></custom-login>',
                         '<div role="form"></div>', '<a href="/">x</a>' * 201,
                         '<input type="password">',
                         '<form>' + '<input>' * 101 + '</form>',
                         '<form></form>' * 51,
                         '<form><button>' + 'x' * 161 + '</button></form>'):
                page.set_content(html)
                assert not collect_page_snapshot(page).collection_complete
            page.set_content('<form role="search"><input type="search"><button>Search</button></form>')
            assert detect_page_features(collect_page_snapshot(page))[1].status == FeatureStatus.PRESENT
            page.set_content('<h1>Information</h1>')
            assert all(item.status == FeatureStatus.ABSENT
                       for item in detect_page_features(collect_page_snapshot(page)))
            page.set_content('<div id="host"></div>')
            page.evaluate("document.querySelector('#host').attachShadow({mode:'open'}).innerHTML = '<input>'")
            assert not collect_page_snapshot(page).collection_complete
            print('Page collector browser checks passed.')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
