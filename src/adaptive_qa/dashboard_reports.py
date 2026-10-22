"""Read-only reports built exclusively from owner-authorized persisted results."""

from adaptive_qa.catalog import TEST_CASES
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
        'catalog_total': len(TEST_CASES),
        'requested_total': len(run['case_ids']),
        'recorded_total': len(results),
        'unrecorded_total': len(run['case_ids']) - len(results),
        'status_counts': counts,
        'filter_status': status,
        'results': [dict(row) for row in results if status is None or row['status'] == status],
    }
