"""Pinned-destination HTTP proxy for controlled browser egress."""

import http.client
import select
import socket
import time
import math
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from threading import Lock, Thread
from urllib.parse import urljoin, urlsplit

from adaptive_qa.config import ProjectConfig
from adaptive_qa.dns_resolver import resolve_with_deadline
from adaptive_qa.policy import DestinationPolicy, validate_public_ip
from adaptive_qa.targets import ValidatedTarget, validate_local_sample_target, validate_target


class DestinationGuard:
    """Separate explicit sample access from public destination validation."""

    def __init__(self, project: ProjectConfig, *, local_sample: bool = False,
                 policy: DestinationPolicy | None = None, max_requests: int = 200) -> None:
        if not isinstance(local_sample, bool):
            raise ValueError("local_sample must be a bool.")
        if type(max_requests) is not int or not 1 <= max_requests <= 200:
            raise ValueError("max_requests must be an integer between 1 and 200.")
        self.max_requests = max_requests
        self.project = project
        self.local_sample = local_sample
        self.policy = policy or DestinationPolicy()
        self.requests = 0
        self.redirects = 0
        self.denied = 0
        self.redirect_outside_scope = False
        self._lock = Lock()

    def authorize(self, url: str) -> ValidatedTarget:
        with self._lock:
            self.requests += 1
            if self.requests > self.max_requests:
                raise ValueError("Destination request budget exceeded.")
        if self.local_sample:
            return validate_local_sample_target(url, self.project)
        return validate_target(url, self.project, self.policy, resolver=resolve_with_deadline)

    def redirect(self, current_url: str, location: str) -> None:
        with self._lock:
            self.redirects += 1
            if self.redirects > 10:
                raise ValueError("Redirect budget exceeded.")
        try:self.authorize(urljoin(current_url, location))
        except ValueError:
            self.redirect_outside_scope=True
            raise

    def connect(self, target: ValidatedTarget, *, timeout_seconds: float = 5) -> socket.socket:
        """Connect to a checked numeric IP, never resolve the hostname again."""
        if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
                or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 5):
            raise ValueError('Connection timeout must be finite and between 0 and 5 seconds.')
        for address in target.addresses:
            if self.local_sample:
                if target.hostname != "127.0.0.1" or target.port != 8000 or address != "127.0.0.1":
                    raise ValueError("Invalid local sample connection.")
            else:
                validate_public_ip(address)
        for address in target.addresses:
            parsed = ip_address(address)
            connection = socket.socket(socket.AF_INET if parsed.version == 4 else socket.AF_INET6)
            connection.settimeout(timeout_seconds)
            try:
                connection.connect((str(parsed), target.port))
                if ip_address(connection.getpeername()[0]) != parsed:
                    raise ValueError("Connected peer does not match the validated IP.")
                return connection
            except OSError:
                connection.close()
            except Exception:
                connection.close()
                raise
        raise OSError("No approved destination address could be reached.")


_HOP_HEADERS = {
    "connection", "proxy-connection", "proxy-authorization", "proxy-authenticate",
    "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
}


class _ProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


class _ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *args) -> None:
        # URLs and request headers may contain sensitive values.
        pass

    def _deny(self, status: int = 403) -> None:
        with self.server.guard._lock:
            self.server.guard.denied += 1
        self.close_connection = True
        self.send_error(status, "Destination policy rejected the request.")

    def do_GET(self) -> None:
        upstream = None
        try:
            target = self.server.guard.authorize(self.path)
            parsed = urlsplit(self.path)
            if parsed.scheme != "http":
                raise ValueError("HTTPS requires an authorized CONNECT tunnel.")
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Length", "0") != "0":
                raise ValueError("Request bodies are not allowed by the read-only proxy.")
            if self.headers.get("Upgrade"):
                raise ValueError("Protocol upgrades are disabled.")
            upstream = http.client.HTTPConnection(target.hostname, target.port, timeout=5)
            upstream.sock = self.server.guard.connect(target)
            connection_tokens = {value.strip().lower() for value in self.headers.get("Connection", "").split(",")}
            headers = {
                key: value for key, value in self.headers.items()
                if key.lower() not in _HOP_HEADERS | connection_tokens | {"host", "content-length"}
            }
            headers["Host"] = parsed.netloc
            headers["Connection"] = "close"
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            upstream.request(self.command, path, headers=headers)
            response = upstream.getresponse()
            locations = response.headers.get_all("Location", [])
            if 300 <= response.status < 400 and locations:
                if len(locations) != 1:
                    raise ValueError("Ambiguous redirect response.")
                self.server.guard.redirect(self.path, locations[0])
            body = b"" if self.command == "HEAD" else response.read(10 * 1024 * 1024 + 1)
            if len(body) > 10 * 1024 * 1024:
                raise ValueError("Response exceeds the evidence transfer limit.")
            self.send_response(response.status)
            response_tokens = {value.strip().lower() for value in response.getheader("Connection", "").split(",")}
            for key, value in response.getheaders():
                if key.lower() not in _HOP_HEADERS | response_tokens | {"content-length"}:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        except (ValueError, OSError, http.client.HTTPException):
            self._deny()
        finally:
            self.close_connection = True
            if upstream is not None:
                upstream.close()

    do_HEAD = do_GET

    def do_CONNECT(self) -> None:
        upstream = None
        established = False
        try:
            if any(character in self.path for character in "/?#@\\"):
                raise ValueError("Invalid CONNECT authority.")
            target = self.server.guard.authorize("https://" + self.path)
            upstream = self.server.guard.connect(target)
            self.send_response(200, "Connection established")
            self.end_headers()
            established = True
            deadline = time.monotonic() + 30
            transferred = 0
            while time.monotonic() < deadline:
                readable, _, _ = select.select([self.connection, upstream], [], [], 0.2)
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    transferred += len(data)
                    if transferred > 20 * 1024 * 1024:
                        return
                    destination = upstream if source is self.connection else self.connection
                    destination.sendall(data)
        except (ValueError, OSError):
            if not established:
                self._deny()
        finally:
            self.close_connection = True
            if upstream is not None:
                upstream.close()

    def do_POST(self) -> None:
        self._deny(405)

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST
    do_OPTIONS = do_POST


class EgressProxy:
    """Own a loopback-only proxy listener for one browser run."""

    def __init__(self, guard: DestinationGuard) -> None:
        self.server = _ProxyServer(("127.0.0.1", 0), _ProxyHandler)
        self.server.guard = guard
        self.thread = Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def chromium_proxy_options(proxy_url: str) -> dict:
    """Route Chromium HTTP(S) traffic through the fixed proxy, including loopback."""
    return {
        **({'chromium_sandbox':True} if os.environ.get('ADAPTIVE_QA_HOSTED_SANDBOX')=='1' else {}),
        "proxy": {"server": proxy_url, "bypass": "<-loopback>"},
        "args": ["--disable-quic", "--disable-http2",
                 "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"],
    }
