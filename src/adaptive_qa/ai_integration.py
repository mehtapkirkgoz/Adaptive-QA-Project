"""Advisory AI overlay and host-owned locator fallback; never grant execution."""

from dataclasses import dataclass, field
import math

from adaptive_qa.ai_models import WebsiteKind
from adaptive_qa.ai_runtime import AiOutcome
from adaptive_qa.ai_validation import ReducedAiInput
from adaptive_qa.element_matching import match_element
from adaptive_qa.element_models import ElementMapping, MatchStatus
from adaptive_qa.models import FeatureStatus
from adaptive_qa.planning import PlanDecision, TestPlan


def _threshold(value):
    if type(value) not in (int, float) or not 0.5 <= value <= 1 or not math.isfinite(value):
        raise ValueError('AI confidence threshold must be finite and in [0.5, 1].')


@dataclass(frozen=True)
class AiPlanReview:
    plan: TestPlan
    website_kind: WebsiteKind
    supported_features: tuple[str, ...]
    prioritized_case_ids: tuple[str, ...]
    execution_authorized: bool = field(default=False, init=False)


def review_plan_with_ai(plan, cases, outcome, *, threshold=0.85):
    """Prioritize already-selected cases only; retain the exact original plan."""
    _threshold(threshold)
    if not isinstance(plan, TestPlan) or not isinstance(outcome, AiOutcome):
        raise ValueError('Typed plan and AI outcome are required.')
    from adaptive_qa.models import TestCase
    if (not isinstance(cases, tuple) or any(not isinstance(case, TestCase) for case in cases)
            or tuple(case.case_id for case in cases) != tuple(item.case_id for item in plan.cases)):
        raise ValueError('Case definitions must match the original plan identities and order.')
    advice = outcome.advice if outcome.status == 'accepted' else None
    kind = WebsiteKind.UNKNOWN
    features = ()
    prioritized = ()
    if advice is not None:
        if advice.confidence >= threshold:
            kind = advice.website_kind
        known = {feature.feature for feature in plan.assessment.features if feature.status == FeatureStatus.PRESENT}
        features = tuple(item.feature for item in advice.features
            if item.status == FeatureStatus.PRESENT and item.confidence >= threshold and item.feature in known)
        prioritized = tuple(case.case_id for case, entry in zip(cases, plan.cases)
            if entry.decision == PlanDecision.SELECTED and case.required_features
            and set(case.required_features) <= set(features))
    return AiPlanReview(plan, kind, features, prioritized)


@dataclass(frozen=True)
class AiElementCandidate:
    candidate_id: str
    mapping: ElementMapping

    def __post_init__(self):
        from adaptive_qa.ai_models import _identifier
        _identifier(self.candidate_id)
        if not isinstance(self.mapping, ElementMapping):
            raise ValueError('Candidate binding requires a host-owned ElementMapping.')


def match_with_ai_fallback(page, default, outcome, reduced, candidates, *, threshold=0.85,
                            explicit_project_mapping=False):
    """AI can reference a host mapping only after a deterministic missing result.

    Never narrow an ambiguous match or override explicit project configuration.
    The result is a static handle; callers still own policy, action and deadline.
    """
    _threshold(threshold)
    if (not isinstance(default, ElementMapping) or not isinstance(outcome, AiOutcome)
            or not isinstance(reduced, ReducedAiInput) or type(explicit_project_mapping) is not bool
            or not isinstance(candidates, tuple) or len(candidates) > 200
            or any(not isinstance(item, AiElementCandidate) for item in candidates)):
        raise ValueError('Typed host mappings, AI outcome and reduced input are required.')
    original = match_element(page, default)
    if original.result.status != MatchStatus.MISSING or explicit_project_mapping:
        return original
    if not reduced.collection_complete:
        return original
    advice = outcome.advice if outcome.status == 'accepted' else None
    feature_name = default.logical_name.split('.')[0]
    feature_name = {'form': 'forms', 'nav': 'navigation'}.get(feature_name, feature_name)
    supported = () if advice is None else tuple(item for item in advice.features
        if item.feature == feature_name and item.status == FeatureStatus.PRESENT
        and item.confidence >= threshold)
    if len(supported) != 1:
        return original
    suggestions = () if advice is None else tuple(item for item in advice.elements
        if item.logical_name == default.logical_name and item.confidence >= threshold
        and item.candidate_id in reduced.candidate_ids)
    if len(suggestions) != 1:
        return original
    # A high-confidence feature from another form cannot justify this candidate.
    import json
    structure = json.loads(reduced.payload)['untrusted_page_data']
    owner_forms = tuple(form['id'] for form in structure['forms']
        if any(item['id'] == suggestions[0].candidate_id for item in form['fields'] + form['buttons']))
    if len(owner_forms) != 1 or owner_forms[0] not in supported[0].evidence_ids:
        return original
    bindings = tuple(item for item in candidates if item.candidate_id == suggestions[0].candidate_id
                     and item.mapping.logical_name == default.logical_name)
    if len(bindings) != 1:
        return original
    original.close()
    return match_element(page, bindings[0].mapping)
