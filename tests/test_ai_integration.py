"""AI cannot change original plan decisions or weaken host matching policy."""

from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from adaptive_qa.ai_integration import AiElementCandidate, match_with_ai_fallback, review_plan_with_ai
from adaptive_qa.ai_models import AiAdvice, AiBudget, ElementAdvice, FeatureAdvice, WebsiteKind
from adaptive_qa.ai_runtime import AiOutcome
from adaptive_qa.ai_validation import reduce_ai_input
from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlResult
from adaptive_qa.discovery import FieldSnapshot, FormSnapshot, PageSnapshot
from adaptive_qa.element_matching import BoundElement
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy, MatchResult, MatchStatus
from adaptive_qa.models import FeatureStatus, TestCase, TestType
from adaptive_qa.planning import build_test_plan


class AiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.page = PageSnapshot('https://example.test', forms=(FormSnapshot(
            fields=(FieldSnapshot('email'), FieldSnapshot('password')), buttons=('Sign in',)),), collection_complete=True)
        self.reduced = reduce_ai_input(self.page, AiBudget())
        project = ProjectConfig('test', 'Test', self.page.url, ('example.test',))
        self.cases = tuple(TestCase(f'TEST-{n}', 'Check', TestType.UI, (feature,),
            ('Inspect controls',), 'Expected controls are visible.', changes_data=write)
            for n, feature, write in ((1, 'login', False), (2, 'cart', False), (3, 'login', True)))
        self.plan = build_test_plan(CrawlResult((self.page,), 1, ()), self.cases, project)
        self.advice = AiAdvice(WebsiteKind.COMMERCE, 0.99,
            (FeatureAdvice('login', FeatureStatus.PRESENT, 0.99, ('form_0',)),
             FeatureAdvice('cart', FeatureStatus.PRESENT, 0.99, ('form_0',))),
            (ElementAdvice('login.submit', 'button_0_0', 0.99),))
        self.outcome = AiOutcome('accepted', 'Validated.', self.advice)
        self.default = ElementMapping('login.submit', (LocatorSpec(LocatorStrategy.ROLE, 'Missing', 'button'),))
        self.candidate = AiElementCandidate('button_0_0', ElementMapping('login.submit',
            (LocatorSpec(LocatorStrategy.ROLE, 'Sign in', 'button'),)))

    def test_plan_is_preserved_and_unsupported_or_policy_blocked_cases_never_prioritized(self):
        review = review_plan_with_ai(self.plan, self.cases, self.outcome)
        self.assertIs(review.plan, self.plan)
        self.assertEqual(review.supported_features, ('login',))
        self.assertEqual(review.prioritized_case_ids, ('TEST-1',))
        self.assertFalse(review.execution_authorized)
        self.assertFalse(review.plan.execution_authorized)

    def test_outages_and_low_confidence_preserve_deterministic_plan(self):
        for outcome in (AiOutcome('timeout', 'Timed out.'),
                        AiOutcome('accepted', 'Low confidence.', replace(self.advice,
                            confidence=0.1, features=()))):
            review = review_plan_with_ai(self.plan, self.cases, outcome)
            self.assertEqual(review.website_kind, WebsiteKind.UNKNOWN)
            self.assertEqual(review.prioritized_case_ids, ())
            self.assertIs(review.plan, self.plan)

    def test_mismatched_cases_and_bad_thresholds_are_rejected(self):
        with self.assertRaises(ValueError):
            review_plan_with_ai(self.plan, self.cases[::-1], self.outcome)
        for threshold in (True, float('nan'), 0.4, 1.1):
            with self.assertRaises(ValueError):
                review_plan_with_ai(self.plan, self.cases, self.outcome, threshold=threshold)

    def bound(self, status):
        count = 2 if status == MatchStatus.AMBIGUOUS else 1 if status == MatchStatus.MATCHED else 0
        return BoundElement(MatchResult('login.submit', status, count, 'Controlled result.',
                                        (0,) if count else ()), Mock() if count == 1 else None)

    def test_ambiguous_error_matched_and_explicit_mappings_never_use_ai_fallback(self):
        for status, explicit in ((MatchStatus.AMBIGUOUS, False), (MatchStatus.ERROR, False),
                                 (MatchStatus.MATCHED, False), (MatchStatus.MISSING, True)):
            original = self.bound(status)
            with patch('adaptive_qa.ai_integration.match_element', return_value=original) as matcher:
                result = match_with_ai_fallback(None, self.default, self.outcome, self.reduced,
                    (self.candidate,), explicit_project_mapping=explicit)
                self.assertIs(result, original)
                matcher.assert_called_once()

    def test_missing_match_uses_only_one_host_registered_collected_candidate(self):
        missing, matched = self.bound(MatchStatus.MISSING), self.bound(MatchStatus.MATCHED)
        with patch('adaptive_qa.ai_integration.match_element', side_effect=(missing, matched)) as matcher:
            result = match_with_ai_fallback(None, self.default, self.outcome, self.reduced, (self.candidate,))
        self.assertIs(result, matched)
        self.assertEqual(matcher.call_args.args[1], self.candidate.mapping)

    def test_duplicate_host_bindings_and_low_confidence_do_not_fallback(self):
        low = replace(self.advice, elements=(replace(self.advice.elements[0], confidence=0.2),))
        for outcome, candidates in ((self.outcome, (self.candidate, self.candidate)),
                                    (AiOutcome('accepted', 'Low.', low), (self.candidate,))):
            with patch('adaptive_qa.ai_integration.match_element', return_value=self.bound(MatchStatus.MISSING)) as matcher:
                match_with_ai_fallback(None, self.default, outcome, self.reduced, candidates)
                matcher.assert_called_once()

    def test_incomplete_collection_or_unknown_feature_prevents_confident_element_fallback(self):
        uncertain = replace(self.advice, features=(replace(self.advice.features[0], status=FeatureStatus.UNKNOWN),))
        for reduced, outcome in ((replace(self.reduced, collection_complete=False), self.outcome),
                                  (self.reduced, AiOutcome('accepted', 'Unknown feature.', uncertain))):
            with patch('adaptive_qa.ai_integration.match_element', return_value=self.bound(MatchStatus.MISSING)) as matcher:
                match_with_ai_fallback(None, self.default, outcome, reduced, (self.candidate,))
                matcher.assert_called_once()

    def test_feature_evidence_from_a_different_form_does_not_authorize_candidate(self):
        other = replace(self.advice, features=(replace(self.advice.features[0], evidence_ids=('form_1',)),))
        with patch('adaptive_qa.ai_integration.match_element', return_value=self.bound(MatchStatus.MISSING)) as matcher:
            match_with_ai_fallback(None, self.default, AiOutcome('accepted', 'Other form.', other),
                                  self.reduced, (self.candidate,))
            matcher.assert_called_once()
