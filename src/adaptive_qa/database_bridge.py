"""Explicit database checks gated by trusted, independent UI and API outcomes."""

from dataclasses import dataclass

from adaptive_qa.database_models import DatabaseCase, DatabaseConfiguration
from adaptive_qa.database_process import run_isolated_database_case
from adaptive_qa.models import TestResult, TestStatus


@dataclass(frozen=True)
class DatabaseBinding:
    project_id: str
    ui_case_id: str
    api_case_id: str
    database_case_id: str

    def __post_init__(self):
        for value in (self.project_id, self.ui_case_id, self.api_case_id, self.database_case_id):
            if not isinstance(value, str) or not value.strip() or len(value) > 80:
                raise ValueError('Binding identities must be bounded non-empty text.')


def validate_ui_api_database(binding, ui_result, api_result, case, configuration,
                             *, fixture_root, database_runner=None):
    """Return the database outcome; never rewrite upstream results or assertions."""
    if (not isinstance(binding, DatabaseBinding) or not isinstance(ui_result, TestResult)
            or not isinstance(api_result, TestResult) or not isinstance(case, DatabaseCase)):
        raise ValueError('Typed binding, layer results, and database case are required.')
    if (ui_result.case_id != binding.ui_case_id or api_result.case_id != binding.api_case_id
            or case.definition.case_id != binding.database_case_id):
        raise ValueError('Layer identities do not match the explicit binding.')
    if configuration is not None and not isinstance(configuration, DatabaseConfiguration):
        raise ValueError('configuration must be a DatabaseConfiguration or None.')
    if (configuration is None or configuration.project.project_id != binding.project_id
            or case.template.project_id != binding.project_id):
        return TestResult(binding.database_case_id, TestStatus.BLOCKED, 0,
                          'Matching explicit database configuration is required.')
    if ui_result.status != TestStatus.PASSED or api_result.status != TestStatus.PASSED:
        return TestResult(binding.database_case_id, TestStatus.BLOCKED, 0,
                          'UI/API prerequisites did not pass; database validation was not executed.')
    try:
        result = (database_runner or run_isolated_database_case)(case, configuration, fixture_root=fixture_root)
        if not isinstance(result, TestResult) or result.case_id != binding.database_case_id:
            raise ValueError('Invalid database result identity.')
        return result
    except Exception:
        return TestResult(binding.database_case_id, TestStatus.ERROR, 0,
                          'Database adapter failed or returned an invalid result identity.')
