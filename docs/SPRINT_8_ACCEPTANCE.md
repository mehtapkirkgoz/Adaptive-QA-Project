# Sprint 8 Acceptance — Reporting and Test Catalog Expansion

Status: Technical acceptance complete; ready for owner review and closure.
Date: 2026-10-22
Tracking issue: [#9](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/9)
Milestone: [#9](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/9)

Implementation: `d72d2f564b332058b66de4941222f459f1a0a671`.
CI: [run 39752481207](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39752481207).
The implementation commit is frozen for evidence review. Acceptance documentation
will be a separate commit; documentation does not substitute for implementation CI.

## Delivered Behavior

| Criterion | Implementation and verification |
|---|---|
| Filterable results and screenshots | Owned status-filtered reports; totals remain complete; guarded PNG links; actual Chromium flow |
| Export | Fixed-name no-store JSON attachment agrees with the two actual dashboard outcomes |
| Explicit reruns | Selected parent-case subset becomes a new queued run; current discovery/policy/quota rechecked; no HTTP execution |
| Historical comparison | Two finalized owned runs require matching saved policy/definition contracts; missing outcomes remain unrecorded |
| Consistency signals | Latest 20 owned runs; strict context groups, five observations, two passes/failures and transitions; advisory only |
| 100 scenarios | 51 UI, 34 API and 15 database definitions, with real controlled adapter checks |
| Applicability | Inspected features, explicit contracts and runtime bindings; absence/uncertainty remain distinct; catalog/requested/recorded counts separate |
| Evidence policy | Seven-day owned PNG expiry, immediate access denial, bounded indexed cleanup and temporary worker screenshots |
| Expansion plan | CATALOG_ROADMAP.md prioritizes pilot-driven gaps toward 200; planned capacity is not counted as executors |

The full definitions are in [the frozen catalog](evidence/sprint8-catalog.json).
The document/semantic additions have three contrasting offline HTML fixtures,
33 positive checks and eleven deliberately broken examples. Fixture variations
do not add scenario IDs. The API additions cover listing/account/commerce
contracts with explicit expected values and do not infer customer endpoints.

## Result Integrity and Ownership

Run lifecycle is separate from assertions: completed can include failed tests.
Queued/cancelled but unattempted cases have no invented pass/skip result. Status
filters do not change aggregate counts. Original outcomes survive reruns, expiry
and cleanup. Comparison does not diagnose flakiness or performance by itself.

Anonymous access is denied and another owner's resources remain indistinguishable
from missing records. Origin/CSRF checks protect mutations. Reports omit raw
adapter messages, private paths, credentials, request payloads and response bodies.
Only opaque owned evidence IDs are exposed before expiry. No public purge API,
automatic retry, AI outcome rewriting or non-executing-plan escalation was added.

## Verified Evidence

All seven CI jobs passed on the exact implementation SHA above. The scaffold
log confirms 534 unit tests. Six downloaded archive SHA-256 digests and artifact
head SHAs match the same commit. The safe permanent record is
[the acceptance manifest](evidence/sprint8-acceptance.json).

- 51 queued UI scenarios passed with matching persisted results and PNGs; all
  51 also passed in reverse order. The 96 existing mapping/language checks remain
  variations of existing IDs, not additional scenarios.
- Eleven document/semantic cases passed 33 contrasting offline checks and
  detected eleven deliberately broken fixtures, with zero external requests.
- All 34 API cases and 20 API policy/redaction/deadline boundaries passed;
  forbidden canaries received zero contacts.
- Both Linux and Windows verified all 15 database cases, 19 database boundaries
  and reverse-order results without changing the protected fixtures. Each also
  passed three real process-lifecycle checks.
- All 28 real dashboard checks passed, including JSON download, filtered totals,
  explicit subset rerun/cancel/lineage, historical comparison, insufficient-history
  information and decoded authorized PNG delivery. Anonymous/other-owner evidence
  access was denied. No dashboard script errors or external requests occurred.
- All 202 retained PNGs passed structural/CRC validation; 200 distinct referenced
  filesystem PNGs were present and validated. The same-commit mobile workspace
  screenshot was visually inspected. Owned database PNGs are not archived; the
  live CI test decoded them before temporary database cleanup.
- Nine browser egress checks, bounded/contrasting discovery, cross-layer fixture
  bridges and the existing free/offline AI controls remained green. No live cloud
  model, customer target or deployment was used.

## Practical Limits

- The networked prototype remains bound to the controlled local fixture. No
  customer site, production deployment or paid/cloud model was used.
- The dashboard admits selected read-only UI tests only. API/database adapters
  require explicit separate contracts; UI discovery does not authorize them.
- Comparisons are descriptive and qualified by recorded metadata. Fixture state
  and timing may differ. Legacy missing contracts/context do not become evidence.
- Consistency signals are investigation cues, not proof of nondeterminism. The
  positive signal threshold is tested with controlled stored observations; the
  real UI flow confirms insufficient history without an invented flaky verdict.
- Screenshot expiry is enforced on access even before cleanup. Worker calls
  clean one bounded batch; inactive installations need the operator command.
  Results and run metadata have no automatic deletion policy in this sprint.
- Normal success/error/cancellation cleans temporary worker PNGs. Abrupt host
  shutdown or an uncatchable worker kill can leave private OS-temp files for
  operator cleanup. Backups, development CLI artifacts and forensic erasure are
  separately controlled; hosted operations remain future scope.
- GitHub evidence expires after seven days. The retained verification manifest
  records IDs/digests and the frozen implementation, not an indefinite backup of
  screenshots or temporary databases.

The owner manages issue/milestone closure and the next sprint start. Issue #9
and milestone #9 remain open for owner review. Do not continue Sprint 8
development, close it automatically or start Sprint 9 without the owner's
explicit instruction. The scheduled follow-up remains quiet while waiting.
