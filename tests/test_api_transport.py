"""API policy and assertion tests without network or secret disclosure."""

from dataclasses import replace
import os
import unittest
from unittest.mock import patch

from adaptive_qa.api_models import ApiCase, ApiConfiguration, ApiRequest, HttpMethod, JsonCheck, JsonOperator, JsonType
from adaptive_qa.api_transport import ApiExchange, ApiPolicyError, failed_json_checks, perform_request, run_api_case
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestCase, TestStatus, TestType
from adaptive_qa.secrets import SecretReference


class ApiTransportTests(unittest.TestCase):
    def setUp(self):
        self.configuration = ApiConfiguration(ProjectConfig('api', 'API', 'http://127.0.0.1:8000', ('127.0.0.1',)))
        definition = TestCase('API-UNIT', 'API assertion', TestType.API, ('api',), ('Inspect response',), 'Explicit contract holds.')
        self.case = ApiCase(definition, ApiRequest('/api/health'), checks=(JsonCheck(('ok',), JsonOperator.EQUALS, True),))

    def test_missing_configuration_is_blocked_without_transport(self):
        with patch('adaptive_qa.api_transport.perform_request') as request:
            self.assertEqual(run_api_case(self.case, None).status, TestStatus.BLOCKED)
            request.assert_not_called()

    def test_nonlocal_origin_is_blocked_before_connect(self):
        config = replace(self.configuration, project=ProjectConfig('api', 'API', 'https://example.com', ('example.com',)))
        with patch('adaptive_qa.api_transport.DestinationGuard') as guard:
            with self.assertRaises(ApiPolicyError):
                perform_request(config, self.case.request)
            guard.assert_not_called()

    def test_mutation_is_blocked_before_transport(self):
        case = replace(self.case, definition=replace(self.case.definition, changes_data=True),
                       request=ApiRequest('/api/echo', HttpMethod.POST, body_json='{}'))
        with patch('adaptive_qa.api_transport.perform_request') as request:
            self.assertEqual(run_api_case(case, self.configuration).status, TestStatus.BLOCKED)
            request.assert_not_called()

    def test_missing_or_injected_authentication_is_blocked_before_connect(self):
        request = replace(self.case.request, use_authentication=True)
        config = replace(self.configuration, bearer_token=SecretReference('QA_UNIT_API_TOKEN'))
        for token in (None, 'secret\r\nInjected: value', 'non ascii ş'):
            env = {} if token is None else {'QA_UNIT_API_TOKEN': token}
            with self.subTest(token=token), patch.dict(os.environ, env, clear=True), \
                 patch('adaptive_qa.api_transport.DestinationGuard') as guard:
                with self.assertRaises(ApiPolicyError):
                    perform_request(config, request)
                guard.assert_not_called()

    def test_boolean_is_not_integer_number_or_numeric_equal(self):
        checks = (JsonCheck((), JsonOperator.TYPE, JsonType.INTEGER),
                  JsonCheck((), JsonOperator.TYPE, JsonType.NUMBER), JsonCheck((), JsonOperator.EQUALS, 1))
        self.assertEqual(failed_json_checks(True, checks), (0, 1, 2))

    def test_null_is_present_but_missing_path_is_not(self):
        checks = (JsonCheck(('value',), JsonOperator.EXISTS), JsonCheck(('value',), JsonOperator.TYPE, JsonType.NULL),
                  JsonCheck(('missing',), JsonOperator.EXISTS))
        self.assertEqual(failed_json_checks({'value': None}, checks), (2,))

    def test_nested_paths_ranges_and_lengths_are_checked(self):
        checks = (JsonCheck(('items', 0, 'price'), JsonOperator.MINIMUM, 5),
                  JsonCheck(('items', 0, 'price'), JsonOperator.MAXIMUM, 20),
                  JsonCheck(('items',), JsonOperator.LENGTH, 1),
                  JsonCheck(('items', 1), JsonOperator.EXISTS))
        self.assertEqual(failed_json_checks({'items': [{'price': 10}]}, checks), (3,))

    def test_expected_status_and_json_contract_failures_are_assertion_failures(self):
        for exchange in (ApiExchange(503, True, True, {'ok': True}),
                         ApiExchange(200, False, True, {'ok': True}),
                         ApiExchange(200, True, False), ApiExchange(200, True, True, {'ok': False})):
            with self.subTest(exchange=exchange), patch('adaptive_qa.api_transport.perform_request', return_value=exchange):
                self.assertEqual(run_api_case(self.case, self.configuration).status, TestStatus.FAILED)

    def test_response_and_exception_secrets_never_appear_in_results(self):
        for outcome in (ApiExchange(200, True, True, {'ok': False, 'secret': 'private-response'}), OSError('private-error')):
            with patch('adaptive_qa.api_transport.perform_request', **(
                {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome})):
                result = run_api_case(self.case, self.configuration)
                self.assertNotIn('private-', repr(result))

    def test_success_and_head_cases_preserve_definition_id(self):
        with patch('adaptive_qa.api_transport.perform_request', return_value=ApiExchange(200, True, True, {'ok': True})):
            result = run_api_case(self.case, self.configuration)
            self.assertEqual(result.status, TestStatus.PASSED)
            self.assertEqual(result.case_id, self.case.definition.case_id)
        case = replace(self.case, request=ApiRequest('/api/health', HttpMethod.HEAD), checks=(), expect_json=False)
        with patch('adaptive_qa.api_transport.perform_request', return_value=ApiExchange(200, False, False)):
            self.assertEqual(run_api_case(case, self.configuration).status, TestStatus.PASSED)
