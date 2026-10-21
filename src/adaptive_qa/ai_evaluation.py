"""Aggregate labeled AI decisions; scripted evaluations must retain their mode."""

from dataclasses import dataclass

from adaptive_qa.ai_integration import _threshold
from adaptive_qa.ai_models import FEATURE_NAMES, WebsiteKind
from adaptive_qa.ai_runtime import AiOutcome
from adaptive_qa.models import FeatureStatus


@dataclass(frozen=True)
class AiEvaluationCase:
    case_id: str
    website_kind: WebsiteKind
    features: tuple[tuple[str, FeatureStatus], ...] = ()
    elements: tuple[tuple[str, str | None], ...] = ()

    def __post_init__(self):
        from adaptive_qa.ai_models import _identifier
        _identifier(self.case_id)
        if not isinstance(self.website_kind, WebsiteKind):
            raise ValueError('Ground-truth website kind must be typed.')
        if not isinstance(self.features, tuple) or len(self.features) > 7:
            raise ValueError('Ground-truth features must be a bounded tuple.')
        if not isinstance(self.elements, tuple) or len(self.elements) > 50:
            raise ValueError('Ground-truth elements must be a bounded tuple.')
        for values, feature in ((self.features, True), (self.elements, False)):
            names = []
            for pair in values:
                if not isinstance(pair, tuple) or len(pair) != 2:
                    raise ValueError('Ground-truth entries must be pairs.')
                name, expected = pair
                if not isinstance(name, str) or not name.strip() or len(name) > 80:
                    raise ValueError('Ground-truth names must be bounded text.')
                if feature:
                    if name not in FEATURE_NAMES or not isinstance(expected, FeatureStatus):
                        raise ValueError('Ground-truth features require supported names and typed states.')
                elif expected is not None:
                    _identifier(expected)
                names.append(name)
            if len(set(names)) != len(names):
                raise ValueError('Ground-truth names must be unique.')


def evaluate_ai_decisions(cases, outcomes, *, mode, threshold=0.85):
    """Report denominators, abstentions, confusion, and high-confidence errors.

    Labels must be independently prepared, not copied from provider predictions.
    This function never decides whether a live provider was actually invoked.
    """
    _threshold(threshold)
    if mode not in ('offline_scripted', 'live_model'):
        raise ValueError('Evaluation mode must be explicit.')
    if (not isinstance(cases, tuple) or not 1 <= len(cases) <= 1000
            or any(not isinstance(case, AiEvaluationCase) for case in cases)
            or len({case.case_id for case in cases}) != len(cases)
            or not isinstance(outcomes, tuple) or len(outcomes) != len(cases)
            or any(not isinstance(outcome, AiOutcome) for outcome in outcomes)):
        raise ValueError('Evaluation requires unique labeled cases and aligned typed outcomes.')
    kind_correct = feature_correct = element_correct = 0
    feature_total = element_total = abstentions = high_confidence_errors = 0
    true_positive = false_positive = false_negative = 0
    confusion = {}
    for case, outcome in zip(cases, outcomes):
        advice = outcome.advice if outcome.status == 'accepted' else None
        predicted_kind = advice.website_kind if advice is not None and advice.confidence >= threshold else WebsiteKind.UNKNOWN
        key = case.website_kind.value + ':' + predicted_kind.value
        confusion[key] = confusion.get(key, 0) + 1
        kind_correct += predicted_kind == case.website_kind
        abstentions += predicted_kind == WebsiteKind.UNKNOWN
        high_confidence_errors += (predicted_kind != case.website_kind and predicted_kind != WebsiteKind.UNKNOWN)
        features = {} if advice is None else {item.feature: item for item in advice.features}
        for name, expected in case.features:
            item = features.get(name)
            predicted = item.status if item is not None and item.confidence >= threshold else FeatureStatus.UNKNOWN
            feature_total += 1
            feature_correct += predicted == expected
            abstentions += predicted == FeatureStatus.UNKNOWN
            high_confidence_errors += predicted != expected and predicted != FeatureStatus.UNKNOWN
            true_positive += predicted == expected == FeatureStatus.PRESENT
            false_positive += predicted == FeatureStatus.PRESENT and expected != FeatureStatus.PRESENT
            false_negative += expected == FeatureStatus.PRESENT and predicted != FeatureStatus.PRESENT
        elements = {} if advice is None else {item.logical_name: item for item in advice.elements}
        for name, expected in case.elements:
            item = elements.get(name)
            predicted = item.candidate_id if item is not None and item.confidence >= threshold else None
            element_total += 1
            element_correct += predicted == expected
            abstentions += predicted is None
            high_confidence_errors += predicted != expected and predicted is not None

    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    return {'mode': mode, 'threshold': threshold, 'case_count': len(cases),
        'kind_correct': kind_correct, 'kind_total': len(cases), 'kind_confusion': confusion,
        'feature_correct': feature_correct, 'feature_total': feature_total,
        'feature_present_precision': ratio(true_positive, true_positive + false_positive),
        'feature_present_recall': ratio(true_positive, true_positive + false_negative),
        'element_correct': element_correct, 'element_total': element_total,
        'decision_abstentions': abstentions, 'high_confidence_errors': high_confidence_errors,
        'real_model_accuracy': ratio(kind_correct, len(cases)) if mode == 'live_model' else None}
