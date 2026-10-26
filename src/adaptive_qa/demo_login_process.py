"""Supervised exact-demo browser; no arbitrary-site or automatic URL admission."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from adaptive_qa.demo_login_contract import LOGIN, AUTHENTICATE, SECURE, LOGOUT, DemoLoginPlan, DemoLoginScenario
from adaptive_qa.demo_login_transport import DemoLoginTransport, demo_body
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.models import TestStatus
from adaptive_qa.public_submission_process import _run_private_child, SubmissionProcessResult


def _execute(plan, profile_directory):
    from playwright.sync_api import sync_playwright
    transport = DemoLoginTransport(plan)
    denied = []
    pending_redirect = []
    try:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(str(profile_directory),
                headless=True, java_script_enabled=False, service_workers='block',
                accept_downloads=False, proxy={'server': 'http://127.0.0.1:1'},
                args=['--disable-background-networking', '--disable-quic', '--disable-extensions'])
            try:
                page = context.pages[0]
                page.set_default_timeout(3000)
                def reject_popup(extra):
                    denied.append(True)
                    extra.close()
                context.on('page', reject_popup)
                def route_request(route):
                    request = route.request
                    if request.resource_type != 'document':
                        route.abort()
                        return
                    try:
                        if request.frame != page.main_frame or denied:
                            raise ValueError()
                        response = transport.request(request.method, request.url, request.post_data_buffer)
                        headers = {'content-type': 'text/html; charset=utf-8'}
                        if response.location:
                            # Browser redirects may bypass route interception. Keep its
                            # direct network dead; follow only the transport-validated
                            # transition explicitly after the current action finishes.
                            if pending_redirect: raise ValueError()
                            pending_redirect.append(response.location)
                            route.fulfill(status=200, headers=headers, body=b'')
                        else:
                            route.fulfill(status=response.status, headers=headers, body=response.body)
                    except Exception:
                        denied.append(True)
                        route.abort()
                context.route('**/*', route_request)
                context.route_web_socket('**/*', lambda socket: socket.close())
                def follow(expected):
                    if pending_redirect != [expected]: raise ValueError('Missing validated redirect.')
                    pending_redirect.clear()
                    page.goto(expected, wait_until='domcontentloaded', timeout=10000)
                page.goto(LOGIN, wait_until='domcontentloaded', timeout=10000)
                form = page.locator('form#login')
                if (form.count() != 1 or not form.is_visible()
                        or form.evaluate('el => el.method') != 'post'
                        or form.evaluate('el => el.action') != AUTHENTICATE
                        or form.locator('input[name="username"]').count() != 1
                        or form.locator('input[name="password"]').count() != 1):
                    return SubmissionProcessResult('blocked', 'preconditions_blocked', 0)
                form.locator('input[name="username"]').fill('tomsmith')
                from urllib.parse import parse_qsl
                password = dict(parse_qsl(demo_body(plan).decode()))['password']
                form.locator('input[name="password"]').fill(password)
                form.locator('button[type="submit"]').click()
                follow(plan.expected_document)
                page.wait_for_url(plan.expected_document, wait_until='domcontentloaded', timeout=10000)
                flash = page.locator('#flash')
                matched = (flash.count() == 1 and flash.is_visible()
                           and flash.inner_text().strip().startswith(plan.expected_message))
                if plan.scenario != DemoLoginScenario.REJECTED:
                    matched = matched and page.get_by_role('heading', name='Secure Area', exact=True).is_visible()
                else:
                    matched = matched and page.locator('form#login').is_visible()
                if not matched:
                    return SubmissionProcessResult('rejected', 'response_rejected', 1)
                if plan.scenario == DemoLoginScenario.LOGOUT:
                    link = page.locator('a[href="/logout"]')
                    if link.count() != 1 or not link.is_visible():
                        return SubmissionProcessResult('rejected', 'response_rejected', 1)
                    link.click()
                    follow(LOGIN)
                    page.wait_for_url(LOGIN, wait_until='domcontentloaded', timeout=10000)
                    if not page.locator('#flash').inner_text().strip().startswith('You logged out of the secure area!'):
                        return SubmissionProcessResult('rejected', 'response_rejected', 1)
                    page.goto(SECURE, wait_until='domcontentloaded', timeout=10000)
                    follow(LOGIN)
                    matched = (page.url == LOGIN and page.locator('form#login').is_visible()
                               and page.locator('#flash').inner_text().strip().startswith('You must login to view the secure area!'))
                if denied or not transport.complete:
                    return SubmissionProcessResult('error', 'transport_error', transport.attempted_submissions)
                return SubmissionProcessResult('accepted' if matched else 'rejected',
                    'response_accepted' if matched else 'response_rejected', 1)
            finally:
                context.close()
    except Exception:
        return SubmissionProcessResult('error', 'transport_error', None if transport.attempted_submissions else 0)
    finally:
        transport.close()


def _read_result(path):
    from adaptive_qa.public_submission_process import _read_result as read
    return read(path)


def run_isolated_demo_login(plan, *, timeout_seconds=45, should_cancel=None):
    if not isinstance(plan, DemoLoginPlan):
        raise ValueError('A typed demo plan is required.')
    result = _run_private_child(json.dumps({'scenario': plan.scenario.value}),
        module='adaptive_qa.demo_login_process', reader=_read_result,
        timeout_seconds=timeout_seconds, should_cancel=should_cancel)
    status = {'accepted': TestStatus.PASSED, 'rejected': TestStatus.FAILED,
              'blocked': TestStatus.BLOCKED, 'error': TestStatus.ERROR, 'cancelled': TestStatus.CANCELLED}[result.outcome]
    return InteractiveProbeResult(status, 'Authorized demo login scenario: '+status.value+'.', result.attempted_submissions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source, output = Path(args.input), Path(args.output)
    if (source.resolve() != source or output.resolve() != output or source.parent != output.parent
            or source.name != 'input.json' or output.name != 'result.json'
            or not source.is_file() or source.stat().st_nlink != 1 or output.exists()):
        raise ValueError('Private canonical sibling paths are required.')
    data = json.loads(source.read_bytes()[:1025])
    if not isinstance(data, dict) or set(data) != {'scenario'}:
        raise ValueError('Exact demo metadata is required.')
    result = _execute(DemoLoginPlan(DemoLoginScenario(data['scenario'])), source.parent/'browser-profile')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(asdict(result), stream)


if __name__ == '__main__':
    main()
