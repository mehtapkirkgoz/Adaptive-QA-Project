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

## Saved Count Binding and Owner Review

Project configuration now accepts optional `local_database_binding` containing
exactly `table` and `expected_count`. It uses the same typed identifier/count
validation as the internal count-only adapter. No SQL, root directory, database
file path or row value is accepted in this metadata. Null removes it; invalid
replacements preserve prior settings. The existing `database_path` reference must
use the exact owner/project/slot namespace. Saving may remove that reference to
revoke readiness without discarding the binding.

Local free/licensed apps expose POST
`/api/projects/{project_id}/local-database/review` with an empty JSON object and
the existing session/Origin/CSRF checks. One owner-scoped snapshot is validated;
review requires the saved binding and scoped database reference. Its digest binds
the complete settings and typed configuration. It does not resolve the reference,
stat a target directory, open SQLite, start a process, enqueue work or reserve
licensed capacity. The response states `execution_authorized: false` and includes
no environment reference name or resolved path.

The dashboard currently preserves this metadata on unrelated saves; a DB editor
and execution route are not enabled. Three persistence/HTTP checks cover reload,
ownership, reference revocation, foreign reference rejection, invalid replacement/
removal, full-settings drift and session/Origin/CSRF guards. All 40 database-focused
checks and six shared-settings checks passed; production/demo builds and the real
free browser save-preservation/discovery/UI/API drill passed without external
requests or page errors.

Next implement confirmed queue admission, shared free/paid capacity, cancellation
and offline-recovery cleanup. The saved workflow must derive a fixed controlled
fixture directory from the workspace and project identity (for example
`database-fixtures/{project_id}`); it must not accept an HTTP-supplied root or turn
the path reference into an unrestricted filesystem grant. Resolve the database
reference only inside the supervised worker and retain existing path confinement.
Only operator-prepared controlled fixtures may be exercised during implementation.
Customer file selection, arbitrary roots, server DB credentials and a general DB
connector remain outside this profile and have not been enabled.
