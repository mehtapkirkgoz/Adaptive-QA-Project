"""Tests for sample catalog registration and execution selection."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.local_browser import run_sample_test
from adaptive_qa.models import TestStatus
from adaptive_qa.smoke_checks import SMOKE_CHECKS


class SmokeCatalogTests(unittest.TestCase):
    def test_catalog_and_executors_have_matching_unique_identifiers(self) -> None:
        identifiers = [case.case_id for case in TEST_CASES]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(set(identifiers), set(SMOKE_CHECKS))

    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_unknown_case_is_blocked_without_browser(self, verify) -> None:
        result = run_sample_test("UNKNOWN-001")
        self.assertEqual(result.status, TestStatus.BLOCKED)
        verify.assert_not_called()

    @patch("adaptive_qa.local_browser._verify_sample_page")
    def test_search_case_is_forwarded_to_browser_verifier(self, verify) -> None:
        with TemporaryDirectory() as temporary:
            with patch("adaptive_qa.local_browser.Path", return_value=Path(temporary)):
                result = run_sample_test("SEARCH-002")
        self.assertEqual(result.case_id, "SEARCH-002")
        self.assertEqual(result.status, TestStatus.PASSED)
        self.assertEqual(verify.call_args.kwargs["case_id"], "SEARCH-002")


if __name__ == "__main__":
    unittest.main()
