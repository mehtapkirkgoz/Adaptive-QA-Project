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
- [ ] 8.3: Add explicit rerun admission and comparable historical results.
- [ ] 8.4: Record flaky-test signals with context and sufficient observations.
- [ ] 8.5: Enforce evidence retention and access rules.
- [ ] 8.6: Expand to at least 100 meaningful, implemented and fixture-verified cases.
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
