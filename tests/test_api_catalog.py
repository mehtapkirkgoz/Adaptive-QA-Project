"""Registry coverage and method policy declarations for the API catalog."""

import unittest

from adaptive_qa.api_catalog import API_BY_ID, API_CASES
from adaptive_qa.api_models import HttpMethod
from adaptive_qa.catalog import TEST_CASES


class ApiCatalogTests(unittest.TestCase):
    def test_twenty_distinct_api_ids_do_not_overlap_ui_catalog(self):
        ids = [case.definition.case_id for case in API_CASES]
        self.assertEqual(len(ids), 20)
        self.assertEqual(len(set(ids)), 20)
        self.assertEqual(set(ids), set(API_BY_ID))
        self.assertFalse(set(ids) & {case.case_id for case in TEST_CASES})
        self.assertEqual(len(TEST_CASES) + len(API_CASES), 65)

    def test_non_read_cases_declare_data_changes(self):
        for case in API_CASES:
            if case.request.method not in (HttpMethod.GET, HttpMethod.HEAD):
                self.assertTrue(case.definition.changes_data)
