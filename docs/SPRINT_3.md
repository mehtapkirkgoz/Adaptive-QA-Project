# Sprint 3 — UI Test Catalog and Element Matching

Start date: October 21, 2026 (Europe/Istanbul)
Status: In progress — planning and tracking initialized.
Tracking issue: [#4](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/4).
Milestone: Pending creation and association by the repository owner.

## Goal

Run reusable UI scenarios across controlled applications with different control
names, using deterministic matching and explicit project mappings. Expand toward
approximately 40 meaningful runnable scenarios without inflating counts through
cosmetic variants or unimplemented definitions.

## Phases

- [ ] 3.1: Define validated element mapping and matching result contracts.
- [ ] 3.2: Implement role/label/alternative-name matching with controlled missing and ambiguous outcomes.
- [ ] 3.3: Bind reusable executors to discovered pages and contrasting fixture variants.
- [ ] 3.4: Expand login, form, search, navigation, and negative UI coverage toward 40 runnable scenarios.
- [ ] 3.5: Add isolated test data preparation/cleanup and data-change policy enforcement.
- [ ] 3.6: Verify independent/repeated execution, remote CI, artifacts, and acceptance.

## Matching Contract Goals

Mappings identify a logical control through allowed roles, accessible labels/names,
and explicit project overrides. Matching must report a unique supported candidate,
missing evidence, or ambiguity. It must not silently choose the first ambiguous
control, weaken expected results, or treat page text as instructions.

The first implementation remains deterministic; AI support belongs to Sprint 6.
Every executor must retain destination authorization and operation/total deadlines.
Selected plans remain non-executing until a compatible executor and runtime checks
are applied. Multi-page workflows require explicit bindings.

## Acceptance Criteria

- [ ] Shared tests work against controlled pages with different element names.
- [ ] Missing and ambiguous controls produce explicit controlled outcomes.
- [ ] Cases are independent of execution order and isolate their test data.
- [ ] Data-changing actions respect project policy and include cleanup behavior.
- [ ] Repeated runs produce explainable results and evidence.
- [ ] Catalog counts reflect implemented runnable coverage.
- [ ] CI and downloaded evidence are verified for the accepted implementation commit.

## Scheduled Continuation

The existing hourly follow-up is active for Sprint 3 in this chat. It checks usage
availability before continuing the next unfinished phase, preserves user changes,
and commits/pushes small verified increments. It stops after Sprint 3 acceptance;
Sprint 4, deployment, and customer-site execution are outside its scope.

## Baseline

Sprint 2 was accepted with 243 unit tests, four contrasting discovery sites, and
verified CI/artifacts. The repository owner confirmed milestone #3 is closed.
The runnable smoke catalog still contains ten cases; no Sprint 3 implementation
or extra executable coverage is claimed at kickoff.
