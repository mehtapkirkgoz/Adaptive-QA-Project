"""Supervised read-only UI execution for one explicitly admitted owned run."""

from time import monotonic
from tempfile import TemporaryDirectory
from pathlib import Path

from adaptive_qa.browser_process import run_isolated_sample_test
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.smoke_checks import SMOKE_CHECKS
from adaptive_qa.worker_lock import worker_lock
from adaptive_qa.dashboard_evidence import import_screenshot
from adaptive_qa.execution_context import capture_execution_context


def process_run_once(queue):
    with worker_lock(queue.projects.database), TemporaryDirectory(prefix='adaptive-qa-owned-evidence-') as temporary:
        queue.prune_expired_evidence()
        work = queue.claim_next()
        if work is None:
            return None
        started = monotonic()
        catalog = {case.case_id: case for case in TEST_CASES}
        def stop():
            return (queue.cancellation_requested(work) or not queue.configuration_current(work)
                    or monotonic() - started >= 120)
        try:
            context = capture_execution_context()
            if work.configuration['base_url'] not in ('http://127.0.0.1:8000', 'http://127.0.0.1:8000/'):
                raise ValueError('Unsupported controlled target.')
            for case_id in work.case_ids:
                if queue.cancellation_requested(work):
                    break
                if stop():
                    raise ValueError('Run configuration or deadline changed.')
                definition = catalog.get(case_id)
                if definition is None or definition.changes_data or case_id not in SMOKE_CHECKS:
                    raise ValueError('Unsupported runtime case.')
                result = run_isolated_sample_test(case_id, timeout_seconds=min(30, 120 - (monotonic() - started)),
                    should_cancel=stop, site='root', evidence_directory=Path(temporary))
                if queue.cancellation_requested(work):
                    break
                if stop() or not isinstance(result, TestResult) or result.case_id != case_id or result.status == TestStatus.CANCELLED:
                    raise ValueError('Run interrupted or returned an invalid result.')
                evidence = import_screenshot(result.evidence_paths, root=Path(temporary))
                if not queue.record_result(work, result, evidence_png=evidence):
                    break
        except Exception:
            status = queue.finish(work, failed=True)
        else:
            if context is not None and capture_execution_context() == context:
                queue.record_execution_context(work, context)
            status = queue.finish(work)
        return {'run_id': work.run_id, 'project_id': work.project_id, 'status': status}
