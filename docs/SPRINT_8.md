# Sprint 8 — Reporting and Test Catalog Expansion

Started: 2026-10-22
Status: In progress; explicitly started by the owner.
Tracking: [issue #9](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/9)
Milestone: [#9](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/9)

Sprint 7 issue #8 and its milestone #8 are confirmed closed. The latest
pre-start CI run 39743359671 passed on e7ac30da9bfed7990fc6c8c6fc39cf4a601e2dcf.

## Delivery steps

- [x] 8.1: Add a read-only owned report projection with result-status filtering,
  unchanged aggregate counts and explicit unrecorded counts.
- [x] 8.2: Expose authenticated JSON reports/exports, with dashboard status filtering.
- [x] 8.3: Add explicit rerun admission and qualified historical results in the API/dashboard.
- [x] 8.4: Record conservative advisory signals with context and sufficient observations.
- [x] 8.5: Enforce owned screenshot expiry and bounded cleanup, preserving assertion history.
- [x] 8.6: Define 100 implemented scenarios and verify them in suitable controlled fixtures.
- [ ] 8.7: Verify integrated acceptance and exact-commit CI evidence.

## Reporting contract

The projection is exposed through authenticated report and JSON download endpoints
and the dashboard's Review report section. Authorization uses the existing owned
run lookup. Reports never enqueue work or re-run assertions. The lifecycle state
is separate from assertion outcomes: a completed run may contain failed tests.
Filtering changes visible rows only. Aggregate counts cover all persisted
results. Requested cases without persisted results remain unrecorded, including
unattempted cases in cancelled runs; they are not fabricated as skipped/passed.
Catalog size is reported separately from requested and recorded counts. This
increment does not claim to measure feature applicability from the run alone.
Messages remain the existing reduced persisted messages, without raw adapter
text, configuration, tokens or filesystem paths.

All 504 unit tests passed locally after this increment. Four focused tests cover filtering fidelity, cancelled/queued non-results,
ownership boundaries and invalid filters. The catalog remains 75 definitions.
Future expansion must add distinct assertions and suitable controlled fixtures,
without cosmetic duplicates or exposing unimplemented executors.

Owner review and closure remain required after technical acceptance. Sprint 9,
deployment, paid services and customer-site execution are not authorized.

## Dashboard report delivery

Report/status/download paths enforce the existing owner session and exact run
binding; query overrides remain rejected. JSON downloads use a fixed attachment
filename and no-store headers, without image bytes or raw adapter messages.
The dashboard loads reports on demand, clears stale rows during filter changes,
and refreshes open reports as run progress changes. Empty filtered views retain
the complete status counts. Screenshot links use the existing guarded endpoint.

Validation: all 506 unit tests passed (including 22 project/API tests), strict TypeScript/Vite build passed,
and the real Chromium dashboard check passed including status filtering and a
downloaded JSON file matching two actual passed outcomes. Mobile width and
authorized screenshot delivery remain covered. Historical comparisons, reruns,
retention and further catalog expansion are still pending.

## Cross-site catalog increment

Added five read-only document rules (DOC-001–005): title, language declaration,
unique IDs, ARIA references and local fragment targets. These do not require
login, commerce or fixed button labels. No discovery still blocks planning.
The full catalog is now 80 definitions (45 UI / 20 API / 15 database).
Fifteen positive checks across three contrasting offline HTML fixtures passed;
all five deliberate defects were detected. CI now runs this verification and
retains its reduced report in the matching evidence archive. See UI_CATALOG.md
for limits and further expansion areas. The goal of 100 verified distinct cases
is not reached and step 8.6 remains unfinished.

The complete local queued browser suite passed all 45 UI scenarios with matching
persisted results and PNG evidence after this addition. The built dashboard
browser verification also passed with the updated 80-case report/plan totals.
All 508 unit tests passed. CI for this increment must still be verified before
technical acceptance; these local checks do not close the sprint.

## Semantic coverage and feature suitability

Added six distinct read-only rules: accessible button/field/link names, explicit
label associations, viewport zoom policy and absence of automatic meta refresh.
The catalog now has 86 cases (51 UI / 20 API / 15 database). Field/label checks
require forms and link checks require navigation. Focused tests verify absent
versus uncertain prerequisites, non-execution without discovery and bounded
element inspection. The document/semantic offline suite now checks eleven IDs
across three site types and rejects eleven deliberately broken examples.

Previous CI run 39748038963 on b6d2a14 failed in check_dashboard_worker.py because
its selected/catalog assertions still assumed 40/75 definitions. The worker
verification now derives those bounds from the registered catalogs. Other six
jobs passed; report delivery commit 5c58b96 passed run 39747234056. Current
increment CI remains pending and Sprint 8 is not accepted yet.

Local verification passed all 512 unit tests, all 51 queued UI cases with
persisted JSON/PNG evidence, the eleven-case offline positive/negative suite,
and the corrected separate discovery worker CLI. These are platform unit tests,
website scenarios and fixture checks respectively; they are separate counts.

## Generic-rule discovery evidence correction

Run 39748798411 failed at the bounded-discovery check: newly selected generic
document rules had no feature-specific evidence. Their plans now record the
actual inspected document snapshot as evidence, without claiming the assertion
passed. The real discovery check resolves expected page bindings from feature
prerequisites and permits generic document inspection under a page limit while
keeping unknown feature-dependent cases blocked. Plans still never execute tests.

## Reruns and historical comparisons

Finalized owned runs can request a new queued run with an explicit subset of
their original case IDs and current owned discovery ID. Admission repeats current
configuration, selection, data-change, local-target and quota checks in the same
transaction. Original outcomes are immutable. No automatic retry or execution
occurs in HTTP; the worker remains separate. The dashboard requires checkbox
selection before enabling a rerun and displays its parent lineage.

New runs retain hashes of their test definition contracts. Comparison requires
two distinct finalized owned runs, common IDs, matching saved target policy and
matching definition contracts. Older runs without contract metadata and changed
policies/contracts are explicitly incomparable. Outcomes may be unchanged,
changed, added, removed or unrecorded. Missing results are never successful.
Fixture state may differ between runs: changes alone do not prove flakiness or
performance regressions. Flaky tracking and retention remain unfinished.

Validation: all 519 unit tests passed, strict TypeScript/Vite build passed and
the real Chromium dashboard flow verified explicit subset rerun admission,
cancelled-child lineage and a historical comparison without invented outcomes.
The mobile report/comparison screenshot was inspected. Same-commit CI remains
required before sprint acceptance.

## Owned evidence retention

New owned screenshots expire seven days after result commit. Expired IDs return
the same 404 as missing evidence, even before cleanup. Public run/report projections
remove expired links and indicate expiry without changing actual assertion outcomes.
Legacy evidence without a known expiry is unavailable; no creation time is invented.
The schema migration preserves results and old BLOBs until bounded cleanup.

`dashboard prune-evidence --database <projects.sqlite> --limit 100` is a trusted
operator command, not a web endpoint. It deletes at most 1,000 expired/unknown-age
BLOBs per call (default 100), using an indexed expiry order. Each owned worker
invocation also performs one default cleanup batch. Inactive installations need
the operator command; there is no hosted scheduler yet. These deletions remove
live database records, not forensic copies in backups or storage snapshots.

The owned worker uses its own temporary evidence directory, imports validated
PNG bytes into the owned database and cleans the temporary directory on success,
failure or cancellation after child termination. Legacy standalone CLI artifacts
remain operator-local development evidence and are not exposed by the dashboard;
their separate retention is an operator responsibility. GitHub evidence still
uses seven-day artifact retention. No customer/deployed storage is enabled.

Validation: all 526 unit tests passed, including expiry, bounded/idempotent
cleanup, unknown-age migration behavior and temporary-directory cleanup on
success/failure. The real dashboard rerun/report/screenshot flow and strict
TypeScript/Vite build passed with temporary owned PNG capture. The expiry index
change was rechecked with all six focused retention tests. CI remains pending.

## Consistency observations

The owned worker captures bounded SHA-256 fingerprints of the local fixture and
relevant executor/guard sources, Python patch version, platform and Playwright
package version before/after execution. Only an unchanged known context is
stored. Missing/oversized sources remain unknown; old runs are not backfilled.

GET `/api/projects/{project_id}/flaky-signals` and the dashboard's Review
consistency view inspect at most the latest 20 owned runs. Only completed runs
with known context/definition contracts and passed/failed assertions contribute.
Groups require matching saved policy, case definition and execution context.
At least five observations, at least two passes and two failures, and two outcome
transitions are required for a potential-flakiness advisory. A single sustained
regression/recovery, insufficient history and cross-context differences do not
establish that signal. No assertion status, confidence threshold, retry count or
authorization is modified. Timing and external state may still differ; this is
an investigation cue, not a proven nondeterminism diagnosis.

Focused tests cover observation thresholds, context separation, excluded legacy
runs, execution errors, ownership and bounded context capture. The real browser
flow confirms that two actual outcomes produce insufficient-history information
without an invented flaky verdict. The hourly follow-up now records Sprint 8 and
the owner's instruction to notify after each commit and continue without waiting.

All 532 unit tests, the strict frontend build and the real dashboard browser
workflow passed after this increment. Same-commit CI is still required.

## One hundred meaningful scenarios

Added API-021–034: pagination/cursor and invalid pagination; numeric sorting;
taxonomy identifiers and category filtering; available/unavailable stock;
empty-cart checkout restriction, line/subtotal arithmetic and discount totals;
regional shipping/unsupported regions; field-specific validation; and a protected
profile preserving null/false fields. These are fourteen distinct explicit
contracts, not language/label/fixture variants. They require configured API
endpoints and expected values and cannot be inferred from UI feature detection.

All 34 isolated API cases passed against the controlled stateless API. Combined
with 51 verified UI scenarios and 15 verified database cases, the catalog has
100 definitions. The dashboard remains UI-only and discovery plans still block
unconfigured API/database cases. This milestone in scenario count is not sprint
acceptance; exact-commit CI and evidence must still confirm the integrated build.

All 534 unit tests passed after the expansion. The follow-on plan toward 200 is
in CATALOG_ROADMAP.md, with pilot-driven priorities and executor/negative-fixture
admission requirements. Planned capacity is not counted as implemented coverage.
