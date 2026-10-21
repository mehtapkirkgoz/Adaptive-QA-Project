# Sprint 3 — UI Test Catalog and Element Matching

Start date: October 21, 2026 (Europe/Istanbul)
Status: Completed — implementation CI and downloaded evidence verified on October 21, 2026.
Tracking issue: [#4](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/4).
Milestone: [Sprint 3 — UI Test Catalog and Element Matching](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/4).
Issue #4 is closed as completed. The repository owner confirmed milestone #4 is closed.

## Goal

Run reusable UI scenarios across controlled applications with different control
names, using deterministic matching and explicit project mappings. Expand toward
approximately 40 meaningful runnable scenarios without inflating counts through
cosmetic variants or unimplemented definitions.

## Phases

- [x] 3.1: Define validated element mapping and matching result contracts.
- [x] 3.2: Implement role/label/alternative-name matching with controlled missing and ambiguous outcomes.
- [x] 3.3: Bind reusable executors to discovered pages and contrasting fixture variants.
- [x] 3.4: Expand login, form, search, navigation, and negative UI coverage toward 40 runnable scenarios.
- [x] 3.5: Add isolated test data preparation/cleanup and data-change policy enforcement.
- [x] 3.6: Verify independent/repeated execution, remote CI, artifacts, and acceptance.

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

At this checkpoint 256 unit tests passed locally, including 13 new contract cases.
Compilation and diff checks passed. These models do
not locate elements or execute actions yet; browser matching belongs to phase 3.2.
The runnable smoke catalog was still ten cases at this checkpoint.

## Phase 3.2 Deliverables

Read-only Chromium matching unions all configured alternatives and deduplicates
DOM identity. Hidden/inert/aria-hidden candidates are excluded. Exact role names
and labels are required; project test-ID overrides replace defaults. Missing or
duplicate scopes fail explicitly. Multiple visible candidates remain ambiguous.
The matcher caps candidates at 200 and has a cooperative five-second operation
budget; callers must still supply a hard process deadline. A matched static DOM
handle cannot retarget silently after replacement and must be disposed by its caller.
Visibility does not imply enabled/actionable state. No click or fill occurs here.

At this checkpoint 256 unit tests and 18 real Chromium checks passed locally. CI runs the matching
script and retains its report under `artifacts/matching/`. Runtime execution and
fixture bindings belong to phase 3.3; the catalog was still ten scenarios here.

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

## Phase 3.4 Deliverables

The catalog now contains 40 registered scenarios: 10 login, 8 search, 16 native
form, and 6 navigation behaviors. Thirty added executors assert keyboard/reset
behavior, validation constraints, selection states, protected inputs, literal
markup rendering, and history/state preservation. See [catalog guide](UI_CATALOG.md).
Every added definition has an explicit expected outcome; variants do not inflate
the count. A browser-invalid username regex was corrected in the fixtures after
the negative case exposed it.

Visible native fields and supported links now provide general forms/navigation
prerequisites. These are structural prerequisites, not universal executor bindings.
Existing discovery acceptance still checks its original five-feature matrix;
the planner additionally carries forms/navigation evidence and limitations.

All 262 unit tests pass locally. The 40-case queue run verifies registered
executors, saved results, and screenshots. The 32 currently reusable cases pass
96 isolated runs across English, Turkish, and mapped fixtures. Discovery budget
and contrasting-site regressions also pass. Final CI evidence is recorded below.

## Phase 3.5 Deliverables

New action scenarios use immutable fake sample data, explicit browser-local
preparation, and cleanup on success or assertion failure. Cleanup resets native
forms/statuses, clears local/session storage and cookies, and rejects unknown
origins/paths. It never deletes backend records. A cleanup error invalidates the
run instead of preserving a pass. Screenshots are captured before cleanup.
Fresh contexts/processes still provide the final resource and data boundary for
all scenarios, including legacy checks. Real customer mutations remain unsupported.

All 268 unit tests pass, including five new data/policy boundary cases. Real
Chromium checks verify failure cleanup and context separation; all 40 scenarios
also pass in reversed catalog order in isolated processes. The forward queue
run and reversed run cover the same IDs without increasing the case count.
The policy regression confirms data-changing definitions are blocked before
browser preparation. Same-commit verification is recorded in phase 3.6.

## Phase 3.6 Verification

Local acceptance covers 40 queued cases, 96 variant runs, 40 reverse-order runs,
18 matching checks, cleanup/context separation, and 268 unit tests. The final
audit corrected cross-feature prerequisites for the login/search independence
and navigation/state cases. A real catalog regression verifies that separate
login/search pages cannot satisfy the combined case. The multi-page discovery
fixture selects 39 cases and blocks that combined case, preserving explicit scope.
See [acceptance review](SPRINT_3_ACCEPTANCE.md). The accepted implementation SHA is
`eb95e96696d148133747ee4f290cb727f9fc4bb1`, verified in [CI](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39519899466).
All four jobs passed. Three downloaded artifact digests matched GitHub metadata
and the implementation SHA. Both OS lifecycle reports, 18 matching checks, 96
variant runs, 40 reversed runs, 40 queued JSON records, and 176 linked PNGs were
verified. Discovery/fixture/security regressions passed. A FORM-005 screenshot
visibly retained express delivery selected before cleanup.

## Acceptance Criteria

- [x] Shared tests work against controlled pages with different element names.
- [x] Missing and ambiguous controls produce explicit controlled outcomes.
- [x] Cases are independent of execution order and isolate their test data.
- [x] Data-changing actions respect project policy and include cleanup behavior.
- [x] Repeated runs produce explainable results and evidence.
- [x] Catalog counts reflect implemented runnable coverage.
- [x] CI and downloaded evidence are verified for the accepted implementation commit.

## Scheduled Continuation

The hourly follow-up covered Sprint 3 only and is paused after acceptance.
Sprint 4, deployment, and customer-site execution were outside its scope.

## Baseline

Sprint 2 was accepted with 243 unit tests, four contrasting discovery sites, and
verified CI/artifacts. The repository owner confirmed milestone #3 is closed.
The baseline catalog contained ten cases. Phase 3.1 added configuration and result
contracts without claiming extra executable scenario coverage; phase 3.4 expanded it to 40.
