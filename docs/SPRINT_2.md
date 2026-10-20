# Sprint 2 — Website Discovery and Feature Detection

Start date: October 20, 2026
Status: In progress — phases 2.1 and 2.2 completed locally.

Tracking issue: [#3](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/3).
Milestone: [Sprint 2 — Website Discovery and Feature Detection](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/3).

## Goal

Collect structural evidence from controlled pages, discover permitted links within
budgets, identify features, and generate appropriate test plans with explicit reasons.

## Phases

- [x] 2.1: Define snapshots and conservative page-scoped login/search detection.
- [x] 2.2: Collect snapshots from the guarded browser.
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

Snapshots describe visible controls. The detector does not navigate links, execute
steps, or make network requests.

## Phase 2.2 Deliverables

- Read-only light-DOM collection from an already guarded Playwright page.
- Visible native forms, associated fields (including external form controls),
  labels, buttons, and HTTP(S) links converted into immutable snapshots.
- Input values are never read; URL queries/fragments and credential URLs are excluded.
- Limits: 50 forms, 100 controls per form, 200 links, 5,000 inspected elements,
  160 characters per text field, and 2,048 characters per URL.
- Truncation, embedded documents, shadow/custom elements, and unsupported form
  structures leave collection incomplete. Collection errors propagate.
- Real Chromium checks include the sample server through the destination guard
  and egress proxy, plus offline documents for hidden controls, values, limits,
  link sanitization, ambiguity, and feature detection.

Completeness refers only to the current supported DOM view. It does not establish
that delayed UI, closed shadow roots, or other routes have been inspected. The
caller owns navigation authorization and total execution deadlines. Labels and
URL paths are untrusted site content and may contain sensitive text; these
snapshots are currently held in memory, not published as sanitized reports.

## Absence Semantics

Positive evidence can establish present even during incomplete collection. Missing
evidence stays unknown until the page snapshot is complete. An absent result then
means no visible matching evidence on that page, never absence across the entire site.
Site-level aggregation and traversal coverage are separate pending work.

## Verification

192 unit tests pass locally, including 14 discovery and three collector cases. Tests cover matching
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
