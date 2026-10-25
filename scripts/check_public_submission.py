"""Emit safe CI evidence for the internal one-shot transport's owned TLS proof."""
import json
from pathlib import Path
import unittest


def main():
    root = Path(__file__).resolve().parents[1]
    suite = unittest.defaultTestLoader.discover(str(root/'tests'), pattern='test_public_submission.py')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful() or result.testsRun < 9 or result.skipped:
        raise SystemExit('Controlled public submission proof was incomplete.')
    report = dict(tests_run=result.testsRun, all_passed=True, target_scope='owned_loopback_tls_harness',
        connector_override='test_only', queue_or_ui_admission_enabled=False,
        public_customer_targets_contacted=False, raw_inputs_in_report=False,
        numeric_peer_pinning_and_verified_tls=True, one_shot_and_no_submission_retry=True,
        lost_response_retains_uncertain_delivery=True)
    path = root/'artifacts/processes/public-submission.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
