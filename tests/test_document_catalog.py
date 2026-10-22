"""Document rules apply without invented login or commerce prerequisites."""

import unittest
from adaptive_qa.document_checks import DOCUMENT_CASES, DOCUMENT_CHECKS
from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlResult
from adaptive_qa.discovery import PageSnapshot
from adaptive_qa.planning import build_test_plan


class DocumentCatalogTests(unittest.TestCase):
    def test_rules_are_read_only_and_registered_once(self):
        self.assertEqual({case.case_id for case in DOCUMENT_CASES}, set(DOCUMENT_CHECKS))
        self.assertTrue(all(not case.changes_data and not case.required_features for case in DOCUMENT_CASES))

    def test_no_discovery_blocks_but_inspected_plain_page_is_applicable(self):
        project = ProjectConfig('document', 'Document', 'http://127.0.0.1:8000/', ('127.0.0.1',))
        empty = build_test_plan(CrawlResult((), 0, ()), DOCUMENT_CASES, project)
        self.assertTrue(all(case.decision == 'blocked' for case in empty.cases))
        crawl = CrawlResult((PageSnapshot(project.base_url, collection_complete=True),), 0, ())
        plan = build_test_plan(crawl, DOCUMENT_CASES, project)
        self.assertTrue(all(case.decision == 'selected' and case.target_url == project.base_url for case in plan.cases))
        self.assertTrue(all(case.evidence == ('page: inspected document snapshot',) for case in plan.cases))
        self.assertFalse(plan.execution_authorized)
