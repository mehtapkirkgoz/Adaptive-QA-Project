"""Private database child transport with a hard deadline and process cleanup."""

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

from adaptive_qa.database_models import DatabaseCase, DatabaseConfiguration, DatabaseCheck, DatabaseOperator, QueryTemplate
from adaptive_qa.database_adapter import run_database_case
from adaptive_qa.browser_process import _terminate_process_tree
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestCase, TestResult, TestStatus, TestType
from adaptive_qa.secrets import SecretReference


def encode_database_input(case, configuration, fixture_root):
    """Private temporary input; no resolved database path is serialized."""
    return json.dumps({'case': asdict(case), 'configuration': asdict(configuration),
                       'fixture_root': str(fixture_root)})


def decode_database_input(text):
    raw = json.loads(text)
    case = raw['case']
    definition = case['definition']
    definition['test_type'] = TestType(definition['test_type'])
    definition['required_features'] = tuple(definition['required_features'])
    definition['steps'] = tuple(definition['steps'])
    template = case['template']
    template['parameter_names'] = tuple(template['parameter_names'])
    checks = []
    for check in case['checks']:
        check['operator'] = DatabaseOperator(check['operator'])
        checks.append(DatabaseCheck(**check))
    parsed_case = DatabaseCase(TestCase(**definition), QueryTemplate(**template),
                              tuple(tuple(pair) for pair in case['parameters']), tuple(checks))
    config = raw['configuration']
    project = config['project']
    project['allowed_hosts'] = tuple(project['allowed_hosts'])
    config['project'] = ProjectConfig(**project)
    config['database_path'] = SecretReference(**config['database_path'])
    return parsed_case, DatabaseConfiguration(**config), Path(raw['fixture_root'])


def run_isolated_database_case(case: DatabaseCase, configuration: DatabaseConfiguration | None,
                          timeout_seconds: float = 15, *, fixture_root, should_cancel=None) -> TestResult:
    if not isinstance(case, DatabaseCase):
        raise ValueError('case must be a DatabaseCase.')
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60):
        raise ValueError('Database total timeout must be finite and between 0 and 60 seconds.')
    if configuration is not None and not isinstance(configuration, DatabaseConfiguration):
        raise ValueError('configuration must be a DatabaseConfiguration or None.')
    if configuration is None or case.template.project_id != configuration.project.project_id:
        return run_database_case(case, configuration, fixture_root=fixture_root)
    started = perf_counter()
    def outcome(status, reason):
        return TestResult(case.definition.case_id, status, perf_counter() - started, reason)
    if should_cancel is not None and should_cancel():
        return outcome(TestStatus.CANCELLED, 'Database execution was cancelled.')
    with TemporaryDirectory(prefix='adaptive-qa-database-') as temporary:
        source, destination = Path(temporary) / 'input.json', Path(temporary) / 'result.json'
        encoded = encode_database_input(case, configuration, fixture_root)
        if len(encoded.encode('utf-8')) > 524288:
            return outcome(TestStatus.BLOCKED, 'Database configuration transport exceeds its size limit.')
        source.write_text(encoded, encoding='utf-8')
        options = {'start_new_session': True} if os.name != 'nt' else {
            'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        process = subprocess.Popen([sys.executable, '-m', 'adaptive_qa.database_process',
            '--child-input', str(source), '--child-output', str(destination)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
        try:
            while True:
                if should_cancel is not None and should_cancel():
                    _terminate_process_tree(process)
                    return outcome(TestStatus.CANCELLED, 'Database execution was cancelled.')
                remaining = timeout_seconds - (perf_counter() - started)
                if remaining <= 0:
                    _terminate_process_tree(process)
                    return outcome(TestStatus.ERROR, 'Database execution exceeded its total time limit.')
                try:
                    process.wait(timeout=min(0.1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            try:
                if process.returncode != 0 or destination.stat().st_size > 16384:
                    raise ValueError('Invalid Database child output.')
                data = json.loads(destination.read_text(encoding='utf-8'))
                data['status'] = TestStatus(data['status'])
                data['evidence_paths'] = tuple(data.get('evidence_paths', ()))
                result = TestResult(**data)
                if result.case_id != case.definition.case_id or result.evidence_paths:
                    raise ValueError('Unexpected Database child result identity or evidence.')
                return replace(result, duration_seconds=perf_counter() - started)
            except (OSError, ValueError, TypeError, KeyError):
                return outcome(TestStatus.ERROR, 'The Database process returned no valid safe result.')
        finally:
            if process.poll() is None:
                _terminate_process_tree(process)


def main():
    parser = argparse.ArgumentParser(description='Private controlled Database child adapter.')
    parser.add_argument('--child-input', type=Path, required=True)
    parser.add_argument('--child-output', type=Path, required=True)
    args = parser.parse_args()
    if args.child_input.stat().st_size > 524288:
        raise ValueError('Database input exceeds the size limit.')
    case, config, fixture_root = decode_database_input(args.child_input.read_text(encoding='utf-8'))
    result = run_database_case(case, config, fixture_root=fixture_root)
    args.child_output.write_text(json.dumps(asdict(result)), encoding='utf-8')


if __name__ == '__main__':
    main()
