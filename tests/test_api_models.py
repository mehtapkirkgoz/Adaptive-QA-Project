"""Validate API contracts without performing network operations."""

from dataclasses import replace
import unittest

from adaptive_qa.api_models import ApiCase, ApiConfiguration, ApiRequest, HttpMethod, JsonCheck, JsonOperator, JsonType
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestCase, TestType
from adaptive_qa.secrets import SecretReference


class ApiModelTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectConfig('api', 'API', 'http://127.0.0.1:8000', ('127.0.0.1',))
        self.definition = TestCase('API-001', 'API health', TestType.API, ('api',),
                                   ('Request configured health endpoint',), 'Healthy status is returned.')

    def test_configuration_uses_references_instead_of_raw_tokens(self):
        configuration = ApiConfiguration(self.project, SecretReference('QA_API_TOKEN'))
        self.assertEqual(configuration.bearer_token.environment_variable, 'QA_API_TOKEN')
        with self.assertRaises(ValueError):
            ApiConfiguration(self.project, 'raw-secret')

    def test_configuration_requires_origin_and_bounded_limits(self):
        for values in ({'timeout_seconds': True}, {'timeout_seconds': float('nan')},
                       {'timeout_seconds': 11}, {'max_response_bytes': True}, {'max_response_bytes': 0}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                ApiConfiguration(self.project, **values)
        for suffix in ('/api', '/?token=secret', '/#fragment'):
            with self.assertRaises(ValueError):
                ApiConfiguration(replace(self.project, base_url=self.project.base_url + suffix))

    def test_absolute_external_or_ambiguous_paths_are_rejected(self):
        for path in ('https://other.example/', '//other.example/', '/api?token=x', '/api#x',
                     '/api/../secret', '/api/%2e%2e', '/api\\secret', '/api\nheader', '/api space', '/api/ürün'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                ApiRequest(path)

    def test_query_and_body_are_not_in_representations(self):
        request = ApiRequest('/api/echo', HttpMethod.POST, (('value', 'query-secret'),),
                             '{"value":"body-secret"}')
        self.assertNotIn('query-secret', repr(request))
        self.assertNotIn('body-secret', repr(request))

    def test_query_structure_and_duplicate_keys_are_validated(self):
        for query in ([('q', 'a')], (('q', 'a'), ('q', 'b')), (('bad-key', 'a'),), (('q', '\n'),)):
            with self.subTest(query=query), self.assertRaises(ValueError):
                ApiRequest('/api/search', query=query)

    def test_methods_and_authentication_flags_require_typed_values(self):
        for values in ({'method': 'GET'}, {'use_authentication': 'true'}):
            with self.assertRaises(ValueError):
                ApiRequest('/api/health', **values)

    def test_json_bodies_reject_invalid_nonfinite_and_read_method_payloads(self):
        for body in ('not-json', '{"value":NaN}', '{"value":1e400}', '{"id":1,"id":2}', 'x' * 65537):
            with self.subTest(body=body[:20]), self.assertRaises(ValueError):
                ApiRequest('/api/echo', HttpMethod.POST, body_json=body)
        with self.assertRaises(ValueError):
            ApiRequest('/api/health', body_json='{}')

    def test_json_paths_and_operands_are_explicit(self):
        JsonCheck(('items', 0, 'id'), JsonOperator.TYPE, JsonType.INTEGER)
        for path in (['items'], (True,), (-1,), ('',), ('a',) * 9):
            with self.subTest(path=path), self.assertRaises(ValueError):
                JsonCheck(path, JsonOperator.EXISTS)

    def test_operator_operand_mismatches_are_rejected(self):
        for operator, expected in ((JsonOperator.EXISTS, True), (JsonOperator.TYPE, 'integer'),
                                   (JsonOperator.MINIMUM, True), (JsonOperator.MAXIMUM, float('inf')),
                                   (JsonOperator.LENGTH, -1), (JsonOperator.EQUALS, {})):
            with self.subTest(operator=operator), self.assertRaises(ValueError):
                JsonCheck(('value',), operator, expected)
        self.assertNotIn('private-value', repr(JsonCheck(('value',), JsonOperator.EQUALS, 'private-value')))

    def test_mutating_methods_require_data_change_declaration(self):
        request = ApiRequest('/api/items', HttpMethod.POST, body_json='{}')
        with self.assertRaises(ValueError):
            ApiCase(self.definition, request)
        ApiCase(replace(self.definition, changes_data=True), request)

    def test_api_case_rejects_ui_definition_invalid_status_and_untyped_checks(self):
        for values in ({'definition': replace(self.definition, test_type=TestType.UI)},
                       {'expected_status': True}, {'expected_status': 600}, {'checks': []}):
            arguments = {'definition': self.definition, 'request': ApiRequest('/api/health'), **values}
            with self.subTest(values=values), self.assertRaises(ValueError):
                ApiCase(**arguments)

    def test_head_and_non_json_cases_cannot_assert_body(self):
        check = JsonCheck((), JsonOperator.TYPE, JsonType.OBJECT)
        with self.assertRaises(ValueError):
            ApiCase(self.definition, ApiRequest('/api/health', HttpMethod.HEAD))
        ApiCase(self.definition, ApiRequest('/api/health', HttpMethod.HEAD), expect_json=False)
        with self.assertRaises(ValueError):
            ApiCase(self.definition, ApiRequest('/api/health'), checks=(check,), expect_json=False)
