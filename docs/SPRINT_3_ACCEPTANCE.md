# Sprint 3 Acceptance Review

Review date: October 21, 2026 (Europe/Istanbul)
Status: Local acceptance passed; final implementation CI/artifact review pending.

Tracking: [issue #4](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/4)
and [milestone #4](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/4).

## Acceptance Evidence

| Requirement | Evidence | Local result |
| --- | --- | --- |
| Shared tests tolerate different control names | 32 shared definitions across English, Turkish, mapped fixtures | 96 isolated runs passed |
| Missing/ambiguous matches are controlled | 18 Chromium matching checks plus status invariants | Passed |
| Forty meaningful scenarios are implemented | Catalog/registry ID agreement, explicit outcomes, queue execution | 40 passed with JSON/PNG evidence |
| Data setup/cleanup is isolated | Fake immutable data, failure cleanup, storage/cookie/context checks | Passed |
| Order is independent | Full catalog repeated in reverse order, fresh processes | 40 reversed runs passed |
| Mutation policy is preserved | Data-changing definition blocked before browser preparation | Passed |
| Plans preserve required feature scope | Cross-form cases require their features on the same page | Passed |

## Reproduce

Run sequentially from the repository root with port 8000 available:

```powershell
python -m unittest discover -s tests -v
python scripts/check_element_matching.py
python scripts/check_reusable_ui.py
python scripts/check_ui_isolation.py
python scripts/check_local_browser.py
python scripts/check_page_collector.py
python scripts/check_local_discovery.py
python scripts/check_discovery_acceptance.py
python scripts/check_network_security.py
python scripts/check_process_lifecycle.py
```

The unit suite contains 268 tests. The forward queue, variants, and reverse-order
checks run the existing 40 definitions repeatedly; they do not create extra
catalog coverage. All thirty added behaviors have explicit expected outcomes.

## Remote Gate

- All four jobs must pass for the same implementation SHA.
- Confirm 268 unit tests in the job log.
- Download all three artifacts and verify their SHA-256 digests and commit SHA.
- Check 18 matching cases, 96 variant runs, cleanup/context separation, 40 reverse
  runs, 40 queued result JSON records and linked screenshots.
- Retain discovery, contrasting-fixture, nine egress, and both OS lifecycle checks.
- Inspect screenshot evidence before cleanup for an action scenario.

## Boundaries

This is a controlled local prototype. Eight original root-specific checks remain
root-only; 32 definitions have shared variant adapters. General customer targets,
AI matching, backend data setup/deletion, production isolation, and API/SQL
execution remain outside this sprint. Sample submits only alter DOM state.
Matched visibility is not actionability; executors assert actual outcomes.
Plans never dispatch or authorize execution automatically. No expected result
is weakened to accommodate a failed match or a fixture variation.

## Closure

- [x] Verify local acceptance and matching catalog/executor counts.
- [x] Record explicit scope and reproduction commands.
- [ ] Verify final same-commit CI and downloaded evidence.
- [ ] Update completion documents and close issue #4 after acceptance.
- [ ] Repository owner closes milestone #4.
