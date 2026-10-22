"""Feature prerequisites and inspection budgets for semantic browser rules."""

import unittest
from unittest.mock import Mock
from adaptive_qa.semantic_checks import SEMANTIC_CASES, SEMANTIC_CHECKS, check_button_names
from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlResult
from adaptive_qa.discovery import PageSnapshot
from adaptive_qa.planning import build_test_plan


class SemanticCatalogTests(unittest.TestCase):
    def test_registry_and_read_only_definitions_agree(self):
        self.assertEqual(set(SEMANTIC_CHECKS), {case.case_id for case in SEMANTIC_CASES})
        self.assertTrue(all(not case.changes_data for case in SEMANTIC_CASES))

    def test_absent_features_skip_but_uncertain_features_block(self):
        project = ProjectConfig('semantic', 'Semantic', 'http://127.0.0.1:8000/', ('127.0.0.1',))
        for complete, expected in ((True, 'skipped'), (False, 'blocked')):
            crawl = CrawlResult((PageSnapshot(project.base_url, collection_complete=complete),), 1, ())
            plan = build_test_plan(crawl, SEMANTIC_CASES, project)
            by_id = {case.case_id: case for case in plan.cases}
            for case in SEMANTIC_CASES:
                self.assertEqual(by_id[case.case_id].decision, expected if case.required_features else 'selected')
            self.assertFalse(plan.execution_authorized)

    def test_missing_inspection_never_authorizes_generic_rules(self):
        project = ProjectConfig('semantic', 'Semantic', 'http://127.0.0.1:8000/', ('127.0.0.1',))
        plan = build_test_plan(CrawlResult((), 0, ()), SEMANTIC_CASES, project)
        self.assertTrue(all(case.decision == 'blocked' for case in plan.cases))

    def test_large_role_collection_is_bounded_before_element_inspection(self):
        page = Mock()
        page.get_by_role.return_value.count.return_value = 501
        with self.assertRaisesRegex(RuntimeError, 'budget'):
            check_button_names(page)
        page.get_by_role.return_value.nth.assert_not_called()
