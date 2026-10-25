"""Evidence aggregation and non-executing, page-scoped test planning."""

from dataclasses import dataclass, field
from enum import StrEnum

from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlResult
from adaptive_qa.discovery import FeatureFinding, PageSnapshot, detect_page_features
from adaptive_qa.models import FeatureStatus, TestCase, TestType
from adaptive_qa.native_form_checks import NATIVE_FORM_CHECKS, has_unique_email


FEATURES = ('login', 'search', 'registration', 'product', 'cart', 'forms', 'navigation')


class PlanDecision(StrEnum):
    SELECTED = 'selected'
    SKIPPED = 'skipped'
    BLOCKED = 'blocked'


@dataclass(frozen=True)
class FeatureSummary:
    feature: str
    status: FeatureStatus
    reason: str
    page_urls: tuple[str, ...]
    scope: str = field(default='inspected_pages', init=False)


@dataclass(frozen=True)
class DiscoveryAssessment:
    features: tuple[FeatureSummary, ...]
    page_findings: tuple[FeatureFinding, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class PlannedCase:
    case_id: str
    decision: PlanDecision
    reason: str
    target_url: str | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class TestPlan:
    assessment: DiscoveryAssessment
    cases: tuple[PlannedCase, ...]
    scope: str = field(default='inspected_pages', init=False)
    execution_authorized: bool = field(default=False, init=False)


def assess_discovery(crawl: CrawlResult, *, action_names=None) -> DiscoveryAssessment:
    """Positive evidence wins; limited or uncertain coverage cannot prove absence."""
    if (not isinstance(crawl, CrawlResult) or not isinstance(crawl.pages, tuple)
            or any(not isinstance(page, PageSnapshot) for page in crawl.pages)
            or not isinstance(crawl.limitations, tuple)
            or any(not isinstance(reason, str) or not reason.strip() for reason in crawl.limitations)):
        raise ValueError('crawl must contain typed pages and limitation reasons.')
    if len({page.url for page in crawl.pages}) != len(crawl.pages):
        raise ValueError('Discovery page URLs must be unique.')
    findings = tuple(finding for page in crawl.pages for finding in detect_page_features(page, action_names=action_names))
    features = []
    for feature in FEATURES:
        relevant = tuple(item for item in findings if item.feature == feature)
        present = tuple(item for item in relevant if item.status == FeatureStatus.PRESENT)
        if present:
            status = FeatureStatus.PRESENT
            reason = 'Positive structural evidence was found on the referenced inspected pages.'
            urls = tuple(dict.fromkeys(item.page_url for item in present))
        elif (relevant and not crawl.limitations and all(page.collection_complete for page in crawl.pages)
              and all(item.status == FeatureStatus.ABSENT for item in relevant)):
            status = FeatureStatus.ABSENT
            reason = 'No matching evidence on inspected pages; this does not establish site-wide absence.'
            urls = tuple(dict.fromkeys(item.page_url for item in relevant))
        else:
            status = FeatureStatus.UNKNOWN
            reason = 'Evidence or coverage is incomplete; feature absence cannot be established.'
            urls = tuple(dict.fromkeys(item.page_url for item in relevant))
        features.append(FeatureSummary(feature, status, reason, urls))
    return DiscoveryAssessment(tuple(features), findings, crawl.limitations)


def build_test_plan(crawl: CrawlResult, cases: tuple[TestCase, ...],
                    project: ProjectConfig, *, action_names=None) -> TestPlan:
    """Select applicable UI definitions, without executing or approving them.

    Selected definitions still require a compatible executor and runtime policy
    checks. Multi-page workflows require a future explicit binding contract.
    """
    if (not isinstance(cases, tuple) or any(not isinstance(case, TestCase) for case in cases)
            or len({case.case_id for case in cases}) != len(cases)):
        raise ValueError('cases must be a tuple of uniquely identified TestCase instances.')
    if not isinstance(project, ProjectConfig):
        raise ValueError('project must be a ProjectConfig.')
    assessment = assess_discovery(crawl, action_names=action_names)
    if any(not project.is_url_allowed(page.url) for page in crawl.pages):
        raise ValueError('Discovery contains a page outside the project hostname allowlist.')
    statuses = {feature.feature: feature.status for feature in assessment.features}
    evidence_by_page: dict[str, dict[str, FeatureFinding]] = {}
    for finding in assessment.page_findings:
        evidence_by_page.setdefault(finding.page_url, {})[finding.feature] = finding
    entries = []
    for case in cases:
        if case.changes_data and not project.allow_data_changes:
            entries.append(PlannedCase(case.case_id, PlanDecision.BLOCKED,
                                       'Project policy disables data-changing tests.'))
            continue
        if case.test_type != TestType.UI:
            entries.append(PlannedCase(case.case_id, PlanDecision.BLOCKED,
                                       'API and database planning require adapter and configuration contracts.'))
            continue
        absent = tuple(name for name in case.required_features if statuses.get(name) == FeatureStatus.ABSENT)
        uncertain = tuple(name for name in case.required_features
                          if statuses.get(name, FeatureStatus.UNKNOWN) == FeatureStatus.UNKNOWN)
        if absent:
            entries.append(PlannedCase(case.case_id, PlanDecision.SKIPPED,
                'No matching evidence on inspected pages for: ' + ', '.join(absent) +
                '. Uninspected routes are outside this plan.'))
        elif uncertain:
            entries.append(PlannedCase(case.case_id, PlanDecision.BLOCKED,
                'Uncertain or unsupported feature prerequisites: ' + ', '.join(uncertain) + '.'))
        else:
            candidates = [(url, findings) for url, findings in evidence_by_page.items()
                          if all(name in findings and findings[name].status == FeatureStatus.PRESENT
                                 for name in case.required_features)]
            if case.case_id in NATIVE_FORM_CHECKS:
                email_urls = {page.url for page in crawl.pages if has_unique_email(page)}
                candidates = [(url, findings) for url, findings in candidates if url in email_urls]
            if not candidates:
                entries.append(PlannedCase(case.case_id, PlanDecision.BLOCKED,
                    'No inspected page satisfies all prerequisites; a multi-page binding is required.'))
                continue
            url, findings = candidates[0]
            evidence = tuple(f'{name}: {reference}' for name in case.required_features
                             for reference in findings[name].evidence)
            if not case.required_features:
                evidence = ('page: inspected document snapshot',)
            entries.append(PlannedCase(case.case_id, PlanDecision.SELECTED,
                'Applicable on the referenced page. A compatible executor and runtime checks are still required.',
                url, evidence))
    return TestPlan(assessment, tuple(entries))
