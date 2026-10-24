"""Explicit reusable API assertions on contrasting owned endpoints only."""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json

from check_owned_submission import server
from adaptive_qa.api_models import ApiCase, ApiRequest, JsonCheck, JsonOperator
from adaptive_qa.config import ProjectConfig
from adaptive_qa.local_api_review import review_local_api, run_reviewed_local_api
from adaptive_qa.models import TestCase, TestType, TestStatus


def main():
    contacts = []
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            contacts.append(self.path)
            assert self.path in ('/service/available', '/other/readiness')
            raw = b'{"available":true}' if self.path.startswith('/service') else b'{"ready":false}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers(); self.wfile.write(raw)

    project = ProjectConfig('a'*32, 'Owned reusable API', 'http://127.0.0.1:8000', ('127.0.0.1',), False)
    definition = TestCase('LOCAL-API-READ', 'Explicit response assertion', TestType.API,
                         ('api',), ('Read one explicitly configured endpoint',), 'Match the declared boolean')
    results = []
    with server(Fixture, 8000):
        for path, field, expected, status in (
            ('/service/available', 'available', True, TestStatus.PASSED),
            ('/other/readiness', 'ready', False, TestStatus.PASSED),
            ('/other/readiness', 'ready', True, TestStatus.FAILED),
        ):
            case = ApiCase(definition, ApiRequest(path), 200,
                           (JsonCheck((field,), JsonOperator.EQUALS, expected),))
            before = len(contacts)
            review = review_local_api(project, case)
            assert len(contacts) == before
            result = run_reviewed_local_api(review, project, confirmed_fingerprint=review.fingerprint)
            assert result.status == status and len(contacts) == before+1
            assert result.evidence_paths == ()
            results.append(result.status.value)
        before = len(contacts)
        try:
            run_reviewed_local_api(review, replace(project, name='Changed'), confirmed_fingerprint=review.fingerprint)
            raise AssertionError('Changed project accepted')
        except ValueError: pass
        cancelled = run_reviewed_local_api(review, project, confirmed_fingerprint=review.fingerprint, should_cancel=lambda: True)
        assert cancelled.status == TestStatus.CANCELLED and len(contacts) == before
    report = dict(owned_loopback_only=True, configured_assertions=results, requests=len(contacts),
                  review_requests=0, stale_dispatches=0, cancellation_requests=0,
                  authentication_used=False, raw_responses_persisted=False, catalog_expanded=False)
    output = Path('artifacts/api'); output.mkdir(parents=True, exist_ok=True)
    (output/'reusable-review.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__': main()
