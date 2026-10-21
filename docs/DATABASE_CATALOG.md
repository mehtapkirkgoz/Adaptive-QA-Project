# Database Catalog

The first adapter validates explicitly configured SQLite fixtures under a trusted
local root. Its private path is resolved through an environment reference. SQLite
does not authenticate server credentials; network database adapters remain future
work. The queue database is separate from this validation fixture.

| Case | Behavior |
|---|---|
| DB-001 | Product lookup by bound primary key |
| DB-002 | Missing product returns no rows |
| DB-003 | Product catalog row count |
| DB-004 | Persisted product price |
| DB-005 | Identification of unavailable stock |
| DB-006 | Filtering available products |
| DB-007 | Unicode name lookup |
| DB-008 | Order customer ownership |
| DB-009 | Persisted paid order status |
| DB-010 | Customer-specific order filtering |
| DB-011 | Null optional note |
| DB-012 | Aggregated line quantity |
| DB-013 | Total from stored quantities and prices |
| DB-014 | Product reference integrity |
| DB-015 | SQL-like customer parameter stays literal |

Run `python scripts/check_local_database.py` for 15 isolated scenario outcomes;
run `python scripts/check_database_boundaries.py` for 19 boundary probes and 15
reverse-order executions. These repetitions do not increase the case count.
`python scripts/check_database_bridge.py` separately verifies a real UI
prerequisite, API-created fake order, and read-only database assertions.

Every fixture is disposable. Query templates belong to a project and use driver
parameter binding. Authorization denies writes regardless of project mutation
permission; only the separate integration fixture API may create a record after
explicit mutation authorization. Reads enforce row, encoded byte, SQLite value,
column, expression, cooperative query time, and parent process total-time bounds.
SQL parameters, rows, private paths, and raw database errors are not reports.

This is a controlled local prototype, not OS filesystem isolation or a general
customer database client. Memory allocation is not governed by a container quota.
Template/schema approval and fixture ownership are trusted host responsibilities.
No arbitrary SQL from website content or AI is accepted as authorization. UI
plans remain non-executing and do not infer database connections or queries.
