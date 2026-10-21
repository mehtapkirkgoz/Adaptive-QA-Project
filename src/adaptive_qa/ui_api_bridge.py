"""Explicit UI-to-API validation; each layer retains its own expected outcome."""

from dataclasses import dataclass
from time import perf_counter

from adaptive_qa.api_models import ApiCase, ApiConfiguration
from adaptive_qa.api_process import run_isolated_api_case
from adaptive_qa.models import TestResult, TestStatus


@dataclass(frozen=True)
class UiApiBinding:
    project_id: str
    ui_case_id: str
    api_case_ids: tuple[str, ...]

    def __post_init__(self):
        for text in (self.project_id, self.ui_case_id):
            if not isinstance(text, str) or not text.strip() or len(text) > 80:
                raise ValueError('Binding identifiers must be bounded non-empty strings.')
        if (not isinstance(self.api_case_ids, tuple) or not 1 <= len(self.api_case_ids) <= 10
                or any(not isinstance(value, str) or not value.strip() or len(value) > 80 for value in self.api_case_ids)
                or len(set(self.api_case_ids)) != len(self.api_case_ids)):
            raise ValueError('api_case_ids must be a tuple of one to ten unique identifiers.')


@dataclass(frozen=True)
class UiApiValidation:
    result: TestResult
    ui_result: TestResult
    api_results: tuple[TestResult, ...]


def validate_ui_api(binding: UiApiBinding, ui_result: TestResult, api_cases: tuple[ApiCase, ...],
                    configuration: ApiConfiguration | None, *, api_runner=None) -> UiApiValidation:
    """Run only explicitly bound API assertions after a successful trusted UI result."""
    if not isinstance(binding, UiApiBinding) or not isinstance(ui_result, TestResult):
        raise ValueError('Typed binding and UI result are required.')
    if configuration is not None and not isinstance(configuration, ApiConfiguration):
        raise ValueError('configuration must be an ApiConfiguration or None.')
    if (not isinstance(api_cases, tuple) or any(not isinstance(case, ApiCase) for case in api_cases)
            or tuple(case.definition.case_id for case in api_cases) != binding.api_case_ids
            or ui_result.case_id != binding.ui_case_id):
        raise ValueError('Case identities do not match the explicit UI/API binding.')
    started = perf_counter()
    results = ()
    if ui_result.status != TestStatus.PASSED:
        status, message = TestStatus.BLOCKED, 'UI prerequisites did not pass; no API validation was executed.'
    elif configuration is None:
        status, message = TestStatus.BLOCKED, 'Explicit API configuration is missing.'
    elif configuration.project.project_id != binding.project_id:
        status, message = TestStatus.BLOCKED, 'API configuration belongs to a different project.'
    else:
        runner = api_runner or run_isolated_api_case
        collected = []
        for case in api_cases:
            try:
                result = runner(case, configuration)
                if not isinstance(result, TestResult) or result.case_id != case.definition.case_id:
                    raise ValueError('API runner returned the wrong result identity.')
            except Exception:
                result = TestResult(case.definition.case_id, TestStatus.ERROR, 0,
                                    'API adapter failed or returned an invalid result identity.')
            collected.append(result)
        results = tuple(collected)
        statuses = {result.status for result in results}
        if TestStatus.ERROR in statuses:
            status = TestStatus.ERROR
        elif TestStatus.FAILED in statuses:
            status = TestStatus.FAILED
        elif statuses != {TestStatus.PASSED}:
            status = TestStatus.BLOCKED
        else:
            status = TestStatus.PASSED
        message = 'Independent UI/API assertions completed; neither layer rewrites the other result.'
    result = TestResult('UIAPI-' + binding.ui_case_id, status,
                        ui_result.duration_seconds + perf_counter() - started, message)
    return UiApiValidation(result, ui_result, results)
