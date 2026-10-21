"""Verify evaluation denominators and intentional wrong/abstaining decisions."""

import unittest

from adaptive_qa.ai_evaluation import AiEvaluationCase, evaluate_ai_decisions
from adaptive_qa.ai_models import AiAdvice, ElementAdvice, FeatureAdvice, WebsiteKind
from adaptive_qa.ai_runtime import AiOutcome
from adaptive_qa.models import FeatureStatus


class AiEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = (AiEvaluationCase('login', WebsiteKind.GENERAL,
            (('login', FeatureStatus.PRESENT),), (('login.submit', 'button_0'),)),
            AiEvaluationCase('plain', WebsiteKind.GENERAL, (('login', FeatureStatus.ABSENT),)),
            AiEvaluationCase('uncertain', WebsiteKind.UNKNOWN, (('login', FeatureStatus.UNKNOWN),),
                             (('login.submit', None),)))
        self.outcomes = (
            AiOutcome('accepted', 'Correct.', AiAdvice(WebsiteKind.GENERAL, 0.99,
                (FeatureAdvice('login', FeatureStatus.PRESENT, 0.99, ('form_0',)),),
                (ElementAdvice('login.submit', 'button_0', 0.99),))),
            AiOutcome('accepted', 'Intentionally wrong.', AiAdvice(WebsiteKind.COMMERCE, 0.99,
                (FeatureAdvice('login', FeatureStatus.PRESENT, 0.99, ('form_0',)),))),
            AiOutcome('timeout', 'Abstained.'))

    def test_metrics_expose_wrong_high_confidence_predictions_and_abstention(self):
        report = evaluate_ai_decisions(self.cases, self.outcomes, mode='offline_scripted')
        self.assertEqual((report['kind_correct'], report['kind_total']), (2, 3))
        self.assertEqual((report['feature_correct'], report['feature_total']), (2, 3))
        self.assertEqual(report['feature_present_precision'], 0.5)
        self.assertEqual(report['feature_present_recall'], 1)
        self.assertEqual((report['element_correct'], report['element_total']), (2, 2))
        self.assertEqual(report['high_confidence_errors'], 2)
        self.assertEqual(report['decision_abstentions'], 3)
        self.assertIsNone(report['real_model_accuracy'])

    def test_no_positive_predictions_have_explicit_undefined_precision(self):
        report = evaluate_ai_decisions(self.cases, (AiOutcome('unavailable', 'No provider.'),) * 3,
                                       mode='offline_scripted')
        self.assertIsNone(report['feature_present_precision'])
        self.assertEqual(report['feature_present_recall'], 0)

    def test_duplicate_labels_and_misaligned_outputs_are_rejected(self):
        for cases, outcomes in ((self.cases * 2, self.outcomes * 2), (self.cases, self.outcomes[:1])):
            with self.assertRaises(ValueError):
                evaluate_ai_decisions(cases, outcomes, mode='offline_scripted')

    def test_low_confidence_wrong_kind_is_an_abstention_not_a_high_confidence_error(self):
        outcome = AiOutcome('accepted', 'Uncertain.', AiAdvice(WebsiteKind.COMMERCE, 0.1))
        report = evaluate_ai_decisions(self.cases[:1], (outcome,), mode='offline_scripted')
        self.assertEqual(report['high_confidence_errors'], 0)
        self.assertEqual(report['kind_confusion'], {'general:unknown': 1})
