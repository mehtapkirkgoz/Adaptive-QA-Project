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
- [ ] 8.2: Expose authenticated reports and exports, with dashboard filtering.
- [ ] 8.3: Add explicit rerun admission and comparable historical results.
- [ ] 8.4: Record flaky-test signals with context and sufficient observations.
- [ ] 8.5: Enforce evidence retention and access rules.
- [ ] 8.6: Expand to at least 100 meaningful, implemented and fixture-verified cases.
- [ ] 8.7: Verify integrated acceptance and exact-commit CI evidence.

## Reporting contract

The first increment is a Python service projection; no report HTTP endpoint or
dashboard report UI is delivered yet. Authorization uses the existing owned
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
