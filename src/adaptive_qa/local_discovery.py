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


_LOCAL_PROJECT = ProjectConfig('local-discovery', 'Local Discovery',
                               'http://127.0.0.1:8000', ('127.0.0.1',))


def _failed_discovery(reason: str) -> dict:
    crawl = CrawlResult((), 0, (reason,))
    payload = {**asdict(crawl), 'plan': asdict(build_test_plan(crawl, TEST_CASES, _LOCAL_PROJECT)),
               'scope': 'inspected_pages_only'}
    return json.loads(json.dumps(payload))


def _collect_sample(budget: CrawlBudget, start_path='/') -> dict:
    validate_document_path('DOC-001', start_path)
    project = replace(_LOCAL_PROJECT, base_url='http://127.0.0.1:8000'+start_path)
    guard = DestinationGuard(project, local_sample=True, max_requests=budget.max_requests)
    def authorize(url):
        return validate_local_sample_target(url, project)
    with EgressProxy(guard) as proxy, sync_playwright() as playwright:
        browser = playwright.chromium.launch(timeout=10000, **chromium_proxy_options(proxy.url))
        try:
            context = browser.new_context(service_workers='block', accept_downloads=False)
            def route_request(route):
                try:
                    if route.request.method not in ('GET', 'HEAD'):
                        raise ValueError('Only read requests are allowed.')
                    authorize(route.request.url)
                except ValueError:
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
            if guard.denied:
                limitations.add('network_policy_denial')
            plan = build_test_plan(replace(result, limitations=tuple(sorted(limitations))), TEST_CASES, project)
            return {**asdict(result), 'limitations': sorted(limitations), 'plan': asdict(plan),
                    'requests': min(guard.requests, budget.max_requests),
                    'request_authorization_attempts': guard.requests,
                    'scope': 'inspected_pages_only'}
        finally:
            browser.close()


def discover_local_sample(budget: CrawlBudget = CrawlBudget(), *, should_cancel=None, start_path='/') -> dict:
    """Run with a hard process deadline; return explicit failure limitations."""
    if not isinstance(budget, CrawlBudget):
        raise ValueError('budget must be a CrawlBudget.')
    validate_document_path('DOC-001', start_path)
    if should_cancel is not None and not callable(should_cancel):
        raise ValueError('Cancellation must be a trusted callback.')
    if should_cancel is not None and should_cancel():
        return {**_failed_discovery('cancelled'), 'partial_results_discarded': True}
    started = monotonic()
    failure = _failed_discovery('discovery_process_error')
    with TemporaryDirectory(prefix='adaptive-qa-discovery-') as directory:
        output = Path(directory) / 'result.json'
        options = {'start_new_session': True} if os.name != 'nt' else {
            'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        command = [
            sys.executable, '-m', 'adaptive_qa.local_discovery', '--child-output', str(output),
            '--budget', json.dumps(asdict(budget)),
        ]
        if start_path != '/':
            command += ['--start-path', start_path]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
        try:
            while process.poll() is None:
                if should_cancel is not None and should_cancel():
                    _terminate_process_tree(process)
                    return {**_failed_discovery('cancelled'), 'partial_results_discarded': True}
                remaining = budget.timeout_seconds - (monotonic() - started)
                if remaining <= 0:
                    _terminate_process_tree(process)
                    return {**_failed_discovery('time_limit'), 'partial_results_discarded': True}
                try:
                    process.wait(timeout=min(0.1, remaining))
                except subprocess.TimeoutExpired:
                    pass
            if should_cancel is not None and should_cancel():
                return {**_failed_discovery('cancelled'), 'partial_results_discarded': True}
            if monotonic() - started >= budget.timeout_seconds:
                return {**_failed_discovery('time_limit'), 'partial_results_discarded': True}
            if process.returncode != 0:
                return failure
            try:
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
    args = parser.parse_args()
    if args.child_output is not None:
        result = _collect_sample(CrawlBudget(**json.loads(args.budget)), args.start_path)
        args.child_output.write_text(json.dumps(result), encoding='utf-8')
    else:
        result = discover_local_sample()
        print(json.dumps(result, indent=2))
        if not result['pages']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
