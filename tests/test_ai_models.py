"""AI proposals stay typed, bounded, advisory, and independent of providers."""

from dataclasses import replace
import unittest

from adaptive_qa.ai_models import AiAdvice, AiBudget, ElementAdvice, FeatureAdvice, WebsiteKind
from adaptive_qa.models import FeatureStatus


class AiModelTests(unittest.TestCase):
    def test_advice_cannot_request_execution_authorization(self):
        advice = AiAdvice(WebsiteKind.UNKNOWN, 0)
        self.assertFalse(advice.execution_authorized)
        with self.assertRaises(TypeError):
            AiAdvice(WebsiteKind.COMMERCE, 1, execution_authorized=True)

    def test_confidence_rejects_boolean_nonfinite_and_out_of_range(self):
        for value in (True, float('nan'), float('inf'), -0.1, 1.1, '1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AiAdvice(WebsiteKind.GENERAL, value)

    def test_feature_advice_requires_known_features_and_evidence(self):
        valid = FeatureAdvice('login', FeatureStatus.PRESENT, 0.9, ('form_1',))
        for values in ({'feature': 'execute_sql'}, {'status': 'present'}, {'evidence_ids': ()},
                       {'evidence_ids': ('form_1', 'form_1')}, {'evidence_ids': ('https://evil.test',)}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(valid, **values)

    def test_duplicate_features_and_logical_elements_are_rejected(self):
        feature = FeatureAdvice('search', FeatureStatus.UNKNOWN, 0.1, ('form_1',))
        element = ElementAdvice('login.submit', 'button_1', 0.9)
        for values in ({'features': (feature, feature)}, {'elements': (element, element)},
                       {'features': [feature]}, {'website_kind': 'commerce'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                AiAdvice(**({'website_kind': WebsiteKind.UNKNOWN, 'confidence': 0} | values))

    def test_budgets_default_to_no_paid_usage_and_reject_invalid_limits(self):
        budget = AiBudget()
        self.assertEqual(budget.max_cost_microusd, 0)
        for values in ({'max_requests': True}, {'timeout_seconds': 0},
                       {'max_input_bytes': 65537}, {'max_output_bytes': -1},
                       {'max_cost_microusd': -1}, {'max_cost_microusd': True}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(budget, **values)
