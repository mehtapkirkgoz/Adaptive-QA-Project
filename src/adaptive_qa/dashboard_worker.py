"""One owned discovery job per trusted operator invocation; no HTTP execution."""

import hashlib
import json

from adaptive_qa.api_catalog import API_CASES
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.crawler import CrawlBudget, CrawlResult
from adaptive_qa.database_catalog import DATABASE_CASES
from adaptive_qa.dashboard_plan import serialize_plan
from adaptive_qa.discovery import PageSnapshot, FormSnapshot, FieldSnapshot, LinkSnapshot, CommerceSnapshot
from adaptive_qa.local_discovery import discover_local_sample, discover_configured_target
from adaptive_qa.planning import build_test_plan
from adaptive_qa.worker_lock import worker_lock
from adaptive_qa.document_target import controlled_start_path
from adaptive_qa.discovery_target import configured_discovery, validate_discovery_url


def configuration_fingerprint(configuration):
    return hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _report(work, payload):
    # Raw snapshots and the child's own plan are never stored or trusted as final decisions.
    if not isinstance(payload, dict) or len(json.dumps(payload, allow_nan=False).encode()) > 2000000:
        raise ValueError('Invalid discovery payload.')
    pages, limitations = payload.get('pages'), payload.get('limitations')
    if not isinstance(pages, list) or not 1 <= len(pages) <= 5 or not isinstance(limitations, list):
        raise ValueError('Discovery has no usable bounded evidence.')
    if len(limitations) > 20 or any(not isinstance(reason, str) or len(reason) > 100 for reason in limitations):
        raise ValueError('Invalid discovery limitations.')
    profile, config = configured_discovery(work.configuration, project_id=work.project_id)
    snapshots = []
    for data in pages:
        validate_discovery_url(data['url'], config, profile)
        forms = tuple(FormSnapshot(**{**form,
            'fields': tuple(FieldSnapshot(**item) for item in form['fields']),
            'buttons': tuple(form['buttons'])}) for form in data['forms'])
        snapshots.append(PageSnapshot(data['url'], forms,
            tuple(LinkSnapshot(**item) for item in data['links']), data['collection_complete'],
            tuple(CommerceSnapshot(**{**item, 'actions': tuple(item['actions'])}) for item in data.get('commerce', []))))
    # Only generic limitation wording leaves the worker. Labels, URLs and evidence strings stay private.
    reasons = ('Discovery coverage is limited; inspected pages do not establish site-wide absence.',) if limitations else ()
    crawl = CrawlResult(tuple(snapshots), len(snapshots), reasons)
    definitions = TEST_CASES + tuple(case.definition for case in API_CASES) + tuple(case.definition for case in DATABASE_CASES)
    plan = build_test_plan(crawl, definitions, config)
    report = serialize_plan(plan, definitions, work.project_id, discovery_status='completed',
                            inspected_pages=len(snapshots), configuration_source='job_snapshot')
    report['configuration_fingerprint'] = configuration_fingerprint(work.configuration)
    report['discovery_profile'] = profile
    return report


def process_discovery_once(queue):
    """Hold the execution/recovery OS lock across claim, supervised child and commit."""
    with worker_lock(queue.projects.database):
        work = queue.claim_next()
        if work is None:
            return None
        try:
            # Recheck the trusted stored dispatch boundary before any process/target access.
            profile, config = configured_discovery(work.configuration, project_id=work.project_id)
            cancellation = lambda: queue.cancellation_requested(work)
            budget = CrawlBudget(max_pages=5, timeout_seconds=30)
            if profile == 'controlled_local':
                path = controlled_start_path(work.configuration)
                binding = {'start_path': path} if path != '/' else {}
                payload = discover_local_sample(budget, should_cancel=cancellation, **binding)
            else:
                payload = discover_configured_target(config, budget, profile=profile, should_cancel=cancellation)
            report = _report(work, payload)
        except Exception:
            status = queue.finish(work, failed=True)
        else:
            status = queue.finish(work, report=report)
        return {'job_id': work.job_id, 'project_id': work.project_id, 'status': status}
