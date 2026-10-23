"""Internal, supervised document checks; dashboard activation is separate."""

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import uuid4

from adaptive_qa.browser_process import _read_result, _terminate_process_tree
from adaptive_qa.config import ProjectConfig
from adaptive_qa.discovery_target import validate_discovery_project, validate_discovery_url
from adaptive_qa.document_checks import DOCUMENT_CHECKS
from adaptive_qa.egress import DestinationGuard, EgressProxy, chromium_proxy_options
from adaptive_qa.models import TestResult, TestStatus


def _validate(case_id, project, profile):
    if case_id not in DOCUMENT_CHECKS:
        raise ValueError('Only independent document checks are supported.')
    validate_discovery_project(project, profile)


def _execute(case_id, project, profile, evidence_root):
    from playwright.sync_api import sync_playwright, Error
    from adaptive_qa.local_browser import _capture_evidence
    started = perf_counter()
    evidence = evidence_root / (uuid4().hex + '.png')
    denied = 0
    guard = DestinationGuard(project, local_sample=profile == 'controlled_local', max_requests=100)
    def route_request(route):
        nonlocal denied
        try:
            if route.request.method not in ('GET', 'HEAD'):
                raise ValueError('Read-only methods are required.')
            validate_discovery_url(route.request.url, project, profile)
        except ValueError:
            denied += 1
            route.abort('blockedbyclient')
        else:
            route.continue_()
    try:
        with EgressProxy(guard) as proxy, sync_playwright() as playwright:
            browser = playwright.chromium.launch(timeout=10000, **chromium_proxy_options(proxy.url))
            try:
                context = browser.new_context(service_workers='block', accept_downloads=False)
                try:
                    context.set_default_timeout(3000)
                    context.set_default_navigation_timeout(10000)
                    context.route('**/*', route_request)
                    context.route_web_socket('**/*', lambda connection: connection.close())
                    page = context.new_page()
                    try:
                        response = page.goto(project.base_url, wait_until='domcontentloaded')
                        if (response is None or response.status != 200 or page.url != project.base_url
                                or 'text/html' not in response.headers.get('content-type', '').lower()):
                            raise RuntimeError('The bound HTML document was not loaded.')
                        DOCUMENT_CHECKS[case_id](page)
                        # Missing resources must never produce a passing document verdict.
                        if denied or guard.denied or page.url != project.base_url:
                            raise RuntimeError('Network coverage is incomplete.')
                    finally:
                        _capture_evidence(page, evidence)
                finally:
                    context.close()
            finally:
                browser.close()
    except AssertionError:
        status = TestStatus.ERROR if denied or guard.denied else TestStatus.FAILED
    except (Error, RuntimeError, OSError, ValueError):
        status = TestStatus.ERROR
    else:
        status = TestStatus.PASSED
    messages = {TestStatus.PASSED: 'The independent document check passed.',
                TestStatus.FAILED: 'The independent document assertion failed.',
                TestStatus.ERROR: 'Document loading, coverage or execution was incomplete.'}
    return TestResult(case_id, status, perf_counter()-started, messages[status],
                      evidence_paths=(evidence.as_posix(),) if evidence.is_file() else ())


def run_isolated_document_test(case_id, project, *, profile='public_https', timeout_seconds=30,
                               should_cancel=None, evidence_directory):
    """Trusted orchestration only; validates without DNS before starting a child."""
    _validate(case_id, project, profile)
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 120):
        raise ValueError('A finite deadline of at most 120 seconds is required.')
    root = Path(evidence_directory).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('An existing private evidence directory is required.')
    started = perf_counter()
    def outcome(status, message):
        return TestResult(case_id, status, perf_counter()-started, message)
    if should_cancel is not None and should_cancel():
        return outcome(TestStatus.CANCELLED, 'Document execution was cancelled.')
    with TemporaryDirectory(prefix='adaptive-qa-document-') as temporary:
        config, output = Path(temporary)/'input.json', Path(temporary)/'result.json'
        data = json.dumps({'project': asdict(project), 'profile': profile}, ensure_ascii=True)
        if len(data.encode('utf-8')) > 16384:
            raise ValueError('Document configuration is too large.')
        config.write_text(data, encoding='utf-8')
        options = {'start_new_session': True} if os.name != 'nt' else {
            'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        command = [sys.executable, '-m', 'adaptive_qa.document_process', '--input', str(config),
                   '--output', str(output), '--case', case_id, '--evidence', str(root)]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
        try:
            while True:
                if should_cancel is not None and should_cancel():
                    return outcome(TestStatus.CANCELLED, 'Document execution was cancelled.')
                remaining = timeout_seconds - (perf_counter()-started)
                if remaining <= 0:
                    return outcome(TestStatus.ERROR, 'Document execution exceeded its deadline.')
                try:
                    process.wait(timeout=min(0.2, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode != 0:
                return outcome(TestStatus.ERROR, 'Document child exited unexpectedly.')
            try:
                if output.stat().st_size > 16384:
                    raise ValueError('Oversized result.')
                result = _read_result(output, expected_case_id=case_id)
                for evidence in result.evidence_paths:
                    candidate = Path(evidence).resolve(strict=True)
                    if candidate.parent != root or not candidate.is_file() or candidate.suffix != '.png':
                        raise ValueError('Evidence escaped the private directory.')
                return result
            except (OSError, ValueError, TypeError, KeyError):
                return outcome(TestStatus.ERROR, 'Document child returned an invalid result.')
        finally:
            if process.poll() is None:
                _terminate_process_tree(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=tuple(DOCUMENT_CHECKS), required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    if args.input.stat().st_size > 16384:
        raise ValueError('Oversized configuration.')
    data = json.loads(args.input.read_text(encoding='utf-8'))
    if set(data) != {'project', 'profile'}:
        raise ValueError('Invalid configuration.')
    project_data = data['project']
    project_data['allowed_hosts'] = tuple(project_data['allowed_hosts'])
    project = ProjectConfig(**project_data)
    _validate(args.case, project, data['profile'])
    root = args.evidence.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Invalid evidence directory.')
    result = _execute(args.case, project, data['profile'], root)
    args.output.write_text(json.dumps(asdict(result)), encoding='utf-8')


if __name__ == '__main__':
    main()
