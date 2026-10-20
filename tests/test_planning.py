"""Coverage-aware aggregation and non-executing test-plan decisions."""

from dataclasses import replace
import unittest

from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlResult
from adaptive_qa.discovery import CommerceSnapshot, FieldSnapshot, FormSnapshot, LinkSnapshot, PageSnapshot
from adaptive_qa.models import FeatureStatus, TestCase, TestType
from adaptive_qa.planning import PlanDecision, assess_discovery, build_test_plan


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectConfig('demo', 'Demo', 'https://example.com/', ('example.com',))
        self.login = FormSnapshot(fields=(FieldSnapshot('email'), FieldSnapshot('password')),
                                  buttons=('Sign in',))
        self.search = FormSnapshot(role='search', fields=(FieldSnapshot('search'),), buttons=('Search',))
        self.case = TestCase('CHECK-001', 'Example check', TestType.UI, ('login',),
                             ('Inspect login',), 'Login controls are visible.')

    def page(self, path='/', **kwargs):
        return PageSnapshot('https://example.com' + path, collection_complete=True, **kwargs)

    def crawl(self, *pages, limitations=()):
        return CrawlResult(tuple(pages), len(pages), limitations)

    def summary(self, crawl):
        return {item.feature: item for item in assess_discovery(crawl).features}

    def entry(self, crawl, case=None, project=None):
        return build_test_plan(crawl, (case or self.case,), project or self.project).cases[0]

    def test_positive_evidence_wins_over_other_page_absence_and_limits(self):
        result = self.summary(self.crawl(self.page(), self.page('/login', forms=(self.login,)),
                                         limitations=('page_limit',)))['login']
        self.assertEqual(result.status, FeatureStatus.PRESENT)
        self.assertEqual(result.page_urls, ('https://example.com/login',))
        self.assertEqual(result.scope, 'inspected_pages')

    def test_absence_requires_complete_pages_without_limitations(self):
        result = self.summary(self.crawl(self.page(), self.page('/about')))['login']
        self.assertEqual(result.status, FeatureStatus.ABSENT)
        self.assertIn('does not establish site-wide absence', result.reason)

    def test_any_traversal_limitation_prevents_absence(self):
        for reason in ('page_limit', 'depth_limit', 'time_limit', 'request_limit', 'excluded_link',
                       'page_load_or_policy_error', 'network_policy_denial'):
            with self.subTest(reason=reason):
                self.assertEqual(self.summary(self.crawl(self.page(), limitations=(reason,)))['login'].status,
                                 FeatureStatus.UNKNOWN)

    def test_empty_discovery_never_implies_absence(self):
        self.assertTrue(all(item.status == FeatureStatus.UNKNOWN
                            for item in assess_discovery(self.crawl()).features))

    def test_incomplete_page_prevents_absence(self):
        page = replace(self.page(), collection_complete=False)
        self.assertEqual(self.summary(self.crawl(page))['login'].status, FeatureStatus.UNKNOWN)

    def test_weak_hint_prevents_aggregate_absence(self):
        page = self.page('/account', links=(LinkSnapshot('Sign in', '/login'),))
        self.assertEqual(self.summary(self.crawl(self.page(), page))['login'].status, FeatureStatus.UNKNOWN)

    def test_selected_case_binds_to_positive_page_with_evidence(self):
        entry = self.entry(self.crawl(self.page(), self.page('/login', forms=(self.login,))))
        self.assertEqual(entry.decision, PlanDecision.SELECTED)
        self.assertEqual(entry.target_url, 'https://example.com/login')
        self.assertEqual(entry.evidence, ('login: form[0]',))

    def test_positive_feature_can_be_selected_despite_traversal_limit(self):
        entry = self.entry(self.crawl(self.page(forms=(self.login,)), limitations=('depth_limit',)))
        self.assertEqual(entry.decision, PlanDecision.SELECTED)

    def test_absent_prerequisite_is_skipped_with_explicit_scope(self):
        entry = self.entry(self.crawl(self.page()))
        self.assertEqual(entry.decision, PlanDecision.SKIPPED)
        self.assertIn('Uninspected routes are outside this plan', entry.reason)
        self.assertIsNone(entry.target_url)

    def test_uncertain_and_unsupported_features_are_blocked(self):
        for name in ('login', 'navigation', 'unknown-feature'):
            with self.subTest(name=name):
                case = replace(self.case, required_features=(name,))
                entry = self.entry(self.crawl(self.page(), limitations=('page_limit',)), case)
                self.assertEqual(entry.decision, PlanDecision.BLOCKED)
                self.assertIn(name, entry.reason)

    def test_policy_blocks_data_changes(self):
        entry = self.entry(self.crawl(self.page(forms=(self.login,))), replace(self.case, changes_data=True))
        self.assertEqual(entry.decision, PlanDecision.BLOCKED)
        self.assertIn('policy', entry.reason)

    def test_allowed_data_changes_still_do_not_authorize_execution(self):
        plan = build_test_plan(self.crawl(self.page(forms=(self.login,))),
                               (replace(self.case, changes_data=True),),
                               replace(self.project, allow_data_changes=True))
        self.assertEqual(plan.cases[0].decision, PlanDecision.SELECTED)
        self.assertFalse(plan.execution_authorized)

    def test_api_and_database_require_configuration_contracts(self):
        for kind in (TestType.API, TestType.DATABASE):
            with self.subTest(kind=kind):
                entry = self.entry(self.crawl(self.page(forms=(self.login,))), replace(self.case, test_type=kind))
                self.assertEqual(entry.decision, PlanDecision.BLOCKED)
                self.assertIn('adapter', entry.reason)

    def test_multiple_prerequisites_require_same_page(self):
        case = replace(self.case, required_features=('login', 'search'))
        entry = self.entry(self.crawl(self.page('/login', forms=(self.login,)),
                                     self.page('/search', forms=(self.search,))), case)
        self.assertEqual(entry.decision, PlanDecision.BLOCKED)
        self.assertIn('multi-page binding', entry.reason)
        combined = self.entry(self.crawl(self.page(forms=(self.login, self.search))), case)
        self.assertEqual(combined.decision, PlanDecision.SELECTED)

    def test_case_without_feature_prerequisites_still_needs_a_page(self):
        case = replace(self.case, required_features=())
        self.assertEqual(self.entry(self.crawl(), case).decision, PlanDecision.BLOCKED)
        self.assertEqual(self.entry(self.crawl(self.page()), case).decision, PlanDecision.SELECTED)

    def test_unauthorized_page_is_rejected(self):
        with self.assertRaises(ValueError):
            self.entry(self.crawl(PageSnapshot('https://other.example/')))

    def test_duplicate_case_identifiers_and_invalid_collections_are_rejected(self):
        for cases in ([self.case], (self.case, self.case), ('invalid',)):
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                build_test_plan(self.crawl(), cases, self.project)
        for crawl in (None, CrawlResult([], 0, ()), CrawlResult((), 0, ('',))):
            with self.assertRaises(ValueError):
                assess_discovery(crawl)

    def test_existing_catalog_selects_eight_cases_and_blocks_navigation(self):
        plan = build_test_plan(self.crawl(self.page(forms=(self.login, self.search))), TEST_CASES, self.project)
        self.assertEqual(sum(item.decision == PlanDecision.SELECTED for item in plan.cases), 8)
        self.assertEqual(sum(item.decision == PlanDecision.BLOCKED for item in plan.cases), 2)
        self.assertFalse(plan.execution_authorized)

    def test_commerce_presence_does_not_invent_login(self):
        product = CommerceSnapshot('product', name='Demo', has_price=True,
                                    has_currency=True, actions=('Add to cart',))
        result = self.summary(self.crawl(self.page(commerce=(product,))))
        self.assertEqual(result['product'].status, FeatureStatus.PRESENT)
        self.assertEqual(result['cart'].status, FeatureStatus.UNKNOWN)
        self.assertEqual(result['login'].status, FeatureStatus.ABSENT)

    def test_duplicate_page_urls_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_discovery(self.crawl(self.page(), self.page(forms=(self.login,))))

    def test_plain_and_commerce_pages_produce_different_plans(self):
        cases = tuple(replace(self.case, case_id=name.upper(), required_features=(name,))
                      for name in ('registration', 'product', 'cart'))
        form = FormSnapshot(fields=(FieldSnapshot('email'),
                                    FieldSnapshot('password', autocomplete='new-password')),
                            buttons=('Register',))
        product = CommerceSnapshot('product', name='Demo', has_price=True,
                                    has_currency=True, actions=('Add to cart',))
        cart = CommerceSnapshot('cart', name='Cart', empty=True)
        plain = build_test_plan(self.crawl(self.page()), cases, self.project)
        commerce = build_test_plan(self.crawl(self.page(forms=(form,), commerce=(product, cart))),
                                   cases, self.project)
        self.assertTrue(all(item.decision == PlanDecision.SKIPPED for item in plain.cases))
        self.assertTrue(all(item.decision == PlanDecision.SELECTED for item in commerce.cases))


if __name__ == '__main__':
    unittest.main()
