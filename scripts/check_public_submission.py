"""Emit safe CI evidence for the internal one-shot transport's owned TLS proof."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


def main():
    root = Path(__file__).resolve().parents[1]
    installed = os.environ.get('ADAPTIVE_QA_VERIFY_SITE')
    if installed:
        site = Path(installed).resolve(strict=True)
        sys.path.insert(0, str(site))
        import adaptive_qa
        if not Path(adaptive_qa.__file__).resolve().is_relative_to(site):
            raise SystemExit('Parent must use the installed package.')
        child = subprocess.check_output([sys.executable, '-c',
            'import adaptive_qa; print(adaptive_qa.__file__)'], text=True).strip()
        if not Path(child).resolve().is_relative_to(site):
            raise SystemExit('Supervised children must use the installed package.')
    suite = unittest.defaultTestLoader.discover(str(root/'tests'), pattern='test_public_submission*.py')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful() or result.testsRun < 20 or result.skipped:
        raise SystemExit('Controlled public submission proof was incomplete.')
    report = dict(tests_run=result.testsRun, all_passed=True, target_scope='owned_loopback_tls_harness',
        connector_override='test_only', queue_or_ui_admission_enabled=False,
        public_customer_targets_contacted=False, raw_inputs_in_report=False,
        numeric_peer_pinning_and_verified_tls=True, one_shot_and_no_submission_retry=True,
        lost_response_retains_uncertain_delivery=True, hard_child_deadlines_and_cancellation=True,
        exact_owner_project_references=True, values_resolved_only_in_child=True,
        browser_completion_or_catalog_pass_claimed=False, installed_wheel=bool(installed),
        supervised_child_package_verified=bool(installed))
    path = Path('artifacts/processes/public-submission.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
