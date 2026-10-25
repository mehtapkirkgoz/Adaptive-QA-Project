"""Internal one-shot HTTPS submission transport; not connected to queues or the UI."""
from dataclasses import dataclass, replace
import hmac
import http.client
import json
import re
import ssl
from threading import Lock
from time import monotonic
from urllib.parse import parse_qsl, urlsplit

from adaptive_qa.egress import DestinationGuard
from adaptive_qa.local_form_binding import _unique
from adaptive_qa.owned_submission import CONTENT_TYPE, OwnedSubmissionResult
from adaptive_qa.public_form_proposal import PublicFormProposal


@dataclass(frozen=True)
class ReviewedPublicForm:
    """Internal confirmation wrapper, not proof of human identity or endpoint ownership."""
    proposal: PublicFormProposal
    confirmed_fingerprint: str

    def __post_init__(self):
        if (not isinstance(self.proposal, PublicFormProposal)
                or not isinstance(self.confirmed_fingerprint, str)
                or not re.fullmatch('[0-9a-f]{64}', self.confirmed_fingerprint)
                or not hmac.compare_digest(self.confirmed_fingerprint, self.proposal.fingerprint())):
            raise ValueError('Confirmation must match the exact proposal fingerprint.')

    def validate_project(self, project, *, current_fingerprint):
        self.proposal.validate_project(project, current_fingerprint=current_fingerprint)
        if not hmac.compare_digest(self.confirmed_fingerprint, self.proposal.fingerprint()):
            raise ValueError('The reviewed proposal changed.')


class PublicSubmissionGate:
    """Consume one attempted request, including malformed requests, without resolving inputs."""
    def __init__(self, review, project, *, current_fingerprint):
        if not isinstance(review, ReviewedPublicForm):
            raise ValueError('A separately confirmed public form review is required.')
        review.validate_project(project, current_fingerprint=current_fingerprint)
        self.proposal = review.proposal
        self._lock, self._consumed = Lock(), False

    def admit(self, *, url, method, content_type, body):
        with self._lock:
            if self._consumed:
                return False
            self._consumed = True
        if (url != self.proposal.endpoint_url or method != 'POST'
                or content_type not in (CONTENT_TYPE, CONTENT_TYPE+';charset=UTF-8')
                or type(body) is not bytes or not 1 <= len(body) <= 8192):
            return False
        try:
            encoded = body.decode('ascii')
            if re.search(r'%(?![0-9a-fA-F]{2})', encoded):
                return False
            pairs = parse_qsl(encoded, keep_blank_values=True, strict_parsing=True,
                              encoding='utf-8', errors='strict', max_num_fields=len(self.proposal.field_names))
            return (tuple(name for name, _ in pairs) == self.proposal.field_names
                    and all(1 <= len(value) <= 512 and not any(ord(c) < 32 or ord(c) == 127 for c in value)
                            for _, value in pairs))
        except (ValueError, UnicodeError):
            return False

    def classify_response(self, status, raw):
        if type(raw) is not bytes or len(raw) > 1024:
            return None
        try:
            payload = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique)
            if type(payload) is not dict or len(payload) != 1:
                return None
            for outcome, expected in (('accepted', self.proposal.accepted), ('rejected', self.proposal.rejected)):
                if (status == expected.status_code and set(payload) == {expected.field_name}
                        and type(payload[expected.field_name]) is bool
                        and payload[expected.field_name] is expected.expected_value):
                    return outcome
        except (ValueError, UnicodeError, RecursionError):
            pass
        return None


class PublicSubmissionTransport:
    """Use only inside a future supervised child; socket timeouts are not a hard total deadline.

    No production connector/TLS override, ambient cookies/proxies, redirect following
    or retry exists. Only tests may redirect an already validated numeric peer to
    an owned TLS harness. No HTTP route or local worker admits this transport yet.
    """
    def __init__(self, review, project, *, current_fingerprint):
        self._gate = PublicSubmissionGate(review, project, current_fingerprint=current_fingerprint)
        self._guard = DestinationGuard(project, local_sample=False, max_requests=1)
        self._timeout = review.proposal.form.timeout_seconds
        self._prepare_lock, self._prepared, self._target = Lock(), False, None

    def prepare_destination(self):
        """Internal child preflight before resolving references; cache the checked peer."""
        with self._prepare_lock:
            if not self._prepared:
                self._prepared = True
                try:
                    self._target = self._guard.authorize(self._gate.proposal.endpoint_url)
                except (ValueError, OSError):
                    pass
            return self._target is not None

    def submit(self, *, url, method, content_type, body):
        if not self._gate.admit(url=url, method=method, content_type=content_type, body=body):
            return OwnedSubmissionResult('blocked', 0)
        if not self.prepare_destination():
            return OwnedSubmissionResult('blocked', 0)
        target = self._target
        connection, delivery_started = None, False
        deadline = monotonic()+self._timeout
        try:
            connection = http.client.HTTPConnection(target.hostname, target.port, timeout=self._timeout)
            connection.auto_open = 0
            # Validate the whole DNS answer set, then attempt one numeric peer only.
            peer = replace(target, addresses=(target.addresses[0],))
            connection.sock = self._guard.connect(peer, timeout_seconds=min(2, self._timeout))
            remaining = deadline-monotonic()
            if remaining <= 0:
                raise TimeoutError()
            connection.sock.settimeout(remaining)
            context = ssl.create_default_context()
            context.keylog_filename = None  # Never inherit TLS key logging for form inputs.
            connection.sock = context.wrap_socket(connection.sock, server_hostname=target.hostname)
            remaining = deadline-monotonic()
            if remaining <= 0:
                raise TimeoutError()
            connection.sock.settimeout(remaining)
            delivery_started = True
            connection.request('POST', urlsplit(url).path, body=body, headers={
                'Host': target.hostname, 'Accept': 'application/json', 'Content-Type': content_type,
                'Content-Length': str(len(body)), 'Connection': 'close'})
            response = connection.getresponse()
            if (response.getheader('Content-Type') != 'application/json'
                    or response.getheader('Location') is not None
                    or response.getheader('Content-Encoding') is not None
                    or response.getheader('Transfer-Encoding') is not None):
                return OwnedSubmissionResult('error', 1)
            raw = response.read(1025)
            if monotonic() > deadline:
                raise TimeoutError()
            outcome = self._gate.classify_response(response.status, raw)
            return OwnedSubmissionResult(outcome or 'error', 1)
        except (OSError, ValueError, http.client.HTTPException):
            # A lost/partial POST response cannot establish whether the peer acted.
            return OwnedSubmissionResult('error', None if delivery_started else 0)
        finally:
            if connection is not None:
                connection.close()
