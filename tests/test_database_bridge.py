"""Explicit identity and prerequisite boundaries for database follow-up checks."""

from dataclasses import replace
import unittest
from unittest.mock import Mock

from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_bridge import DatabaseBinding, validate_ui_api_database
from adaptive_qa.database_catalog import DATABASE_CASES
from adaptive_qa.database_models import DatabaseConfiguration
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.secrets import SecretReference


class DatabaseBridgeTests(unittest.TestCase):
    def setUp(self):
        self.case = DATABASE_CASES[0]
        self.config = DatabaseConfiguration(ProjectConfig('local-database', 'Fixture',
            'http://127.0.0.1:8000', ('127.0.0.1',)), SecretReference('QA_DB_PATH'))
        self.ui = TestResult('UI-CREATE', TestStatus.PASSED, 0, 'UI passed.')
        self.api = TestResult('API-CREATE', TestStatus.PASSED, 0, 'API passed.')
        self.binding = DatabaseBinding('local-database', self.ui.case_id, self.api.case_id,
                                       self.case.definition.case_id)
        self.runner = Mock(return_value=TestResult(self.case.definition.case_id, TestStatus.PASSED, 0, 'Matched.'))

    def run_binding(self, ui=None, api=None, case=None, config=None):
        return validate_ui_api_database(self.binding, ui or self.ui, api or self.api,
            case or self.case, config or self.config, fixture_root='fixture', database_runner=self.runner)

    def test_each_nonpassing_upstream_status_prevents_database_execution(self):
        for status in TestStatus:
            if status == TestStatus.PASSED:
                continue
            for field in ('ui', 'api'):
                with self.subTest(status=status, field=field):
                    result = self.run_binding(**{field: replace(getattr(self, field), status=status)})
                    self.assertEqual(result.status, TestStatus.BLOCKED)
        self.runner.assert_not_called()

    def test_missing_or_foreign_configuration_never_executes(self):
        result = validate_ui_api_database(self.binding, self.ui, self.api, self.case, None,
            fixture_root='fixture', database_runner=self.runner)
        self.assertEqual(result.status, TestStatus.BLOCKED)
        foreign = replace(self.config, project=replace(self.config.project, project_id='other'))
        self.assertEqual(self.run_binding(config=foreign).status, TestStatus.BLOCKED)
        self.runner.assert_not_called()

    def test_wrong_identity_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            self.run_binding(api=replace(self.api, case_id='wrong'))
        self.runner.assert_not_called()

    def test_database_failure_does_not_change_passing_upstream_results(self):
        self.runner.return_value = replace(self.runner.return_value, status=TestStatus.FAILED)
        self.assertEqual(self.run_binding().status, TestStatus.FAILED)
        self.assertEqual((self.ui.status, self.api.status), (TestStatus.PASSED, TestStatus.PASSED))

    def test_runner_error_and_wrong_result_identity_are_safe_errors(self):
        self.runner.return_value = replace(self.runner.return_value, case_id='wrong')
        self.assertEqual(self.run_binding().status, TestStatus.ERROR)
        self.runner.side_effect = RuntimeError('private connection details')
        result = self.run_binding()
        self.assertEqual(result.status, TestStatus.ERROR)
        self.assertNotIn('private', result.message)
