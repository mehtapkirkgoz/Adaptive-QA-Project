# Sprint 3 — UI Test Catalog and Element Matching

Start date: October 21, 2026 (Europe/Istanbul)
Status: In progress — phases 3.1 through 3.3 completed locally.
Tracking issue: [#4](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/4).
Milestone: [Sprint 3 — UI Test Catalog and Element Matching](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/4).

## Goal

Run reusable UI scenarios across controlled applications with different control
names, using deterministic matching and explicit project mappings. Expand toward
approximately 40 meaningful runnable scenarios without inflating counts through
cosmetic variants or unimplemented definitions.

## Phases

- [x] 3.1: Define validated element mapping and matching result contracts.
- [x] 3.2: Implement role/label/alternative-name matching with controlled missing and ambiguous outcomes.
- [x] 3.3: Bind reusable executors to discovered pages and contrasting fixture variants.
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

## Phase 3.1 Deliverables

- Immutable locator specs for accessible role/name, label, and test ID.
- Logical control names, up to 20 alternative locators, and optional form/region
  scoping through an explicit test ID. Raw CSS/XPath is not part of the contract.
- Project-specific overrides replace defaults for the same logical control;
  they do not silently merge with fallback alternatives. Project identity is checked.
- Match results distinguish matched, missing, ambiguous, and error, with explicit
  reasons and rule indexes. Counts and indexes must agree with the result status.
- Bounds, typed tuples/enums, duplicate alternatives, duplicate logical names,
  invalid roles, and malformed text are rejected before browser use.

All 256 unit tests pass locally, including 13 new contract cases. Compilation
and diff checks pass. Remote verification is pending after push. These models do
not locate elements or execute actions yet; browser matching belongs to phase 3.2.
The runnable smoke catalog remains at ten cases.

## Phase 3.2 Deliverables

Read-only Chromium matching unions all configured alternatives and deduplicates
DOM identity. Hidden/inert/aria-hidden candidates are excluded. Exact role names
and labels are required; project test-ID overrides replace defaults. Missing or
duplicate scopes fail explicitly. Multiple visible candidates remain ambiguous.
The matcher caps candidates at 200 and has a cooperative five-second operation
budget; callers must still supply a hard process deadline. A matched static DOM
handle cannot retarget silently after replacement and must be disposed by its caller.
Visibility does not imply enabled/actionable state. No click or fill occurs here.

All 256 unit tests and 18 real Chromium checks pass locally. CI runs the matching
script and retains its report under `artifacts/matching/`. Runtime execution and
fixture bindings belong to phase 3.3; the smoke catalog remains ten scenarios.

## Phase 3.3 Deliverables

Existing LOGIN-001 and SEARCH-001 definitions now have reusable fixture adapters
for English/Turkish labels and explicit test-ID project overrides. Each isolated
variant run validates its destination, collects structural evidence, checks the
non-executing plan prerequisites, and dispatches only the registered controlled
executor. Six runs pass across three fixtures with fresh browser processes and
screenshots; this does not increase the ten-case catalog count. Root smoke
behavior is preserved. Missing/ambiguous bindings produce blocked outcomes,
while browser matching errors remain execution errors. Four new unit cases cover
dispatch rejection and classification; all 260 unit tests pass locally.

The mapped fixture changes input labels while retaining recognizable submit
semantics for discovery. Universal custom action-name discovery is not claimed.
AI, arbitrary customer URLs, and automatic plan execution remain disabled.

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
The runnable smoke catalog still contains ten cases. Phase 3.1 adds configuration
and result contracts, without claiming extra executable scenario coverage.
