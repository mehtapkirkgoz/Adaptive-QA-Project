"""Isolated discovery restricted to the controlled local sample target."""

import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

from adaptive_qa.browser_process import _terminate_process_tree
from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlBudget, CrawlResult, crawl_pages
from adaptive_qa.egress import DestinationGuard, EgressProxy, chromium_proxy_options
from adaptive_qa.page_collector import collect_page_snapshot
from adaptive_qa.targets import validate_local_sample_target
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.planning import build_test_plan
from adaptive_qa.document_target import validate_document_path
from adaptive_qa.discovery_target import validate_discovery_project, validate_discovery_url


_LOCAL_PROJECT = ProjectConfig('local-discovery', 'Local Discovery',
                               'http://127.0.0.1:8000', ('127.0.0.1',))


def _failed_discovery(reason: str, project=_LOCAL_PROJECT) -> dict:
    crawl = CrawlResult((), 0, (reason,))
    payload = {**asdict(crawl), 'plan': asdict(build_test_plan(crawl, TEST_CASES, project)),
               'scope': 'inspected_pages_only'}
    return json.loads(json.dumps(payload))


def _collect_sample(budget: CrawlBudget, start_path='/') -> dict:
    validate_document_path('DOC-001', start_path)
    project = replace(_LOCAL_PROJECT, base_url='http://127.0.0.1:8000'+start_path)
    return _collect_project(project, budget, 'controlled_local')


def _collect_project(project, budget, profile):
    validate_discovery_project(project, profile)
    guard = DestinationGuard(project, local_sample=profile == 'controlled_local', max_requests=budget.max_requests)
    def authorize(url):
        return validate_discovery_url(url, project, profile)
    with EgressProxy(guard) as proxy, sync_playwright() as playwright:
        browser = playwright.chromium.launch(timeout=10000, **chromium_proxy_options(proxy.url))
        try:
            context = browser.new_context(service_workers='block', accept_downloads=False)
            denied_routes = 0
            def route_request(route):
                nonlocal denied_routes
                try:
                    if route.request.method not in ('GET', 'HEAD'):
                        raise ValueError('Only read requests are allowed.')
                    authorize(route.request.url)
                except ValueError:
                    denied_routes += 1
                    route.abort('blockedbyclient')
                else:
                    route.continue_()
            context.route('**/*', route_request)
            context.route_web_socket('**/*', lambda connection: connection.close())
            page = context.new_page()
            def load(url, remaining):
                response = page.goto(url, wait_until='domcontentloaded',
                                     timeout=max(1, min(10000, remaining * 1000)))
                if response is None or not 200 <= response.status < 300:
                    raise RuntimeError('Page did not return a successful response.')
                authorize(page.url)
                return collect_page_snapshot(page)
            result = crawl_pages(project.base_url, budget, authorize=authorize, load=load)
            limitations = set(result.limitations)
            if guard.requests > budget.max_requests:
                limitations.add('request_limit')
            if guard.denied or denied_routes:
                limitations.add('network_policy_denial')
            plan = build_test_plan(replace(result, limitations=tuple(sorted(limitations))), TEST_CASES, project)
            return {**asdict(result), 'limitations': sorted(limitations), 'plan': asdict(plan),
                    'requests': min(guard.requests, budget.max_requests),
                    'request_authorization_attempts': guard.requests,
                    'scope': 'inspected_pages_only'}
        finally:
            browser.close()


def discover_local_sample(budget: CrawlBudget = CrawlBudget(), *, should_cancel=None, start_path='/') -> dict:
    validate_document_path('DOC-001', start_path)
    project = replace(_LOCAL_PROJECT, base_url='http://127.0.0.1:8000'+start_path)
    return discover_configured_target(project, budget, profile='controlled_local', should_cancel=should_cancel)


def discover_configured_target(project, budget=CrawlBudget(), *, profile='public_https', should_cancel=None):
    """Trusted worker entry point; no dashboard/public activation is implied."""
    if not isinstance(budget, CrawlBudget):
        raise ValueError('budget must be a CrawlBudget.')
    validate_discovery_project(project, profile)
    if should_cancel is not None and not callable(should_cancel):
        raise ValueError('Cancellation must be a trusted callback.')
    if should_cancel is not None and should_cancel():
        return {**_failed_discovery('cancelled', project), 'partial_results_discarded': True}
    started = monotonic()
    failure = _failed_discovery('discovery_process_error', project)
    with TemporaryDirectory(prefix='adaptive-qa-discovery-') as directory:
        output = Path(directory) / 'result.json'
        configuration = Path(directory) / 'input.json'
        encoded = json.dumps({'profile': profile, 'project': asdict(project)}, allow_nan=False).encode('utf-8')
        if len(encoded) > 16384:
            raise ValueError('Discovery configuration exceeds its limit.')
        configuration.write_bytes(encoded)
        options = {'start_new_session': True} if os.name != 'nt' else {
            'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        command = [
            sys.executable, '-m', 'adaptive_qa.local_discovery', '--child-output', str(output),
            '--budget', json.dumps(asdict(budget)),
        ]
        command += ['--project-input', str(configuration)]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
        try:
            while process.poll() is None:
                if should_cancel is not None and should_cancel():
                    _terminate_process_tree(process)
                    return {**_failed_discovery('cancelled', project), 'partial_results_discarded': True}
                remaining = budget.timeout_seconds - (monotonic() - started)
                if remaining <= 0:
                    _terminate_process_tree(process)
                    return {**_failed_discovery('time_limit', project), 'partial_results_discarded': True}
                try:
                    process.wait(timeout=min(0.1, remaining))
                except subprocess.TimeoutExpired:
                    pass
            if should_cancel is not None and should_cancel():
                return {**_failed_discovery('cancelled', project), 'partial_results_discarded': True}
            if monotonic() - started >= budget.timeout_seconds:
                return {**_failed_discovery('time_limit', project), 'partial_results_discarded': True}
            if process.returncode != 0:
                return failure
            try:
                if output.stat().st_size > 2000000:
                    return failure
                payload = json.loads(output.read_text(encoding='utf-8'))
                if (not isinstance(payload, dict) or not isinstance(payload.get('pages'), list)
                        or not isinstance(payload.get('limitations'), list)):
                    return failure
                return payload
            except (OSError, ValueError):
                return failure
        finally:
            if process.poll() is None:
                _terminate_process_tree(process)


def main():
    parser = argparse.ArgumentParser(description='Discover the controlled local sample only.')
    parser.add_argument('--child-output', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--budget', help=argparse.SUPPRESS)
    parser.add_argument('--start-path', default='/', help=argparse.SUPPRESS)
    parser.add_argument('--project-input', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child_output is not None:
        budget = CrawlBudget(**json.loads(args.budget))
        if args.project_input is None:
            result = _collect_sample(budget, args.start_path)
        else:
            if args.project_input.stat().st_size > 16384:
                raise ValueError('Oversized discovery input.')
            data = json.loads(args.project_input.read_text(encoding='utf-8'))
            if set(data) != {'profile', 'project'} or not isinstance(data['project'], dict):
                raise ValueError('Invalid discovery input.')
            values = data['project']
            if not isinstance(values.get('allowed_hosts'), list):
                raise ValueError('Invalid discovery hosts.')
            project = ProjectConfig(**{**values, 'allowed_hosts': tuple(values['allowed_hosts'])})
            result = _collect_project(project, budget, data['profile'])
        args.child_output.write_text(json.dumps(result), encoding='utf-8')
    else:
        result = discover_local_sample()
        print(json.dumps(result, indent=2))
        if not result['pages']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
