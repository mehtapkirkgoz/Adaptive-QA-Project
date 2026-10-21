"""Bindings cannot turn failed UI/API layers into passing results."""

from dataclasses import replace
import unittest
from unittest.mock import Mock

from adaptive_qa.api_catalog import API_BY_ID
from adaptive_qa.api_models import ApiConfiguration
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.ui_api_bridge import UiApiBinding, validate_ui_api


class UiApiBridgeTests(unittest.TestCase):
    def setUp(self):
        self.binding = UiApiBinding('demo', 'SEARCH-002', ('API-006',))
        self.ui = TestResult('SEARCH-002', TestStatus.PASSED, 0.1, 'UI passed.')
        self.case = API_BY_ID['API-006']
        self.configuration = ApiConfiguration(ProjectConfig('demo', 'Demo', 'http://127.0.0.1:8000', ('127.0.0.1',)))

    def test_invalid_binding_ids_are_rejected(self):
        for ids in ([], (), ('API-006', 'API-006')):
            with self.assertRaises(ValueError):
                UiApiBinding('demo', 'SEARCH-002', ids)

    def test_failed_ui_does_not_dispatch_api(self):
        runner = Mock()
        result = validate_ui_api(self.binding, replace(self.ui, status=TestStatus.FAILED),
                                  (self.case,), self.configuration, api_runner=runner)
        self.assertEqual(result.result.status, TestStatus.BLOCKED)
        runner.assert_not_called()

    def test_missing_or_wrong_project_configuration_is_blocked(self):
        runner = Mock()
        wrong = replace(self.configuration, project=replace(self.configuration.project, project_id='other'))
        for configuration in (None, wrong):
            with self.subTest(configuration=configuration):
                result = validate_ui_api(self.binding, self.ui, (self.case,), configuration, api_runner=runner)
                self.assertEqual(result.result.status, TestStatus.BLOCKED)
        runner.assert_not_called()

    def test_case_id_mismatch_cannot_silently_change_binding(self):
        with self.assertRaises(ValueError):
            validate_ui_api(self.binding, self.ui, (API_BY_ID['API-005'],), self.configuration)

    def test_api_failure_is_not_overridden_by_passing_ui(self):
        runner = Mock(return_value=TestResult('API-006', TestStatus.FAILED, 0.1, 'API assertion failed.'))
        result = validate_ui_api(self.binding, self.ui, (self.case,), self.configuration, api_runner=runner)
        self.assertEqual(result.result.status, TestStatus.FAILED)
        self.assertEqual(result.ui_result.status, TestStatus.PASSED)

    def test_both_layers_must_pass(self):
        runner = Mock(return_value=TestResult('API-006', TestStatus.PASSED, 0.1, 'API passed.'))
        result = validate_ui_api(self.binding, self.ui, (self.case,), self.configuration, api_runner=runner)
        self.assertEqual(result.result.status, TestStatus.PASSED)
        self.assertEqual(len(result.api_results), 1)

    def test_wrong_adapter_result_identity_is_an_error(self):
        runner = Mock(return_value=TestResult('OTHER-CASE', TestStatus.PASSED, 0.1, 'Wrong result.'))
        result = validate_ui_api(self.binding, self.ui, (self.case,), self.configuration, api_runner=runner)
        self.assertEqual(result.result.status, TestStatus.ERROR)
