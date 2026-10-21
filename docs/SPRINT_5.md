# Sprint 5 — Database Validation

Started: 2026-10-21
Status: In progress
Tracking issue: [#6](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/6)
Milestone: Awaiting the owner's milestone link.

## Goal

Add bounded, configured database validation and demonstrate one controlled
UI/API/database flow. The current catalog has 40 UI and 20 API cases; no
database case is executable yet. Aim for approximately 15 meaningful database
scenarios, subject to implemented behavior and verified acceptance.

## Delivery Phases

- [x] 5.0: Establish sprint tracking and owner-controlled continuation rules.
- [ ] 5.1: Define database configuration, query templates, parameters, assertions, and secret references.
- [ ] 5.2: Implement the first bounded adapter with enforced read-only execution, row limits, deadlines, and safe outcomes.
- [ ] 5.3: Implement controlled fixture preparation and approximately 15 distinct database scenarios.
- [ ] 5.4: Validate a record created through a controlled UI/API operation without combining independent layer outcomes.
- [ ] 5.5: Verify write rejection, malformed queries, connection failures, timeout/cancellation, redaction, and cleanup.
- [ ] 5.6: Review exact-commit CI and artifacts; report technical acceptance to the owner.

## Adapter Decision Gate

Choose the first database explicitly before implementation. Existing queue
SQLite storage is not a database validation adapter. A file-based fixture must
not be presented as verification of network database authentication. If SQLite
is chosen initially, document its lack of server credentials and separately
validate the secret-reference contract without claiming authenticated execution.
Customer databases remain disabled until their connection and access policies
are implemented and verified.

## Acceptance

Queries use bound parameters and project-specific templates. Database reads
have bounded rows, bytes, and execution time. Read-only authorization is enforced
by the adapter/database, not a SQL keyword check. Connection/runtime failures
remain distinct from assertion failures. Results exclude SQL parameters, returned
rows, connection strings, and secrets. Controlled integration demonstrates the
UI/API/database chain and isolated cleanup. Acceptance requires same-commit CI
evidence and owner-managed sprint closure; Sprint 6 does not start automatically.
