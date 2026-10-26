"""Pinned HTTPS and memory-only cookies for the exact public demonstration."""
from dataclasses import dataclass, replace
from http.cookiejar import CookieJar
import http.client
import ssl
from urllib.request import Request
from urllib.parse import urlencode, urlsplit

from adaptive_qa.config import ProjectConfig
from adaptive_qa.demo_login_contract import (
    ORIGIN, LOGIN, AUTHENTICATE, SECURE, LOGOUT, DemoLoginPlan, DemoLoginScenario,
)
from adaptive_qa.egress import DestinationGuard


def demo_body(plan):
    # Publicly documented demo account only; never accept customer inputs here.
    password = 'deliberately-wrong-demo-password' if plan.scenario == DemoLoginScenario.REJECTED else 'SuperSecretPassword!'
    return urlencode((('username', 'tomsmith'), ('password', password))).encode('ascii')


@dataclass(frozen=True)
class DemoResponse:
    status: int
    body: bytes
    location: str | None = None


class DemoLoginTransport:
    """No arbitrary URLs, headers, TLS override, cookie export or redirect following."""
    def __init__(self, plan):
        if not isinstance(plan, DemoLoginPlan):
            raise ValueError('A typed exact-demo plan is required.')
        self.plan = plan
        self.guard = DestinationGuard(ProjectConfig('public-login-demo', 'Public login demo', LOGIN,
                                                   ('the-internet.herokuapp.com',), True), max_requests=1)
        self._target = None
        self._cookies = CookieJar()
        self._steps = [('GET', LOGIN, 200, None),
                       ('POST', AUTHENTICATE, 302, plan.expected_document),
                       ('GET', plan.expected_document, 200, None)]
        if plan.scenario == DemoLoginScenario.LOGOUT:
            self._steps += [('GET', LOGOUT, 302, LOGIN), ('GET', LOGIN, 200, None),
                            ('GET', SECURE, 302, LOGIN), ('GET', LOGIN, 200, None)]
        self._index = 0
        self.attempted_submissions = 0

    @property
    def complete(self):
        return self._index == len(self._steps)

    def close(self):
        self._cookies.clear()

    def request(self, method, url, body=None):
        if self.complete:
            raise ValueError('Demo request budget consumed.')
        wanted_method, wanted_url, status, destination = self._steps[self._index]
        # Consume attempts, including malformed ones: never retry an uncertain POST.
        self._index += 1
        if ((method, url) != (wanted_method, wanted_url)
                or (method == 'POST' and body != demo_body(self.plan))
                or (method == 'GET' and body is not None)):
            self._index = len(self._steps)
            raise ValueError('Unexpected demo request.')
        connection = None
        try:
            if self._target is None:
                target = self.guard.authorize(LOGIN)
                self._target = replace(target, addresses=(target.addresses[0],))
            target = self._target
            connection = http.client.HTTPConnection(target.hostname, target.port, timeout=5)
            connection.auto_open = 0
            connection.sock = self.guard.connect(target, timeout_seconds=5)
            context = ssl.create_default_context()
            context.keylog_filename = None
            connection.sock = context.wrap_socket(connection.sock, server_hostname=target.hostname)
            connection.sock.settimeout(5)
            cookie_request = Request(url)
            self._cookies.add_cookie_header(cookie_request)
            headers = {'Host': target.hostname, 'Accept': 'text/html', 'Connection': 'close',
                       'User-Agent': 'Adaptive-QA-Authorized-Demo/1.0'}
            cookie = cookie_request.get_header('Cookie')
            if cookie:
                headers['Cookie'] = cookie
            if method == 'POST':
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                headers['Content-Length'] = str(len(body))
                self.attempted_submissions = 1
            connection.request(method, urlsplit(url).path, body=body, headers=headers)
            response = connection.getresponse()
            if (response.status != status or response.getheader('Content-Encoding') is not None
                    or len(response.headers.get_all('Location', [])) > 1):
                raise ValueError('Unexpected demo HTTP response.')
            location = response.getheader('Location')
            if destination:
                if location not in (destination, destination[len(ORIGIN):]):
                    raise ValueError('Unexpected demo redirect.')
            elif location is not None or not response.getheader('Content-Type', '').lower().startswith('text/html'):
                raise ValueError('Expected an HTML document without redirects.')
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError('Oversized demo response.')
            self._cookies.extract_cookies(response, cookie_request)
            return DemoResponse(status, raw, destination)
        except Exception:
            self._index = len(self._steps)
            raise
        finally:
            if connection:
                connection.close()
