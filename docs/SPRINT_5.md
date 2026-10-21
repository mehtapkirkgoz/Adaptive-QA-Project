# Sprint 5 — Database Validation

Started: 2026-10-21
Status: In progress
Tracking issue: [#6](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/6)
Milestone: [Sprint 5 — Database Validation](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/6)

## Goal

Add bounded, configured database validation and demonstrate one controlled
UI/API/database flow. The current catalog has 40 UI and 20 API cases; no
database case is executable yet. Aim for approximately 15 meaningful database
scenarios, subject to implemented behavior and verified acceptance.

## Delivery Phases

- [x] 5.0: Establish sprint tracking and owner-controlled continuation rules.
- [x] 5.1: Define database configuration, query templates, parameters, assertions, and secret references.
- [ ] 5.2: Implement the first bounded adapter with enforced read-only execution, row limits, deadlines, and safe outcomes.
- [ ] 5.3: Implement controlled fixture preparation and approximately 15 distinct database scenarios.
- [ ] 5.4: Validate a record created through a controlled UI/API operation without combining independent layer outcomes.
- [ ] 5.5: Verify write rejection, malformed queries, connection failures, timeout/cancellation, redaction, and cleanup.
- [ ] 5.6: Review exact-commit CI and artifacts; report technical acceptance to the owner.

## Adapter Decision Gate

SQLite is the first validation adapter for controlled local fixtures. Existing queue
SQLite storage is not a database validation adapter. A file-based fixture must
not be presented as verification of network database authentication. If SQLite
is chosen initially, document its lack of server credentials and separately
validate the secret-reference contract without claiming authenticated execution.
Customer databases remain disabled until their connection and access policies
are implemented and verified.

## Phase 5.1 Delivered

Immutable configuration uses an environment reference for the private database
path and bounded time, row, and byte limits. Project-owned query templates declare
exact unique parameter names. Parameters and assertion operands accept only
bounded immutable scalars. Database cases require read-only definitions and at
least one typed row-count or cell-equality assertion. SQL, parameter values, and
expected operands are excluded from representations. Creating a contract neither
connects nor resolves secrets. SQL authorization and actual parameter binding
remain adapter responsibilities in phase 5.2; models are not an execution permit.

Nine new model tests pass; the complete local suite has 316 passing tests.
Database execution and additional executable catalog cases are not implemented.

## Acceptance

Queries use bound parameters and project-specific templates. Database reads
have bounded rows, bytes, and execution time. Read-only authorization is enforced
by the adapter/database, not a SQL keyword check. Connection/runtime failures
remain distinct from assertion failures. Results exclude SQL parameters, returned
rows, connection strings, and secrets. Controlled integration demonstrates the
UI/API/database chain and isolated cleanup. Acceptance requires same-commit CI
evidence and owner-managed sprint closure; Sprint 6 does not start automatically.
