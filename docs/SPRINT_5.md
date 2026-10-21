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
- [x] 5.2: Implement the first bounded adapter with enforced read-only execution, row limits, deadlines, and safe outcomes.
- [x] 5.3: Implement controlled fixture preparation and approximately 15 distinct database scenarios.
- [x] 5.4: Validate a record created through a controlled UI/API operation without combining independent layer outcomes.
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
Additional executable catalog cases are not implemented.

## Phase 5.2 Progress

The internal SQLite primitive now binds parameters through the driver, opens
existing fixture files with `mode=ro`, enables `query_only`, disables trusted
schema and extension loading, and installs an authorizer with a narrow read and
function allowlist. Writes, attachments, pragmas, and other operations are denied
by SQLite authorization rather than SQL keyword matching. A trusted caller must
supply a fixture root; the resolved private file must remain inside it. Only
the fixed local sample project origin is accepted. This is not OS isolation
against a concurrent filesystem attacker or permission to query customer files.

Row count, cumulative encoded bytes, SQLite value/column/expression limits,
cooperative query timeouts, and cancellation are enforced. Results expose only
safe statuses and failed assertion indexes; rows, paths, SQL, and SQLite error
messages remain private. All connections close on success and failure.

Eight tests exercise real disposable SQLite files, including bound injection
input, write rejection, resource limits, recursive-query interruption, cleanup,
and safe outcome classification. The full local suite passes 324 tests.
An isolated child now enforces a hard total deadline and active cancellation,
using the established process-tree termination mechanism. Private temporary
inputs carry templates and operands but not resolved database paths; they are
removed after execution and never used as report artifacts. Child stdout and
stderr are suppressed. Parent output validation requires the expected case ID,
typed result, bounded output, and no evidence paths. No database CLI or catalog
execution is enabled in this increment.

Eight additional process tests cover real child passes/failures, write rejection,
total timeout, active cancellation, released database locks, private roundtrips,
prestart non-execution, invalid deadlines, and missing output. The full local
suite passes 332 tests. Same-commit remote acceptance remains pending.

## Phase 5.3 Delivered

Fifteen executable database scenarios cover product identity/missing records,
catalog count, price, unavailable and available stock, Unicode lookup, order
ownership/status/customer filtering, nullable notes, quantity and total
aggregation, product references, and literal SQL-like parameters. These are
distinct behaviors, not repeated execution counts. The combined catalog now
contains 75 definitions: 40 UI, 20 API, and 15 database.

`scripts/check_local_database.py` creates fake records in a fresh temporary
database, runs every case in an isolated child, confirms the fixture bytes are
unchanged, removes the fixture, and writes metadata-only evidence. Exclusive file
creation prevents overwriting existing files. Local execution passed all 15
scenarios; 334 unit tests pass. Dedicated Ubuntu and Windows CI jobs now repeat
the scenario and boundary checks and retain safe JSON evidence. Remote results
and cross-layer creation validation remain pending; seeded fixtures alone do
not satisfy phase 5.4.

## Phase 5.4 Delivered

A real guarded UI search prerequisite is followed by an explicitly authorized,
authenticated API fixture operation that creates a fixed fake order. SQLite
independently reads its customer and status through bound parameters. The
integration proves the record absent before creation. UI search is a prerequisite,
not a claim that the UI created the order. The database adapter itself remains
read-only; fixture provisioning and API writes use separate owned connections.

Explicit project and case bindings require both trusted UI/API results to pass.
Missing/foreign configuration and failed prerequisites prevent database execution.
The four local integration controls verify successful creation/readback, denied
API mutation, blocked follow-up, and intentional database assertion failure while
upstream results stay passed. Five unit tests cover gating, identity mismatches,
foreign configuration, adapter errors, and independent outcomes. Local validation:
339 unit tests and the real four-control bridge pass. The bridge is an integration
control, not an extra catalog case. CI browser acceptance now repeats it.

## Acceptance

Queries use bound parameters and project-specific templates. Database reads
have bounded rows, bytes, and execution time. Read-only authorization is enforced
by the adapter/database, not a SQL keyword check. Connection/runtime failures
remain distinct from assertion failures. Results exclude SQL parameters, returned
rows, connection strings, and secrets. Controlled integration demonstrates the
UI/API/database chain and isolated cleanup. Acceptance requires same-commit CI
evidence and owner-managed sprint closure; Sprint 6 does not start automatically.
