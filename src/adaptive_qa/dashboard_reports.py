"""Read-only reports built exclusively from owner-authorized persisted results."""

from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.api_catalog import API_CASES
from adaptive_qa.database_catalog import DATABASE_CASES
from adaptive_qa.models import TestStatus


def build_run_report(runs, actor, project_id, run_id, *, status=None):
    """Filtering changes visible rows, never totals or execution outcomes."""
    run = runs.get(actor, project_id, run_id)
    if status is not None and (
        not isinstance(status, str) or status not in {item.value for item in TestStatus}
    ):
        raise ValueError('Unknown test result status.')
    results = run['results']
    counts = {item.value: 0 for item in TestStatus}
    for result in results:
        counts[result['status']] += 1
    return {
        'schema_version': 1,
        'run_id': run['run_id'],
        'project_id': run['project_id'],
        'run_status': run['status'],
        'rerun_of': run['rerun_of'],
        'catalog_total': len(TEST_CASES) + len(API_CASES) + len(DATABASE_CASES),
        'requested_total': len(run['case_ids']),
        'recorded_total': len(results),
        'unrecorded_total': len(run['case_ids']) - len(results),
        'status_counts': counts,
        'filter_status': status,
        'results': [dict(row) for row in results if status is None or row['status'] == status],
    }


def compare_runs(runs, actor, project_id, baseline_id, current_id):
    """Describe recorded outcome changes; never infer flaky tests or performance."""
    baseline = runs.get(actor, project_id, baseline_id)
    current = runs.get(actor, project_id, current_id)
    if baseline_id == current_id or any(run['status'] not in ('completed', 'cancelled', 'error')
                                         for run in (baseline, current)):
        raise ValueError('Select two different finalized runs.')
    before = runs.comparison_context(actor, project_id, baseline_id)
    after = runs.comparison_context(actor, project_id, current_id)
    common = set(baseline['case_ids']) & set(current['case_ids'])
    comparable = bool(common and before['configuration'] == after['configuration']
        and before['contracts'] and after['contracts']
        and all(before['contracts'].get(case) == after['contracts'].get(case)
                and before['contracts'].get(case) for case in common))
    previous = {item['case_id']: item['status'] for item in baseline['results']}
    latest = {item['case_id']: item['status'] for item in current['results']}
    rows = []
    if comparable:
        for case_id in dict.fromkeys(baseline['case_ids'] + current['case_ids']):
            old, new = previous.get(case_id), latest.get(case_id)
            change = ('added' if case_id not in baseline['case_ids'] else
                      'removed' if case_id not in current['case_ids'] else
                      'unrecorded' if old is None or new is None else
                      'unchanged' if old == new else 'changed')
            rows.append({'case_id': case_id, 'baseline_status': old,
                         'current_status': new, 'change': change})
    return {'baseline_run_id': baseline_id, 'current_run_id': current_id,
            'comparable': comparable, 'results': rows,
            'reason': ('Matching saved policy and test definitions; fixture state may differ. '
                       'Outcome changes alone do not establish flakiness.' if comparable else
                       'Common cases with matching recorded policy and definition contracts are required.')}
