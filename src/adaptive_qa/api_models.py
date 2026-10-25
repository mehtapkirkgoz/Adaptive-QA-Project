"""Explicit API configuration and bounded JSON assertion contracts."""

from dataclasses import dataclass, field
from enum import StrEnum
import json
import math
import re
from urllib.parse import urlsplit

from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestCase, TestType
from adaptive_qa.secrets import SecretReference


class HttpMethod(StrEnum):
    GET = 'GET'
    HEAD = 'HEAD'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


class JsonOperator(StrEnum):
    EXISTS = 'exists'
    TYPE = 'type'
    EQUALS = 'equals'
    MINIMUM = 'minimum'
    MAXIMUM = 'maximum'
    LENGTH = 'length'


class JsonType(StrEnum):
    OBJECT = 'object'
    ARRAY = 'array'
    STRING = 'string'
    INTEGER = 'integer'
    NUMBER = 'number'
    BOOLEAN = 'boolean'
    NULL = 'null'


def _bounded_text(value, name, maximum=160):
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError(f'{name} must be bounded non-empty text without control characters.')


def _reject_constant(value):
    raise ValueError('Non-finite JSON constants are not allowed.')


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('JSON floating-point values must be finite.')
    return number


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON keys are not allowed.')
        result[key] = value
    return result


def parse_api_json(value):
    return json.loads(value, parse_constant=_reject_constant,
                      parse_float=_finite_float, object_pairs_hook=_unique_object)


@dataclass(frozen=True)
class ApiConfiguration:
    project: ProjectConfig
    bearer_token: SecretReference | None = None
    timeout_seconds: float = 5
    max_response_bytes: int = 65536
    execution_profile: str = 'controlled_local'

    def __post_init__(self):
        if not isinstance(self.project, ProjectConfig):
            raise ValueError('project must be a ProjectConfig.')
        if self.execution_profile not in ('controlled_local', 'public_https'):
            raise ValueError('Unknown API execution profile.')
        if self.execution_profile == 'public_https':
            from adaptive_qa.discovery_target import validate_discovery_project
            validate_discovery_project(self.project, 'public_https')
            if self.bearer_token is not None:
                raise ValueError('Public HTTPS API authentication is not enabled.')
        parsed = urlsplit(self.project.base_url)
        if parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('API base_url must be an origin without path, query, or fragment.')
        if self.bearer_token is not None and not isinstance(self.bearer_token, SecretReference):
            raise ValueError('Authentication must use an environment secret reference.')
        if (isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float))
                or not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 10):
            raise ValueError('timeout_seconds must be finite and between 0 and 10 seconds.')
        if type(self.max_response_bytes) is not int or not 1 <= self.max_response_bytes <= 1048576:
            raise ValueError('max_response_bytes must be an integer between 1 and 1048576.')


@dataclass(frozen=True)
class ApiRequest:
    path: str
    method: HttpMethod = HttpMethod.GET
    query: tuple[tuple[str, str], ...] = field(default=(), repr=False)
    body_json: str | None = field(default=None, repr=False)
    use_authentication: bool = False

    def __post_init__(self):
        _bounded_text(self.path, 'path', 2048)
        if (not self.path.startswith('/') or self.path.startswith('//')
                or not self.path.isascii() or any(character.isspace() for character in self.path)
                or any(character in self.path for character in ('?', '#', '\\', '%'))
                or any(segment in ('.', '..') for segment in self.path.split('/'))):
            raise ValueError('path must be an explicit absolute path without query, escapes, or traversal.')
        if not isinstance(self.method, HttpMethod):
            raise ValueError('method must be an HttpMethod.')
        if not isinstance(self.use_authentication, bool):
            raise ValueError('use_authentication must be a bool.')
        if not isinstance(self.query, tuple) or len(self.query) > 20:
            raise ValueError('query must be a tuple of at most 20 key/value pairs.')
        names = set()
        for pair in self.query:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError('Query entries must be key/value tuples.')
            key, value = pair
            if not isinstance(key, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}', key):
                raise ValueError('Query keys must be bounded ASCII identifiers.')
            _bounded_text(value, 'query value', 512)
            if key in names:
                raise ValueError('Duplicate query keys are not allowed.')
            names.add(key)
        if self.body_json is not None:
            if (not isinstance(self.body_json, str)
                    or len(self.body_json.encode('utf-8')) > 65536):
                raise ValueError('body_json must be bounded JSON text.')
            try:
                parse_api_json(self.body_json)
            except (ValueError, RecursionError) as error:
                raise ValueError('body_json must contain valid finite JSON.') from error
            if self.method in (HttpMethod.GET, HttpMethod.HEAD):
                raise ValueError('GET and HEAD bodies are not supported.')


@dataclass(frozen=True)
class JsonCheck:
    path: tuple[str | int, ...]
    operator: JsonOperator
    expected: object = field(default=None, repr=False)

    def __post_init__(self):
        if not isinstance(self.path, tuple) or len(self.path) > 8:
            raise ValueError('JSON paths must be tuples with at most eight components.')
        for component in self.path:
            if type(component) is int and 0 <= component <= 1000:
                continue
            _bounded_text(component, 'JSON path component', 80)
        if not isinstance(self.operator, JsonOperator):
            raise ValueError('operator must be a JsonOperator.')
        value = self.expected
        if self.operator == JsonOperator.EXISTS:
            valid = value is None
        elif self.operator == JsonOperator.TYPE:
            valid = isinstance(value, JsonType)
        elif self.operator in (JsonOperator.MINIMUM, JsonOperator.MAXIMUM):
            valid = type(value) is int or (type(value) is float and math.isfinite(value))
        elif self.operator == JsonOperator.LENGTH:
            valid = type(value) is int and 0 <= value <= 10000
        else:
            valid = (value is None or type(value) in (bool, int) or
                     (type(value) is float and math.isfinite(value)) or
                     (type(value) is str and len(value) <= 1000))
        if not valid:
            raise ValueError('JSON assertion operand is invalid for its operator.')


@dataclass(frozen=True)
class ApiCase:
    definition: TestCase
    request: ApiRequest
    expected_status: int = 200
    checks: tuple[JsonCheck, ...] = ()
    expect_json: bool = True

    def __post_init__(self):
        if not isinstance(self.definition, TestCase) or self.definition.test_type != TestType.API:
            raise ValueError('definition must be an API TestCase.')
        if not isinstance(self.request, ApiRequest):
            raise ValueError('request must be an ApiRequest.')
        if self.request.method not in (HttpMethod.GET, HttpMethod.HEAD) and not self.definition.changes_data:
            raise ValueError('Non-read methods must declare changes_data=True.')
        if type(self.expected_status) is not int or not 100 <= self.expected_status <= 599:
            raise ValueError('expected_status must be a valid HTTP status integer.')
        if (not isinstance(self.checks, tuple) or len(self.checks) > 50
                or any(not isinstance(check, JsonCheck) for check in self.checks)):
            raise ValueError('checks must be a tuple of at most 50 JsonCheck instances.')
        if not isinstance(self.expect_json, bool):
            raise ValueError('expect_json must be a bool.')
        if (self.request.method == HttpMethod.HEAD or not self.expect_json) and self.checks:
            raise ValueError('Body assertions require a JSON response body.')
        if self.request.method == HttpMethod.HEAD and self.expect_json:
            raise ValueError('HEAD cases cannot expect a JSON body.')
