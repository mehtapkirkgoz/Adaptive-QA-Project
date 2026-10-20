"""Compare real guarded discovery and test plans across controlled fixture sites."""

from dataclasses import asdict
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlBudget, CrawlResult
from adaptive_qa.discovery import CommerceSnapshot, FieldSnapshot, FormSnapshot, LinkSnapshot, PageSnapshot
from adaptive_qa.local_discovery import discover_local_sample
from adaptive_qa.models import TestCase, TestType
from adaptive_qa.planning import build_test_plan


EXPECTED = {
    'plain': ('absent', 'absent', 'absent', 'absent', 'absent'),
    'account': ('present', 'present', 'present', 'absent', 'absent'),
    'store': ('unknown', 'absent', 'present', 'present', 'present'),
    'ambiguous': ('unknown', 'unknown', 'unknown', 'unknown', 'unknown'),
}
FEATURES = ('login', 'search', 'registration', 'product', 'cart')
CASES = tuple(TestCase(f'DISC-{name.upper()}', f'Inspect {name} structure', TestType.UI,
                       (name,), ('Inspect discovered structural evidence',),
                       f'Visible structural evidence confirms {name}.') for name in FEATURES)


def snapshot(payload):
    """Reconstruct immutable discovery models from the local child transport."""
    return PageSnapshot(payload['url'],
        forms=tuple(FormSnapshot(**{**form,
            'fields': tuple(FieldSnapshot(**item) for item in form['fields']),
            'buttons': tuple(form['buttons'])}) for form in payload['forms']),
        links=tuple(LinkSnapshot(**link) for link in payload['links']),
        collection_complete=payload['collection_complete'],
        commerce=tuple(CommerceSnapshot(**{**region, 'actions': tuple(region['actions'])})
                       for region in payload['commerce']))


class RecordingHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def handle_one_request(self):
        super().handle_one_request()
        if hasattr(self, 'command'):
            self.server.methods.append(self.command)


def main():
    root = Path(__file__).resolve().parents[1]
    project = ProjectConfig('acceptance', 'Discovery Acceptance',
                            'http://127.0.0.1:8000', ('127.0.0.1',))
    report = {'schema_version': 1, 'fixtures': {}, 'execution_performed': False}
    for name, expected in EXPECTED.items():
        directory = root / 'samples/discovery' / name
        server = ThreadingHTTPServer(('127.0.0.1', 8000), partial(RecordingHandler, directory=str(directory)))
        server.methods = []
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = discover_local_sample(CrawlBudget(max_pages=10, max_requests=100))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        assert result['pages'], (name, result)
        assert not result['limitations'], (name, result['limitations'])
        assert result['attempted_pages'] == (4 if name == 'store' else 1), (name, result)
        assert 0 < result['requests'] <= 100
        assert server.methods and set(server.methods) <= {'GET', 'HEAD'}, (name, server.methods)
        crawl = CrawlResult(tuple(snapshot(page) for page in result['pages']),
                            result['attempted_pages'], tuple(result['limitations']))
        plan = build_test_plan(crawl, CASES, project)
        statuses = {item.feature: item.status.value for item in plan.assessment.features}
        assert statuses == dict(zip(FEATURES, expected)), (name, statuses)
        assert not plan.execution_authorized
        decisions = {'present': 'selected', 'absent': 'skipped', 'unknown': 'blocked'}
        for case, status in zip(plan.cases, expected):
            assert case.decision.value == decisions[status], (name, case)
            assert case.reason
            if case.decision == 'selected':
                assert case.target_url and case.evidence
                assert project.is_url_allowed(case.target_url)
            else:
                assert case.target_url is None
        if name == 'store':
            targets = {case.case_id: case.target_url for case in plan.cases}
            for feature, path in (('registration', 'register'), ('product', 'product'), ('cart', 'cart')):
                assert targets[f'DISC-{feature.upper()}'] == f'http://127.0.0.1:8000/{path}.html'
        report['fixtures'][name] = {
            'result': result, 'acceptance_plan': asdict(plan), 'methods': server.methods,
            'fixture_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sorted(directory.glob('*.html'))},
        }
        print(f'{name}: feature states, decisions, evidence, and read-only requests passed.')
    destination = root / 'artifacts/discovery/acceptance.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Four contrasting discovery fixtures passed.')


if __name__ == '__main__':
    main()
