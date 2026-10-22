"""Budget, coverage, and authorization contracts for bounded traversal."""

from dataclasses import replace
import subprocess
import unittest
from unittest.mock import Mock, patch

from adaptive_qa.crawler import CrawlBudget, canonical_url, crawl_pages
from adaptive_qa.discovery import LinkSnapshot, PageSnapshot
from adaptive_qa.egress import DestinationGuard
from adaptive_qa.config import ProjectConfig
from adaptive_qa.local_discovery import discover_local_sample


class CrawlerTests(unittest.TestCase):
    def run_graph(self, graph, budget=CrawlBudget(), **kwargs):
        def authorize(url):
            if not url.startswith('https://example.com/'):
                raise ValueError('Denied')
        self.loaded = []
        def load(url, remaining):
            self.assertGreater(remaining, 0)
            self.loaded.append(url)
            value = graph[url]
            if isinstance(value, Exception):
                raise value
            return PageSnapshot(url, links=tuple(LinkSnapshot('', item) for item in value),
                                collection_complete=True)
        return crawl_pages('https://example.com', budget, authorize=authorize, load=load, **kwargs)

    def test_breadth_first_order_and_cycle_deduplication(self):
        result = self.run_graph({'https://example.com/': ['/a', '/b', '/a#repeat'],
                                 'https://example.com/a': ['/', '/c'],
                                 'https://example.com/b': ['/c'],
                                 'https://example.com/c': []})
        self.assertEqual(self.loaded, ['https://example.com/', 'https://example.com/a',
                                       'https://example.com/b', 'https://example.com/c'])
        self.assertEqual(result.limitations, ())

    def test_page_budget_counts_failed_attempts(self):
        result = self.run_graph({'https://example.com/': ['/a', '/b'],
                                 'https://example.com/a': RuntimeError('secret')},
                                replace(CrawlBudget(), max_pages=2))
        self.assertEqual(result.attempted_pages, 2)
        self.assertEqual(len(result.pages), 1)
        self.assertIn('page_limit', result.limitations)
        self.assertIn('page_load_or_policy_error', result.limitations)
        self.assertNotIn('secret', repr(result))

    def test_depth_zero_collects_only_start_page(self):
        result = self.run_graph({'https://example.com/': ['/a']},
                                replace(CrawlBudget(), max_depth=0))
        self.assertEqual(result.attempted_pages, 1)
        self.assertIn('depth_limit', result.limitations)

    def test_external_and_non_http_links_are_never_loaded(self):
        result = self.run_graph({'https://example.com/': ['https://other.example/', 'javascript:x']})
        self.assertEqual(self.loaded, ['https://example.com/'])
        self.assertIn('excluded_link', result.limitations)

    def test_time_budget_stops_before_navigation(self):
        result = self.run_graph({}, clock=Mock(side_effect=[0, 31]))
        self.assertEqual(result.attempted_pages, 0)
        self.assertEqual(result.limitations, ('time_limit',))

    def test_collection_after_deadline_is_not_published(self):
        result = self.run_graph({'https://example.com/': []}, clock=Mock(side_effect=[0, 0, 31]))
        self.assertEqual(result.pages, ())
        self.assertIn('time_limit', result.limitations)

    def test_incomplete_snapshot_preserves_coverage_limitation(self):
        result = crawl_pages('https://example.com', CrawlBudget(), authorize=lambda url: None,
                             load=lambda url, remaining: PageSnapshot(url))
        self.assertIn('incomplete_page', result.limitations)

    def test_redirect_destination_is_reauthorized(self):
        def authorize(url):
            if 'other.example' in url:
                raise ValueError('Denied')
        result = crawl_pages('https://example.com', CrawlBudget(), authorize=authorize,
                             load=lambda url, remaining: PageSnapshot('https://other.example/'))
        self.assertEqual(result.pages, ())
        self.assertIn('page_load_or_policy_error', result.limitations)

    def test_redirect_to_visited_page_is_not_published_twice(self):
        root = PageSnapshot('https://example.com/', links=(LinkSnapshot('', '/redirect'),),
                            collection_complete=True)
        result = crawl_pages(root.url, CrawlBudget(), authorize=lambda url: None,
                             load=lambda url, remaining: root)
        self.assertEqual(result.pages, (root,))
        self.assertEqual(result.attempted_pages, 2)

    def test_query_fragment_default_port_and_hostname_are_normalized(self):
        self.assertEqual(canonical_url('https://EXAMPLE.com:443/a?token=secret#login'),
                         'https://example.com/a')
        self.assertEqual(canonical_url('http://[::1]:8000'), 'http://[::1]:8000/')

    def test_credentials_and_invalid_targets_are_rejected(self):
        for url in ('https://user:pass@example.com/', 'file:///tmp/test',
                    'https://example.com/' + 'a' * 2048):
            with self.subTest(url=url[:50]), self.assertRaises(ValueError):
                canonical_url(url)

    def test_budget_rejects_invalid_values(self):
        for values in ({'max_pages': True}, {'max_pages': 51}, {'max_depth': -1},
                       {'max_requests': 201}, {'timeout_seconds': float('nan')},
                       {'timeout_seconds': True}, {'timeout_seconds': 0}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                CrawlBudget(**values)

    def test_guard_enforces_configured_request_limit(self):
        project = ProjectConfig('demo', 'Demo', 'http://127.0.0.1:8000', ('127.0.0.1',))
        guard = DestinationGuard(project, local_sample=True, max_requests=1)
        guard.authorize(project.base_url)
        with self.assertRaisesRegex(ValueError, 'request budget'):
            guard.authorize(project.base_url)
        for value in (True, 0, 201):
            with self.assertRaises(ValueError):
                DestinationGuard(project, max_requests=value)

    @patch('adaptive_qa.local_discovery._terminate_process_tree')
    @patch('adaptive_qa.local_discovery.subprocess.Popen')
    def test_hard_deadline_terminates_process_tree(self, popen, terminate):
        process = popen.return_value
        process.wait.side_effect = subprocess.TimeoutExpired('discovery', 1)
        process.poll.return_value = None
        terminate.side_effect = lambda child: setattr(child.poll, 'return_value', -1)
        with patch('adaptive_qa.local_discovery.monotonic', side_effect=(0, 2)):
            result = discover_local_sample(CrawlBudget(timeout_seconds=1))
        terminate.assert_called_once_with(process)
        self.assertEqual(result['limitations'], ['time_limit'])
        self.assertTrue(result['partial_results_discarded'])


if __name__ == '__main__':
    unittest.main()
