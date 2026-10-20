# Sprint 2 — Website Discovery and Feature Detection

Start date: October 20, 2026
Status: In progress — phase 2.1 completed locally.

Tracking issue: [#3](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/3).
Milestone: Pending creation and association in GitHub.

## Goal

Collect structural evidence from controlled pages, discover permitted links within
budgets, identify features, and generate appropriate test plans with explicit reasons.

## Phases

- [x] 2.1: Define snapshots and conservative page-scoped login/search detection.
- [ ] 2.2: Collect snapshots from the guarded browser.
- [ ] 2.3: Discover links within page, depth, request, and time limits.
- [ ] 2.4: Add registration, product, and cart evidence rules.
- [ ] 2.5: Aggregate findings and generate applicable test plans.
- [ ] 2.6: Verify contrasting sample sites, CI, and acceptance criteria.

## Phase 2.1 Deliverables

- Immutable page, form, field, and link snapshots with input validation.
- No field values, passwords, cookies, or tokens in the snapshot model.
- English/Turkish action-name normalization for initial login/search rules.
- Positive login evidence must come from matching fields/actions in one visible form.
- Hidden fields/forms, registration password fields, and passwordless forms cannot
  accidentally prove a conventional password login flow.
- Links and incomplete forms are hints, yielding unknown instead of false certainty.
- Every finding includes its page URL, reason, evidence references, and page scope.

Snapshots describe visible controls. A future collector must include only visible
button labels in each form and set collection_complete only after a successful read.
The detector does not navigate links, execute steps, or make network requests.

## Absence Semantics

Positive evidence can establish present even during incomplete collection. Missing
evidence stays unknown until the page snapshot is complete. An absent result then
means no visible matching evidence on that page, never absence across the entire site.
Site-level aggregation and traversal coverage are separate pending work.

## Verification

189 unit tests pass locally, including 14 discovery cases. Tests cover matching
actions, Turkish normalization, search semantics, hidden controls, mixed forms,
registration/passwordless ambiguity, weak links, collection completeness, and
snapshot validation. Compilation and diff checks pass.

No new runtime dependencies. Current changes require remote CI verification after push.
The guarded sample runner and Sprint 1 behavior remain unchanged.

## Remaining Acceptance Criteria

- [ ] Different controlled sites produce appropriate feature sets and plans.
- [ ] Absent and uncertain features remain distinguishable after aggregation.
- [ ] Skipped/blocked cases include explicit reasons.
- [ ] Discovery respects destination policies and configured budgets.
- [ ] Remote checks pass and reports are reviewed before closing the sprint.
