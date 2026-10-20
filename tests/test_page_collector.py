"""Verify typed conversion and conservative collector failure behavior."""

import unittest
from unittest.mock import Mock

from playwright.sync_api import Error

from adaptive_qa.discovery import FieldSnapshot, LinkSnapshot
from adaptive_qa.page_collector import collect_page_snapshot


class PageCollectorTests(unittest.TestCase):
    def test_payload_converts_to_immutable_models(self):
        page = Mock()
        page.evaluate.return_value = {
            'url': 'https://example.com/', 'collection_complete': False,
            'forms': [{'form_id': 'search', 'role': 'search', 'buttons': ['Search'],
                       'fields': [{'input_type': 'search', 'label': 'Query', 'autocomplete': ''}]}],
            'links': [{'text': 'Login', 'href': 'https://example.com/login'}],
        }
        result = collect_page_snapshot(page)
        self.assertFalse(result.collection_complete)
        self.assertEqual(result.forms[0].buttons, ('Search',))
        self.assertEqual(result.forms[0].fields, (FieldSnapshot('search', 'Query'),))
        self.assertEqual(result.links, (LinkSnapshot('Login', 'https://example.com/login'),))
        page.goto.assert_not_called()

    def test_browser_error_is_not_converted_to_empty_complete_snapshot(self):
        page = Mock()
        page.evaluate.side_effect = Error('Page closed')
        with self.assertRaises(Error):
            collect_page_snapshot(page)

    def test_invalid_page_url_is_rejected(self):
        page = Mock()
        page.evaluate.return_value = {'url': None, 'forms': [], 'links': [],
                                      'collection_complete': True}
        with self.assertRaises(ValueError):
            collect_page_snapshot(page)


if __name__ == '__main__':
    unittest.main()
