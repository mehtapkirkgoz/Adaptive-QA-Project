"""Bounded local API transport using authorized numeric destinations."""

from dataclasses import dataclass, field
import http.client
from time import monotonic, perf_counter
from urllib.parse import urlencode

from adaptive_qa.api_models import ApiCase, ApiConfiguration, ApiRequest, HttpMethod, JsonOperator, JsonType, parse_api_json
from adaptive_qa.egress import DestinationGuard
from adaptive_qa.models import TestResult, TestStatus


class ApiPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ApiExchange:
    status: int
    json_content_type: bool
    valid_json: bool
    payload: object = field(default=None, repr=False)


def perform_request(configuration: ApiConfiguration, request: ApiRequest) -> ApiExchange:
    """Read one response; never follow redirects or honor environment proxies.

    Socket/size limits are bounded; the isolated adapter must enforce the hard
    total deadline against slow header/body streams. No raw response is reported.
    """
    if not isinstance(configuration, ApiConfiguration) or not isinstance(request, ApiRequest):
        raise ValueError('API configuration and request contracts are required.')
    project = configuration.project
    if project.base_url.rstrip('/') != 'http://127.0.0.1:8000':
        raise ApiPolicyError('Only the registered local API origin is executable.')
    if request.method not in (HttpMethod.GET, HttpMethod.HEAD) and not project.allow_data_changes:
        raise ApiPolicyError('Project policy disables data-changing API operations.')
    headers = {'Accept': 'application/json', 'Connection': 'close'}
    if request.use_authentication:
        if configuration.bearer_token is None:
            raise ApiPolicyError('API authentication configuration is missing.')
        try:
            token = configuration.bearer_token.resolve().value
        except ValueError as error:
            raise ApiPolicyError('Required API authentication is unavailable.') from error
        if (not token.isascii() or len(token) > 4096
                or any(ord(character) <= 32 or ord(character) == 127 for character in token)):
            raise ApiPolicyError('API authentication value is not a supported header token.')
        headers['Authorization'] = 'Bearer ' + token
    path = request.path
    if request.query:
        path += '?' + urlencode(request.query)
    if len(path) > 8192:
        raise ApiPolicyError('Encoded API request target exceeds the limit.')
    url = project.base_url.rstrip('/') + path
    guard = DestinationGuard(project, local_sample=True, max_requests=1)
    target = guard.authorize(url)
    deadline = monotonic() + configuration.timeout_seconds
    connection = http.client.HTTPConnection(target.hostname, target.port, timeout=configuration.timeout_seconds)
    try:
        connection.sock = guard.connect(target, timeout_seconds=min(5, configuration.timeout_seconds))
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError('API operation deadline exceeded.')
        connection.sock.settimeout(remaining)
        body = None if request.body_json is None else request.body_json.encode('utf-8')
        if body is not None:
            headers['Content-Type'] = 'application/json'
        connection.request(request.method.value, path, body=body, headers=headers)
        response = connection.getresponse()
        encoding = response.getheader('Content-Encoding', 'identity').strip().casefold()
        if encoding != 'identity':
            raise http.client.HTTPException('Encoded API responses are not supported.')
        raw = response.read(configuration.max_response_bytes + 1)
        if len(raw) > configuration.max_response_bytes:
            raise http.client.HTTPException('API response size limit exceeded.')
        if monotonic() > deadline:
            raise TimeoutError('API operation deadline exceeded.')
        media = response.getheader('Content-Type', '').split(';', 1)[0].strip().casefold()
        json_type = media == 'application/json' or (media.startswith('application/') and media.endswith('+json'))
        try:
            payload = parse_api_json(raw.decode('utf-8'))
            valid_json = True
        except (ValueError, UnicodeError, RecursionError):
            payload, valid_json = None, False
        return ApiExchange(response.status, json_type, valid_json, payload)
    finally:
        connection.close()


def failed_json_checks(payload, checks) -> tuple[int, ...]:
    """Return assertion indexes only; payloads and expected operands stay private."""
    failures = []
    for index, check in enumerate(checks):
        value = payload
        exists = True
        for component in check.path:
            if type(component) is int and isinstance(value, list) and component < len(value):
                value = value[component]
            elif isinstance(component, str) and isinstance(value, dict) and component in value:
                value = value[component]
            else:
                exists = False
                break
        passed = exists
        if exists:
            operand = check.expected
            if check.operator == JsonOperator.TYPE:
                passed = {JsonType.OBJECT: type(value) is dict, JsonType.ARRAY: type(value) is list,
                    JsonType.STRING: type(value) is str, JsonType.INTEGER: type(value) is int,
                    JsonType.NUMBER: type(value) in (int, float), JsonType.BOOLEAN: type(value) is bool,
                    JsonType.NULL: value is None}[operand]
            elif check.operator == JsonOperator.EQUALS:
                numeric = type(value) in (int, float) and type(operand) in (int, float)
                passed = (numeric or type(value) is type(operand)) and value == operand
            elif check.operator in (JsonOperator.MINIMUM, JsonOperator.MAXIMUM):
                passed = type(value) in (int, float)
                if passed:
                    passed = value >= operand if check.operator == JsonOperator.MINIMUM else value <= operand
            elif check.operator == JsonOperator.LENGTH:
                passed = type(value) in (list, dict, str) and len(value) == operand
        if not passed:
            failures.append(index)
    return tuple(failures)


def run_api_case(case: ApiCase, configuration: ApiConfiguration | None) -> TestResult:
    """Map configuration, policy, assertions, and transport errors to safe results."""
    if not isinstance(case, ApiCase):
        raise ValueError('case must be an ApiCase.')
    started = perf_counter()
    case_id = case.definition.case_id
    if configuration is None:
        return TestResult(case_id, TestStatus.BLOCKED, 0, 'API configuration is missing.')
    if case.definition.changes_data and not configuration.project.allow_data_changes:
        return TestResult(case_id, TestStatus.BLOCKED, 0, 'Project policy disables data-changing API tests.')
    try:
        exchange = perform_request(configuration, case.request)
        if exchange.status != case.expected_status:
            status, message = TestStatus.FAILED, 'HTTP status did not match the explicit contract.'
        elif case.expect_json and (not exchange.json_content_type or not exchange.valid_json):
            status, message = TestStatus.FAILED, 'The JSON response contract was not satisfied.'
        elif case.expect_json and (failures := failed_json_checks(exchange.payload, case.checks)):
            status, message = TestStatus.FAILED, 'JSON assertion indexes failed: ' + ', '.join(map(str, failures)) + '.'
        else:
            status, message = TestStatus.PASSED, 'The configured API response satisfied all explicit checks.'
    except ApiPolicyError:
        status, message = TestStatus.BLOCKED, 'API configuration, authentication, or operation policy blocked execution.'
    except (OSError, ValueError, http.client.HTTPException):
        status, message = TestStatus.ERROR, 'API transport or bounded response processing failed.'
    return TestResult(case_id, status, perf_counter() - started, message)
