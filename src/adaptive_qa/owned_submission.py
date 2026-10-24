"""Non-networking admission for one POST to an explicitly bound owned fixture."""
from dataclasses import dataclass
import hashlib
import json
import re
from urllib.parse import parse_qsl

from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract

ORIGIN = "http://127.0.0.1:8000"
FIXTURE_OPERATIONS = {
    "login-transition": FormOperation.LOGIN,
    "login-rejected": FormOperation.LOGIN,
    "search-transition": FormOperation.SEARCH,
    "search-empty": FormOperation.SEARCH,
}
CONTENT_TYPE = "application/x-www-form-urlencoded"


@dataclass(frozen=True)
class OwnedSubmissionContract:
    """Exact metadata only; does not resolve inputs or grant a network connection."""
    form: InteractiveFormContract
    fixture_id: str
    document_url: str
    endpoint_url: str
    field_names: tuple[str, ...]

    def __post_init__(self):
        if (not isinstance(self.form, InteractiveFormContract)
                or not isinstance(self.fixture_id, str)
                or self.fixture_id not in FIXTURE_OPERATIONS
                or self.form.operation != FIXTURE_OPERATIONS[self.fixture_id]):
            raise ValueError("A typed matching owned fixture contract is required.")
        fields = ("user", "password") if self.form.operation == FormOperation.LOGIN else ("query",)
        if (self.document_url != ORIGIN + "/interactive/" + self.fixture_id
                or self.endpoint_url != ORIGIN + "/interactive-submit/" + self.fixture_id
                or type(self.field_names) is not tuple or self.field_names != fields):
            raise ValueError("Exact owned document, endpoint and field bindings are required.")

    @property
    def method(self):
        return "POST"

    @property
    def max_body_bytes(self):
        return 8192

    def validate_project(self, project, *, current_fingerprint):
        self.form.validate_project(project, current_fingerprint=current_fingerprint)
        if project.base_url != self.document_url or project.allowed_hosts != ("127.0.0.1",):
            raise ValueError("The saved project must match the owned document binding.")

    def fingerprint(self):
        payload = dict(form=self.form.fingerprint(), fixture=self.fixture_id,
                       document=self.document_url, endpoint=self.endpoint_url,
                       fields=self.field_names, method=self.method, content_types=(CONTENT_TYPE, CONTENT_TYPE+";charset=UTF-8"),
                       max_body_bytes=self.max_body_bytes, max_attempts=1, redirects=False)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class OwnedSubmissionGate:
    """Child-local one-shot validator; no retries, transport, persistence or plaintext output."""
    def __init__(self, contract, project, *, current_fingerprint):
        if not isinstance(contract, OwnedSubmissionContract):
            raise ValueError("A typed owned submission contract is required.")
        contract.validate_project(project, current_fingerprint=current_fingerprint)
        self.contract = contract
        self._consumed = False

    def admit(self, *, url, method, content_type, body):
        # Consume even a rejected attempt; never turn a blocked request into a retry.
        if self._consumed:
            return False
        self._consumed = True
        contract = self.contract
        if (url != contract.endpoint_url or method != contract.method
                or content_type not in (CONTENT_TYPE, CONTENT_TYPE+";charset=UTF-8") or type(body) is not bytes
                or not 1 <= len(body) <= contract.max_body_bytes):
            return False
        try:
            encoded = body.decode("ascii")
            if re.search(r"%(?![0-9a-fA-F]{2})", encoded):
                return False
            pairs = parse_qsl(encoded, keep_blank_values=True, strict_parsing=True,
                              encoding="utf-8", errors="strict", max_num_fields=len(contract.field_names))
            if tuple(name for name, _ in pairs) != contract.field_names:
                return False
            return all(1 <= len(value) <= 512 and not any(ord(c) < 32 or ord(c) == 127 for c in value)
                       for _, value in pairs)
        except (ValueError, UnicodeError):
            return False


@dataclass(frozen=True)
class OwnedSubmissionResult:
    outcome: str
    attempted_submissions: int | None

    def __post_init__(self):
        if (self.outcome not in ("accepted", "rejected", "blocked", "error")
                or (self.attempted_submissions is not None
                    and (type(self.attempted_submissions) is not int or self.attempted_submissions not in (0, 1)))
                or (self.outcome in ("accepted", "rejected") and self.attempted_submissions != 1)):
            raise ValueError("Invalid owned submission outcome.")


class OwnedSubmissionTransport:
    """One fixed local POST through a pinned peer; no cookies, redirects or retries.

    Instantiate only inside an owned supervised child. Socket timeouts bound I/O;
    the caller must still enforce the existing hard process deadline/cancellation.
    """
    def __init__(self, contract, project, *, current_fingerprint):
        from adaptive_qa.egress import DestinationGuard
        self._gate = OwnedSubmissionGate(contract, project, current_fingerprint=current_fingerprint)
        self._guard = DestinationGuard(project, local_sample=True, max_requests=1)

    def submit(self, *, url, method, content_type, body):
        import http.client
        from urllib.parse import urlsplit
        if not self._gate.admit(url=url, method=method, content_type=content_type, body=body):
            return OwnedSubmissionResult("blocked", 0)
        connection = None
        try:
            target = self._guard.authorize(url)
            parsed = urlsplit(url)
            connection = http.client.HTTPConnection(target.hostname, target.port, timeout=2)
            connection.sock = self._guard.connect(target, timeout_seconds=2)
            connection.request("POST", parsed.path, body=body, headers={
                "Host": "127.0.0.1:8000", "Content-Type": CONTENT_TYPE,
                "Content-Length": str(len(body)), "Connection": "close"})
            response = connection.getresponse()
            if (response.status not in (200, 401)
                    or response.getheader("Content-Type") != "application/json"
                    or response.getheader("Location") is not None
                    or response.getheader("Content-Encoding") is not None
                    or response.getheader("Transfer-Encoding") is not None):
                return OwnedSubmissionResult("error", 1)
            raw = response.read(1025)
            # Only fixed bytes are admitted; parsing arbitrary echoed JSON is unnecessary.
            expected = b'{"outcome":"accepted"}' if response.status == 200 else b'{"outcome":"rejected"}'
            if raw != expected:
                return OwnedSubmissionResult("error", 1)
            return OwnedSubmissionResult("accepted" if response.status == 200 else "rejected", 1)
        except Exception:
            # The peer may have processed the POST even if its response was lost.
            return OwnedSubmissionResult("error", None)
        finally:
            if connection is not None:
                connection.close()
