# Controlled Local Database Integration

The existing 15 database catalog definitions describe explicit sample contracts;
they are not applicable to every database and remain within the 100-case catalog.
This first reusable operator profile is internal and limited to owned SQLite
fixtures. It does not expose customer files, a server database connector or a UI
execution route.

## Explicit Record Count Review

`review_local_database` accepts a typed DatabaseConfiguration containing only an
environment reference for the database path, an explicit application table name,
expected count and caller-owned fixture directory. It checks directory identity
but does not resolve the database reference, open SQLite or contact a network.
Private root paths are excluded from the review representation. Its fingerprint
binds configuration, table/count and directory identity. A changed configuration,
confirmation, directory replacement or path redirection blocks parent dispatch.

Table identifiers are bounded lowercase ASCII names; SQLite internal tables,
qualified names and SQL fragments are rejected. The adapter generates exactly a
quoted `SELECT COUNT(*)` query with one explicit count assertion. Operators cannot
supply SQL, mutation statements or row values through this profile.

After separate explicit fingerprint confirmation, the internal runner uses the
existing isolated database child, 15-second process deadline and cancellation
callback. Existing read-only SQLite mode, query-only/authorizer limits and resolved
path confinement to the owned fixture root remain authoritative. No rows, resolved
database paths or raw SQLite errors are returned in reports. This is a trusted
local fixture workflow, not isolation from a hostile operator controlling the host.

Four contract checks cover non-resolving review, rejected SQL/count/origin input,
stale confirmation/configuration/root identity and bounded child dispatch. The
real isolated proof uses two different table layouts and expected counts: two
passes and one deliberate assertion failure. A reference resolving outside the
reviewed root is blocked, pre-cancellation passes no work to SQLite and fixture
file hashes remain unchanged. Reports contain statuses only; no catalog scenario
is added. All 37 database-focused checks passed locally.

Next add saved project-scoped reference/binding review, transactional free/paid
queue admission/cancellation/recovery, customer CLI commands and explicit UI
confirmation on controlled fixtures. No customer database access or central test
data collection is authorized by this internal increment.
