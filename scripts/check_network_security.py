"""Real Chromium egress regression checks using local canary servers only."""

import json
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import Error, sync_playwright

from adaptive_qa.config import ProjectConfig
from adaptive_qa.egress import DestinationGuard, EgressProxy, chromium_proxy_options


class CountingServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.accepted = 0
        self.posts = 0

    def get_request(self):
        connection, address = super().get_request()
        self.accepted += 1
        connection.settimeout(3)
        return connection, address


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/redirect-"):
            destination = {
                "/redirect-allowed": "/allowed",
                "/redirect-denied": self.server.forbidden_url + "/blocked",
                "/redirect-loop": "/redirect-loop",
            }.get(self.path, "/allowed")
            self.send_response(302)
            self.send_header("Location", destination)
            self.end_headers()
            return
        content = "<title>Allowed fixture</title><h1>Allowed fixture</h1>"
        if self.path == "/script-redirect":
            content += f'<script>location.href="{self.server.forbidden_url}/blocked";</script>'
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.server.posts += 1
        self.send_response(200)
        self.end_headers()


class BrowserEgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canary = CountingServer(("127.0.0.1", 0), FixtureHandler)
        cls.addClassCleanup(cls.canary.server_close)
        canary_thread = Thread(target=cls.canary.serve_forever, daemon=True)
        canary_thread.start()
        cls.addClassCleanup(cls.canary.shutdown)
        cls.forbidden = f"http://127.0.0.1:{cls.canary.server_port}"
        cls.origin = CountingServer(("127.0.0.1", 8000), FixtureHandler)
        cls.origin.forbidden_url = cls.forbidden
        cls.addClassCleanup(cls.origin.server_close)
        origin_thread = Thread(target=cls.origin.serve_forever, daemon=True)
        origin_thread.start()
        cls.addClassCleanup(cls.origin.shutdown)

    @contextmanager
    def browser_context(self):
        project = ProjectConfig("fixture", "Fixture", "http://127.0.0.1:8000", ("127.0.0.1",))
        guard = DestinationGuard(project, local_sample=True)
        with EgressProxy(guard) as proxy, sync_playwright() as playwright:
            browser = playwright.chromium.launch(**chromium_proxy_options(proxy.url))
            try:
                context = browser.new_context(service_workers="block")
                context.set_default_timeout(5000)
                context.set_default_navigation_timeout(10000)
                yield guard, context
            finally:
                browser.close()

    def test_allowed_redirect_reaches_authorized_destination(self):
        with self.browser_context() as (guard, context):
            page = context.new_page()
            response = page.goto("http://127.0.0.1:8000/redirect-allowed")
            self.assertEqual(response.status, 200)
            self.assertEqual(page.url, "http://127.0.0.1:8000/allowed")
            self.assertGreaterEqual(guard.redirects, 1)

    def test_denied_redirect_never_connects_to_canary(self):
        before = self.canary.accepted
        with self.browser_context() as (guard, context):
            response = context.new_page().goto("http://127.0.0.1:8000/redirect-denied")
            self.assertEqual(response.status, 403)
            self.assertGreaterEqual(guard.denied, 1)
        self.assertEqual(self.canary.accepted, before)

    def test_script_redirect_is_checked_as_a_new_connection(self):
        before = self.canary.accepted
        with self.browser_context() as (_, context):
            page = context.new_page()
            page.goto("http://127.0.0.1:8000/script-redirect")
            page.wait_for_url(self.forbidden + "/blocked")
            self.assertIn("Destination policy rejected", page.content())
        self.assertEqual(self.canary.accepted, before)

    def test_subresource_request_cannot_reach_canary(self):
        before = self.canary.accepted
        with self.browser_context() as (_, context):
            page = context.new_page()
            page.goto("http://127.0.0.1:8000/allowed")
            outcome = page.evaluate(
                "url => fetch(url).then(response => response.status).catch(() => 'blocked')",
                self.forbidden + "/asset",
            )
            self.assertIn(outcome, (403, "blocked"))
        self.assertEqual(self.canary.accepted, before)

    def test_https_connect_cannot_reach_canary(self):
        before = self.canary.accepted
        with self.browser_context() as (_, context):
            with self.assertRaises(Error):
                context.new_page().goto(f"https://127.0.0.1:{self.canary.server_port}/")
        self.assertEqual(self.canary.accepted, before)

    def test_redirect_loop_stops_at_proxy_budget(self):
        with self.browser_context() as (guard, context):
            response = context.new_page().goto("http://127.0.0.1:8000/redirect-loop")
            self.assertEqual(response.status, 403)
            self.assertEqual(guard.redirects, 11)

    def test_post_is_rejected_before_origin(self):
        before = self.origin.posts
        with self.browser_context() as (_, context):
            page = context.new_page()
            page.goto("http://127.0.0.1:8000/allowed")
            outcome = page.evaluate(
                "() => fetch('/write', {method: 'POST', body: 'fake'}).then(r => r.status)"
            )
            self.assertEqual(outcome, 405)
        self.assertEqual(self.origin.posts, before)

    def test_websocket_cannot_connect_to_canary(self):
        before = self.canary.accepted
        with self.browser_context() as (_, context):
            page = context.new_page()
            page.goto("http://127.0.0.1:8000/allowed")
            outcome = page.evaluate("""url => new Promise(resolve => {
                const socket = new WebSocket(url);
                socket.onerror = () => resolve('blocked');
                socket.onopen = () => { socket.close(); resolve('opened'); };
                setTimeout(() => { socket.close(); resolve('timeout'); }, 2000);
            })""", self.forbidden.replace("http:", "ws:") + "/socket")
            self.assertEqual(outcome, "blocked")
        self.assertEqual(self.canary.accepted, before)

    def test_browser_does_not_fallback_to_direct_when_proxy_stops(self):
        project = ProjectConfig("fixture", "Fixture", "http://127.0.0.1:8000", ("127.0.0.1",))
        guard = DestinationGuard(project, local_sample=True)
        proxy = EgressProxy(guard)
        proxy.__enter__()
        stopped = False
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(**chromium_proxy_options(proxy.url))
                try:
                    page = browser.new_page()
                    proxy.__exit__()
                    stopped = True
                    before = self.origin.accepted
                    with self.assertRaises(Error):
                        page.goto("http://127.0.0.1:8000/allowed", timeout=5000)
                    self.assertEqual(self.origin.accepted, before)
                finally:
                    browser.close()
        finally:
            if not stopped:
                proxy.__exit__()


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BrowserEgressTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "checks": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "passed": result.wasSuccessful(),
    }
    path = Path(__file__).resolve().parents[1] / "artifacts/security/report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
