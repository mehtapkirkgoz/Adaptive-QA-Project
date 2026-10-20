# Sprint 2 — Website Discovery and Feature Detection

Start date: October 20, 2026
Status: In progress — phases 2.1 through 2.3 completed locally.

Tracking issue: [#3](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/3).
Milestone: [Sprint 2 — Website Discovery and Feature Detection](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/3).

## Goal

Collect structural evidence from controlled pages, discover permitted links within
budgets, identify features, and generate appropriate test plans with explicit reasons.

## Phases

- [x] 2.1: Define snapshots and conservative page-scoped login/search detection.
- [x] 2.2: Collect snapshots from the guarded browser.
- [x] 2.3: Discover links within page, depth, request, and time limits.
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
snapshots are not published as sanitized customer reports. Integration reports
contain only controlled fixtures; CLI output must still be treated as sensitive.

## Phase 2.3 Deliverables

- Breadth-first traversal with cycle detection and redirect destination deduplication.
- Every candidate and final page is authorized; browser requests and redirects
  also pass through the existing destination guard and pinned egress proxy.
- Defaults: five page attempts, depth two, 100 request authorizations, 30 seconds.
  Configuration caps: 50 page attempts, depth five, 200 requests, 120 seconds.
- Failed page attempts consume the page budget. The frontier has at most 500
  known URL identifiers. Queries/fragments are removed and default ports normalized.
- Explicit limitations identify page/depth/time/frontier limits, excluded links,
  incomplete collection, load failures, request exhaustion, and policy denials.
- The local discovery runner executes in a separate process; the parent terminates
  its process tree at the total deadline. Cleanup may take additional time.
  A hard timeout discards partial child results and reports that explicitly.
- Five real Chromium scenarios verify traversal, page/depth/request budgets,
  redirects, cycles, excluded destinations, and the process deadline.

Only the fixed controlled local target is executable. The callback-based traversal
core requires its caller to enforce request limits and blocking-operation deadlines;
the local runner supplies those controls. Request accounting counts proxy
authorization attempts (including redirect checks), not only successful transfers.
Query-driven pages, fragment routes, arbitrary customer sites, and site-wide
coverage are outside this checkpoint.

With the controlled sample server running, inspect discovery output using:

```powershell
python -m adaptive_qa.local_discovery
```

## Absence Semantics

Positive evidence can establish present even during incomplete collection. Missing
evidence stays unknown until the page snapshot is complete. An absent result then
means no visible matching evidence on that page, never absence across the entire site.
Site-level aggregation remains pending; traversal limitations must inform it.

## Verification

206 unit tests pass locally, including 14 discovery, three collector, and 14 traversal cases. Tests cover matching
actions, Turkish normalization, search semantics, hidden controls, mixed forms,
registration/passwordless ambiguity, weak links, collection completeness, and
snapshot validation. Compilation and diff checks pass.

No new runtime dependencies. The phase 2.2 [CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39494076177)
passed. Phase 2.3 requires remote verification after push. Local browser regression
checks cover nine egress scenarios and the ten existing queued smoke cases.

## Remaining Acceptance Criteria

- [ ] Different controlled sites produce appropriate feature sets and plans.
- [ ] Absent and uncertain features remain distinguishable after aggregation.
- [ ] Skipped/blocked cases include explicit reasons.
- [ ] Discovery respects destination policies and configured budgets.
- [ ] Remote checks pass and reports are reviewed before closing the sprint.
