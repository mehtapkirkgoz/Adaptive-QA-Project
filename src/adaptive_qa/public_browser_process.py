"""Internal supervised reviewed HTTPS browser workflow; no HTTP/queue admission."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from urllib.parse import urlencode

from adaptive_qa.egress import DestinationGuard, EgressProxy, chromium_proxy_options
from adaptive_qa.discovery_target import validate_discovery_url
from adaptive_qa.form_configuration import decode_form_mappings
from adaptive_qa.interactive_process import _validate_mappings
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.local_form_binding import _unique
from adaptive_qa.models import TestStatus
from adaptive_qa.public_form_probe import probe_reviewed_public_form
from adaptive_qa.public_submission import PublicSubmissionTransport
from adaptive_qa.public_submission_process import (
    _encode as _encode_response, _decode as _decode_response, _run_private_child,
    _validate, SubmissionProcessResult)


INITIAL_ERROR = 'The reviewed browser could not load its guarded document.'
MESSAGES = {
    TestStatus.PASSED: {'The reviewed HTTP response and UI transition were verified.'},
    TestStatus.FAILED: {'The reviewed HTTP outcome did not match the expected workflow.',
                      'The reviewed response and UI transition were not both observed.'},
    TestStatus.BLOCKED: {'Reviewed form preconditions were not satisfied.'},
    TestStatus.ERROR: {'The reviewed form could not complete within its guarded scope.', INITIAL_ERROR},
}


def _encode(review, project, owner_id, fingerprint, mappings):
    _validate_mappings(mappings, project)
    data = dict(submission=json.loads(_encode_response(review, project, owner_id, fingerprint)),
                mappings=asdict(mappings) if mappings is not None else None)
    raw = json.dumps(data, ensure_ascii=True)
    if len(raw.encode('utf-8')) > 16384:
        raise ValueError('Oversized private browser metadata.')
    return raw


def _decode(raw):
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > 16384:
        raise ValueError('Bounded browser metadata is required.')
    data = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(data, dict) or set(data) != {'submission', 'mappings'}:
        raise ValueError('Exact reviewed browser fields are required.')
    review, project, owner_id, fingerprint = _decode_response(json.dumps(data['submission']))
    mappings = decode_form_mappings(data['mappings'])
    _validate_mappings(mappings, project)
    return review, project, owner_id, fingerprint, mappings


def _read_result(path):
    if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError('Invalid private browser result path.')
    with path.open('rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError('Oversized browser outcome.')
    data = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(data, dict) or set(data) != {'status', 'message', 'attempted_submissions'}:
        raise ValueError('Invalid browser result fields.')
    result = InteractiveProbeResult(TestStatus(data['status']), data['message'], data['attempted_submissions'])
    if (result.status not in MESSAGES or result.message not in MESSAGES[result.status]
            or (result.status == TestStatus.PASSED and result.attempted_submissions != 1)
            or (result.status == TestStatus.BLOCKED and result.attempted_submissions != 0)):
        raise ValueError('Unexpected browser outcome.')
    return result


def run_isolated_public_browser(review, project, *, owner_id, current_fingerprint,
                                mappings=None, timeout_seconds=45, should_cancel=None):
    raw = _encode(review, project, owner_id, current_fingerprint, mappings)
    result = _run_private_child(raw, module='adaptive_qa.public_browser_process', reader=_read_result,
                                timeout_seconds=timeout_seconds, should_cancel=should_cancel,
                                reference_variables=tuple(ref.environment_variable for ref in review.proposal.form.inputs))
    if not isinstance(result, SubmissionProcessResult):
        return result
    if result.outcome == 'cancelled':
        return InteractiveProbeResult(TestStatus.CANCELLED, 'The reviewed browser check was cancelled.', result.attempted_submissions)
    message = ('The reviewed browser exceeded its process deadline.' if result.reason_code == 'deadline_exceeded'
               else 'The reviewed browser could not return a reliable outcome.')
    return InteractiveProbeResult(TestStatus.ERROR, message, result.attempted_submissions)


def _execute(review, project, owner_id, fingerprint, mappings=None, *, profile_directory):
    from playwright.sync_api import sync_playwright
    _validate(review, project, owner_id, fingerprint)
    _validate_mappings(mappings, project)
    transport = PublicSubmissionTransport(review, project, current_fingerprint=fingerprint)
    guard = DestinationGuard(project, local_sample=False, max_requests=100)
    state = dict(denied=0, document=False, reads=0, protected=False, armed=False,
                 expected=None, response=None, transport_started=False)
    def clean():return state['denied'] == 0 and guard.denied == 0
    def count():
        if state['response'] is not None:
            return state['response'].attempted_submissions
        return None if state['transport_started'] else 0
    try:
        with EgressProxy(guard) as proxy, sync_playwright() as playwright:
            if profile_directory.exists() or profile_directory.is_symlink():
                raise ValueError('A fresh private browser profile is required.')
            profile_directory.mkdir(mode=0o700)
            context = playwright.chromium.launch_persistent_context(str(profile_directory), timeout=10000,
                service_workers='block', accept_downloads=False, ignore_https_errors=False,
                **chromium_proxy_options(proxy.url))
            browser = context.browser
            try:
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    for extra in context.pages:
                        if extra != page:extra.close()
                    def popup(extra):
                        state['denied'] += 1
                        try:extra.close()
                        except Exception:pass
                    context.on('page', popup)
                    page.set_default_timeout(3000)
                    page.on('pageerror', lambda _:state.update(denied=state['denied']+1))
                    def deny(route):
                        state['denied'] += 1
                        try:route.abort()
                        except Exception:pass
                    def route_request(route):
                        request = route.request
                        try:
                            if (not state['protected'] and request.method in ('GET', 'HEAD')
                                    and request.post_data_buffer is None):
                                if request.resource_type == 'document':
                                    if (state['document'] or request.method != 'GET' or request.url != project.base_url
                                            or request.frame != page.main_frame):
                                        deny(route);return
                                    state['document'] = True
                                state['reads'] += 1
                                if state['reads'] > 100:
                                    deny(route);return
                                validate_discovery_url(request.url, project, 'public_https')
                                route.continue_()
                            elif (state['armed'] and clean() and not state['transport_started'] and request.method == 'POST'
                                    and request.url == review.proposal.endpoint_url
                                    and request.post_data_buffer == state['expected']):
                                state['transport_started'] = True
                                response = transport.submit(url=request.url, method=request.method,
                                    content_type=request.headers.get('content-type', ''), body=request.post_data_buffer)
                                state['response'] = response
                                if response.outcome not in ('accepted', 'rejected'):
                                    deny(route);return
                                assertion = review.proposal.accepted if response.outcome == 'accepted' else review.proposal.rejected
                                route.fulfill(status=assertion.status_code, content_type='application/json',
                                    body=json.dumps({assertion.field_name:assertion.expected_value}))
                            else:deny(route)
                        except Exception:deny(route)
                    def websocket(connection):
                        state['denied'] += 1
                        connection.close()
                    context.route('**/*', route_request)
                    context.route_web_socket('**/*', websocket)
                    loaded = page.goto(project.base_url, wait_until='domcontentloaded', timeout=10000)
                    if (loaded is None or loaded.status != 200 or page.url != project.base_url
                            or 'text/html' not in loaded.headers.get('content-type', '').lower()
                            or guard.requests < 1 or not clean()):
                        raise ValueError()
                    def before_inputs():
                        state['protected'] = True
                        return clean() and transport.prepare_destination()
                    def arm(values):
                        state['expected'] = urlencode(tuple(zip(review.proposal.field_names, values, strict=True))).encode('ascii')
                        state['armed'] = True
                    return probe_reviewed_public_form(page, review, project, owner_id=owner_id,
                        current_fingerprint=fingerprint, network_clean=clean, before_inputs=before_inputs,
                        before_submit=arm, submission_state=lambda:state['response'], mappings=mappings)
                finally:context.close()
            finally:
                if browser is not None and browser.is_connected():browser.close()
    except Exception:
        return InteractiveProbeResult(TestStatus.ERROR, INITIAL_ERROR, count())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True);parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source, output = Path(args.input), Path(args.output)
    if (source.resolve() != source or output.resolve() != output or source.parent != output.parent
            or source.name != 'input.json' or output.name != 'result.json'
            or not source.is_file() or source.stat().st_nlink != 1 or output.exists()):
        raise ValueError('Private canonical sibling paths are required.')
    with source.open('rb') as stream:
        raw = stream.read(16385)
    result = _execute(*_decode(raw.decode('utf-8')), profile_directory=source.parent/'browser-profile')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(asdict(result), stream)


if __name__ == '__main__':main()
