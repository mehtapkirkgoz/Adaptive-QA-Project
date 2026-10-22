"""Registry coverage and method policy declarations for the API catalog."""

import unittest

from adaptive_qa.api_catalog import API_BY_ID, API_CASES
from adaptive_qa.api_models import HttpMethod
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.api_models import ApiConfiguration
from adaptive_qa.api_transport import ApiExchange, run_api_case
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestStatus
from unittest.mock import patch


class ApiCatalogTests(unittest.TestCase):
    def test_thirty_four_distinct_api_ids_do_not_overlap_ui_catalog(self):
        ids = [case.definition.case_id for case in API_CASES]
        self.assertEqual(len(ids), 34)
        self.assertEqual(len(set(ids)), 34)
        self.assertEqual(set(ids), set(API_BY_ID))
        self.assertFalse(set(ids) & {case.case_id for case in TEST_CASES})
        self.assertEqual(len(TEST_CASES) + len(API_CASES), 85)

    def test_non_read_cases_declare_data_changes(self):
        for case in API_CASES:
            if case.request.method not in (HttpMethod.GET, HttpMethod.HEAD):
                self.assertTrue(case.definition.changes_data)

    def test_new_contracts_are_read_only_and_block_without_configuration(self):
        for case in API_CASES[20:]:
            with self.subTest(case=case.definition.case_id):
                self.assertEqual(case.request.method, HttpMethod.GET)
                self.assertFalse(case.definition.changes_data)
                with patch('adaptive_qa.api_transport.perform_request') as transport:
                    self.assertEqual(run_api_case(case, None).status, TestStatus.BLOCKED)
                    transport.assert_not_called()

    def test_new_contracts_detect_wrong_payload_even_with_correct_http_status(self):
        configuration = ApiConfiguration(ProjectConfig('api', 'API', 'http://127.0.0.1:8000', ('127.0.0.1',)))
        for case in API_CASES[20:]:
            with self.subTest(case=case.definition.case_id):
                exchange = ApiExchange(case.expected_status, True, True, {})
                with patch('adaptive_qa.api_transport.perform_request', return_value=exchange):
                    self.assertEqual(run_api_case(case, configuration).status, TestStatus.FAILED)
