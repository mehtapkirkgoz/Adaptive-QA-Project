# Sprint 4 — API Testing

Start date: October 21, 2026 (Europe/Istanbul)
Status: In progress — phase 4.1 completed locally.
Tracking: [issue #5](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/5).
Milestone: Pending creation and association by the repository owner.

## Goal

Execute configured API checks against a controlled local fixture, with explicit
authentication references, structural/business assertions, redacted outcomes,
and enforced destination, mutation, response-size, and execution limits.

## Phases

- [x] 4.1: Define API configuration, request, and assertion contracts.
- [ ] 4.2: Implement bounded pinned-destination transport and safe reporting.
- [ ] 4.3: Add controlled positive/negative API coverage toward 60 combined cases.
- [ ] 4.4: Add explicit UI/API validation bindings.
- [ ] 4.5: Verify missing configuration, secrets, mutation policy, redirects, and deadlines.
- [ ] 4.6: Verify same-commit CI/artifacts and close after acceptance.

## Phase 4.1 Deliverables

Immutable API configuration references an authorized project origin and an optional
environment-based bearer token. Raw authentication strings are rejected. Requests
use explicit ASCII paths, typed methods, bounded query pairs, and bounded JSON
bodies. Read methods cannot carry bodies; non-read methods must declare data changes.
Limits reject unbounded timeouts, oversized responses, path traversal, duplicate
query keys, and invalid/non-finite JSON bodies.

JSON assertions use typed path components and explicit exists/type/equality/range/
length operators. This is a bounded assertion subset, not full JSON Schema or
OpenAPI validation. Query/body/expected operands are excluded from repr; later
reports must serialize only explicit safe outcome fields, never whole request models.
All 280 unit tests pass, including 12 API contract cases. No transport or runnable
API coverage is claimed at this checkpoint. Remote verification follows push.

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
