# Sprint 3 Acceptance Review

Review date: October 21, 2026 (Europe/Istanbul)
Status: Accepted. Final implementation CI and downloaded evidence verified.

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

## Verified Remote Evidence

Implementation: `eb95e96696d148133747ee4f290cb727f9fc4bb1`.
[CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39519899466)
passed all four jobs. The unit log confirms 268 tests. Both OS reports contain
three successful lifecycle checks. Browser reports confirm 18 matching checks,
96 variant runs, failure cleanup/context separation, 40 reversed runs, and 40
queued JSON results. All 176 referenced PNGs are present and valid. The reversed
case ID order matches the reverse of the forward queue order. Four discovery
fixture hashes/matrices, five budget scenarios, and nine egress checks also pass.
The combined login/search case is correctly blocked on separate discovered pages.

All three downloaded archive digests matched GitHub metadata and the same
implementation SHA. A FORM-005 screenshot was visually inspected: express delivery
remained selected, proving evidence was captured before cleanup. Downloads,
metadata, and inspection tooling are retained under ignored `artifacts/acceptance/`.
GitHub artifact retention is seven days; committed scripts/fixtures reproduce checks.

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
- [x] Verify final same-commit CI and downloaded evidence.
- [x] Update completion documents and close issue #4 after acceptance.
- [ ] Repository owner closes milestone #4.

Issue #4 is closed as completed. The connected tool cannot close milestones;
milestone #4 remains an owner action. Technical acceptance is complete.
