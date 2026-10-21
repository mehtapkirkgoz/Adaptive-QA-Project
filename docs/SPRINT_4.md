# Sprint 4 — API Testing

Start date: October 21, 2026 (Europe/Istanbul)
Status: In progress — tracking initialized.
Tracking: [issue #5](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/5).
Milestone: Pending creation and association by the repository owner.

## Goal

Execute configured API checks against a controlled local fixture, with explicit
authentication references, structural/business assertions, redacted outcomes,
and enforced destination, mutation, response-size, and execution limits.

## Phases

- [ ] 4.1: Define API configuration, request, and assertion contracts.
- [ ] 4.2: Implement bounded pinned-destination transport and safe reporting.
- [ ] 4.3: Add controlled positive/negative API coverage toward 60 combined cases.
- [ ] 4.4: Add explicit UI/API validation bindings.
- [ ] 4.5: Verify missing configuration, secrets, mutation policy, redirects, and deadlines.
- [ ] 4.6: Verify same-commit CI/artifacts and close after acceptance.

## Acceptance Criteria

- [ ] Controlled positive and negative API cases pass.
- [ ] Missing API configuration has an explicit non-execution reason.
- [ ] Secrets and response payloads do not appear in reports/logs.
- [ ] Target and mutation policies and execution budgets are enforced.
- [ ] UI/API bindings preserve independent expected outcomes.
- [ ] Catalog counts reflect runnable behavior, not cosmetic variations.
- [ ] Remote CI and downloaded artifacts are verified before closure.

## Boundaries

Do not infer customer API endpoints or credentials from a site URL. Initial
execution remains confined to registered local fixtures. Public/customer API
execution, private network access, database validation, AI, and deployment
remain outside the initial adapter. A small explicit JSON assertion contract
will not be described as full JSON Schema/OpenAPI support.

## Baseline

Sprint 3 was accepted with 40 runnable UI cases, 268 unit tests, 96 variant runs,
40 reversed runs, and verified CI/artifacts. The owner confirmed milestone #4 closed.
API cases remain blocked by the existing UI-only planner until a compatible API
execution/configuration contract is implemented. No API coverage is claimed yet.
