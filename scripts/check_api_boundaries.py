"""Real API denial, redaction, hostile-response, deadline, and cancellation checks."""

from dataclasses import asdict, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Thread
from time import perf_counter
from unittest.mock import patch
from uuid import uuid4

from adaptive_qa.api_catalog import API_BY_ID
from adaptive_qa.api_models import ApiConfiguration, ApiRequest, JsonCheck, JsonOperator
from adaptive_qa.api_process import run_isolated_api_case
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestStatus
from adaptive_qa.sample_api import create_sample_api
from adaptive_qa.secrets import SecretReference


class Canary(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.contacts += 1
        self.send_response(200)
        self.send_header('Content-Length', '0')
        self.end_headers()


def main():
    canary = ThreadingHTTPServer(('127.0.0.1', 0), Canary)
    canary.contacts = 0
    canary_thread = Thread(target=canary.serve_forever, daemon=True)
    canary_thread.start()
    token, wrong_token = uuid4().hex + uuid4().hex, uuid4().hex + uuid4().hex
    server = create_sample_api(token, redirect_target=f'http://127.0.0.1:{canary.server_port}/forbidden')
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    configuration = ApiConfiguration(ProjectConfig('api', 'API Boundaries',
        'http://127.0.0.1:8000', ('127.0.0.1',)), SecretReference('QA_BOUNDARY_API_TOKEN'))
    def probe(name, path, *, authenticated=False, checks=()):
        base = API_BY_ID['API-001']
        return replace(base, definition=replace(base.definition, case_id='API-CHECK-' + name.upper()),
                       request=ApiRequest(path, use_authentication=authenticated), checks=checks)
    def check(name, case, expected, config=configuration, **options):
        result = run_isolated_api_case(case, config, **options)
        assert result.status == expected, (name, result)
        results.append({'name': name, 'expected': expected.value, 'result': asdict(result)})
        return result
    try:
        with patch.dict(os.environ, {'QA_BOUNDARY_API_TOKEN': token}):
            before = len(server.operations)
            check('missing configuration', API_BY_ID['API-001'], TestStatus.BLOCKED, None)
            check('mutation policy', API_BY_ID['API-014'], TestStatus.BLOCKED)
            check('authentication configuration', API_BY_ID['API-010'], TestStatus.BLOCKED,
                  replace(configuration, bearer_token=None))
            with patch.dict(os.environ, {'QA_BOUNDARY_API_TOKEN': ''}):
                check('missing authentication secret', API_BY_ID['API-010'], TestStatus.BLOCKED)
            with patch.dict(os.environ, {'QA_BOUNDARY_API_TOKEN': 'private\r\nInjected: value'}):
                check('header injection', API_BY_ID['API-010'], TestStatus.BLOCKED)
            assert len(server.operations) == before
            with patch.dict(os.environ, {'QA_BOUNDARY_API_TOKEN': wrong_token}):
                check('invalid server token', API_BY_ID['API-010'], TestStatus.FAILED)
            check('reflected secret redaction', probe('reflect', '/api/reflect', authenticated=True,
                  checks=(JsonCheck(('value',), JsonOperator.EXISTS),)), TestStatus.PASSED)
            check('response limit', probe('size', '/api/oversized'), TestStatus.ERROR,
                  replace(configuration, max_response_bytes=1024))
            for name, path in (('malformed JSON', '/api/malformed'), ('duplicate keys', '/api/duplicate'),
                               ('float overflow', '/api/overflow'), ('wrong media type', '/api/text')):
                check(name, probe(name.replace(' ', '-'), path), TestStatus.FAILED)
            check('encoded response', probe('encoding', '/api/encoded'), TestStatus.ERROR)
            check('redirect does not forward', API_BY_ID['API-020'], TestStatus.PASSED)
            assert canary.contacts == 0
            for name, path in (('headers', '/api/slow-headers'), ('body', '/api/slow-body')):
                started = perf_counter()
                result = check('total deadline ' + name, probe('slow-' + name, path), TestStatus.ERROR,
                               timeout_seconds=1)
                assert 'total time limit' in result.message and perf_counter() - started < 5
                assert ('GET', path) in server.operations
            outside = ApiConfiguration(ProjectConfig('api', 'API', 'https://example.com', ('example.com',)))
            check('nonlocal execution disabled', API_BY_ID['API-001'], TestStatus.BLOCKED, outside)
            before = len(server.operations)
            check('prestart cancellation', API_BY_ID['API-001'], TestStatus.CANCELLED, should_cancel=lambda: True)
            assert len(server.operations) == before
            baseline = server.operations.count(('GET', '/api/slow-headers'))
            check('active cancellation', probe('cancel', '/api/slow-headers'), TestStatus.CANCELLED,
                  should_cancel=lambda: server.operations.count(('GET', '/api/slow-headers')) > baseline)
            check('socket idle timeout', probe('stall', '/api/stall'), TestStatus.ERROR,
                  replace(configuration, timeout_seconds=0.1))
        report = {'checks': len(results), 'passed': True, 'canary_contacts': canary.contacts,
                  'results': results, 'operations': server.operations}
        serialized = json.dumps(report, indent=2)
        assert token not in serialized and wrong_token not in serialized
        assert 'Authorization' not in serialized and 'X-Debug-Token' not in serialized
        path = Path('artifacts/api/boundaries.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding='utf-8')
        print(f'{len(results)} API boundary checks passed; canary contacts=0 and reports are redacted.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        canary.shutdown()
        canary.server_close()
        canary_thread.join(timeout=5)


if __name__ == '__main__':
    main()
