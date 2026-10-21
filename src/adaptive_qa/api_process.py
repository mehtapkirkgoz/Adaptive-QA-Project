"""Private API child transport with a hard total deadline and process cleanup."""

import argparse
from dataclasses import asdict, replace
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from adaptive_qa.api_models import ApiCase, ApiConfiguration, ApiRequest, HttpMethod, JsonCheck, JsonOperator, JsonType
from adaptive_qa.api_transport import run_api_case
from adaptive_qa.browser_process import _terminate_process_tree
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestCase, TestResult, TestStatus, TestType
from adaptive_qa.secrets import SecretReference


def encode_api_input(case, configuration):
    """Private temporary input, never a report; bearer values are not resolved here."""
    return json.dumps({'case': asdict(case), 'configuration': asdict(configuration)})


def decode_api_input(text):
    raw = json.loads(text)
    case = raw['case']
    definition = case['definition']
    definition['test_type'] = TestType(definition['test_type'])
    definition['required_features'] = tuple(definition['required_features'])
    definition['steps'] = tuple(definition['steps'])
    request = case['request']
    request['method'] = HttpMethod(request['method'])
    request['query'] = tuple(tuple(pair) for pair in request['query'])
    checks = []
    for check in case['checks']:
        check['path'] = tuple(check['path'])
        check['operator'] = JsonOperator(check['operator'])
        if check['operator'] == JsonOperator.TYPE:
            check['expected'] = JsonType(check['expected'])
        checks.append(JsonCheck(**check))
    parsed_case = ApiCase(TestCase(**definition), ApiRequest(**request), case['expected_status'],
                          tuple(checks), case['expect_json'])
    config = raw['configuration']
    project = config['project']
    project['allowed_hosts'] = tuple(project['allowed_hosts'])
    config['project'] = ProjectConfig(**project)
    if config['bearer_token'] is not None:
        config['bearer_token'] = SecretReference(**config['bearer_token'])
    return parsed_case, ApiConfiguration(**config)


def run_isolated_api_case(case: ApiCase, configuration: ApiConfiguration | None,
                          timeout_seconds: float = 15, *, should_cancel=None) -> TestResult:
    if not isinstance(case, ApiCase):
        raise ValueError('case must be an ApiCase.')
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60):
        raise ValueError('API total timeout must be finite and between 0 and 60 seconds.')
    if configuration is not None and not isinstance(configuration, ApiConfiguration):
        raise ValueError('configuration must be an ApiConfiguration or None.')
    if configuration is None or (case.definition.changes_data and not configuration.project.allow_data_changes):
        return run_api_case(case, configuration)
    started = perf_counter()
    def outcome(status, reason):
        return TestResult(case.definition.case_id, status, perf_counter() - started, reason)
    if should_cancel is not None and should_cancel():
        return outcome(TestStatus.CANCELLED, 'API execution was cancelled.')
    with TemporaryDirectory(prefix='adaptive-qa-api-') as temporary:
        source, destination = Path(temporary) / 'input.json', Path(temporary) / 'result.json'
        encoded = encode_api_input(case, configuration)
        if len(encoded.encode('utf-8')) > 524288:
            return outcome(TestStatus.BLOCKED, 'API configuration transport exceeds its size limit.')
        source.write_text(encoded, encoding='utf-8')
        options = {'start_new_session': True} if os.name != 'nt' else {
            'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        process = subprocess.Popen([sys.executable, '-m', 'adaptive_qa.api_process',
            '--child-input', str(source), '--child-output', str(destination)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
        try:
            while True:
                if should_cancel is not None and should_cancel():
                    _terminate_process_tree(process)
                    return outcome(TestStatus.CANCELLED, 'API execution was cancelled.')
                remaining = timeout_seconds - (perf_counter() - started)
                if remaining <= 0:
                    _terminate_process_tree(process)
                    return outcome(TestStatus.ERROR, 'API execution exceeded its total time limit.')
                try:
                    process.wait(timeout=min(0.1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            try:
                if process.returncode != 0 or destination.stat().st_size > 16384:
                    raise ValueError('Invalid API child output.')
                data = json.loads(destination.read_text(encoding='utf-8'))
                data['status'] = TestStatus(data['status'])
                data['evidence_paths'] = tuple(data.get('evidence_paths', ()))
                result = TestResult(**data)
                if result.case_id != case.definition.case_id or result.evidence_paths:
                    raise ValueError('Unexpected API child result identity or evidence.')
                return replace(result, duration_seconds=perf_counter() - started)
            except (OSError, ValueError, TypeError, KeyError):
                return outcome(TestStatus.ERROR, 'The API process returned no valid safe result.')
        finally:
            if process.poll() is None:
                _terminate_process_tree(process)


def main():
    parser = argparse.ArgumentParser(description='Private controlled API child adapter.')
    parser.add_argument('--child-input', type=Path, required=True)
    parser.add_argument('--child-output', type=Path, required=True)
    args = parser.parse_args()
    if args.child_input.stat().st_size > 524288:
        raise ValueError('API input exceeds the size limit.')
    case, config = decode_api_input(args.child_input.read_text(encoding='utf-8'))
    result = run_api_case(case, config)
    args.child_output.write_text(json.dumps(asdict(result)), encoding='utf-8')


if __name__ == '__main__':
    main()
