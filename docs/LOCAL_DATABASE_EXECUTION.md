# Controlled Local Database Integration

The existing 15 database catalog definitions describe explicit sample contracts;
they are not applicable to every database and remain within the 100-case catalog.
The reusable operator profile is limited to owned SQLite fixtures. The local
dashboard provides explicit saved-binding review, confirmation and history. It
does not expose customer file selection or a server database connector.

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

## Internal Confirmed Queue and Pinned Worker

`LocalDatabaseQueue` now transactionally admits an explicit current saved-review
fingerprint, with owner isolation and shared free/paid pending/running capacity.
API, form and UI admissions count these jobs too. Claim tokens, current settings/
license checks, cancellation and status-only finalization mirror the existing
controlled API lifecycle. Changed settings block dispatch or stop active work;
interrupted recovery never retries. Offline workspace recovery cancels database
jobs and clears claims alongside other queues.

The internal worker derives exactly
`{workspace}/database-fixtures/{project_id}` from the canonical project-store path.
It requires that existing directory without redirection before creating the
count-only review. There is no HTTP or environment fixture-root override. Only
then may the existing supervised child resolve the scoped database-path reference;
the resolved file must stay inside that fixed root. Missing/redirected roots never
dispatch a database child. Target fixture files are not included in application
workspace backups; recovery restores application metadata/results and cancels work,
not copies of target databases.

Eight real SQLite queue checks passed: confirmation/ownership, concurrent pending
limits and unique claims, drift/cancellation/no retry, sanitized failures, signed
license capacity/expiry, backup restoration, API/DB shared pending capacity and
missing/redirected-root denial. The real isolated saved-queue proof returned one
pass, one deliberate count failure and one outside-fixed-root block; every fixture
file hash stayed unchanged and raw paths/rows were not persisted. The 100-case
catalog is unchanged. HTTP admission, customer CLI and operator UI remain the next
integration step; no customer database connector is enabled by this increment.

## Explicit One-Shot Worker Commands

An operator can process at most one already confirmed database job with the same
workspace used by the local dashboard. Replace these example paths:

```powershell
python -m adaptive_qa dashboard free-database-once --database C:/QA/workspace/projects.sqlite
python -m adaptive_qa local database-once --workspace C:/QA/workspace --trusted-keys C:/QA/publisher-public-keys.json
```

Free commands refuse licensing state and create no account database. Paid commands
always construct the licensed store; current entitlement and shared capacity are
checked before claim. `free-recover-database` and `local recover-database` explicitly
mark interrupted work terminal under the worker lock and never execute/retry it.
The existing worker-cycle command remains unchanged; DB has a separate command.
No command admits a new job or accepts a target path/root override.

Fourteen CLI checks passed. The real controlled saved-queue proof now uses a
separate free-database-once process for pass, expected assertion failure and
outside-fixed-root denial, retaining unchanged fixture file hashes. HTTP admission
and the operator editor/confirmation UI are not enabled yet.

## Protected Local HTTP Admission

Free/licensed local apps now expose project-scoped `/local-database/jobs`: POST
accepts exactly the current `confirmed_contract_fingerprint`, GET lists the latest
twenty jobs, GET `/{job_id}` reads one job and POST `/{job_id}/cancel` accepts an
empty object. Mutations require the existing local session, Origin and CSRF token.
Admission revalidates the owned snapshot and current license/capacity inside one
write transaction; the HTTP handler never starts SQLite execution.

Path/root overrides, missing/stale confirmation and unknown fields are rejected.
The fixed workspace/project fixture root remains authoritative. HTTP tests verify
ownership, guarded cancellation and reference revocation. The real controlled proof
now saves/reviews/confirms through HTTP, runs the separate free CLI and reads the
persisted pass/fail/outside-root-block outcomes through HTTP. A fourth queued job
is cancelled before execution, fixture hashes stay unchanged and resolved database
paths are absent from application storage. All 49 database-focused tests passed.
The operator DB editor and explicit confirmation/history panel remain next; no
customer file picker or general database connector is enabled.


## Explicit Local Operator Panel

Free and licensed dashboards now edit the typed table/count binding without SQL
or file-path inputs. The operator selects the scoped database-path reference,
saves, reviews the current snapshot and explicitly confirms one count. Unsaved
edits clear confirmation and block admission. History exposes status-only results
and guarded cancellation; uncertain admission is never retried automatically.
Worker instructions use the fixed project fixture directory and a separate
one-shot command. The three-queue worker cycle stays unchanged.

The free browser proof configured a three-record owned fixture through the UI,
ran the real separate CLI, observed a passed result, cancelled a second job,
verified reload/save/removal and unchanged fixture bytes, and checked a 390px
panel without horizontal overflow. It recorded no external browser requests or
page errors. Licensed/installed DB operator acceptance remains pending.


Licensed source UI proof now saves/reviews/confirms an empty owned SQLite table,
runs the actual authenticated local database-once command and observes a passed
result. Fixture bytes remain unchanged. Offline backup/restore preserves the DB
binding and status-only result, requires fresh login and intentionally does not
copy target fixture databases. The existing discovery/UI/API proofs also passed
with no external browser requests or page errors. Production and unchanged-demo
builds passed. Installed-wheel and new exact-commit CI acceptance remain pending.


Installed DB operator validation passed for package commit 273f96a. All four
release file sizes/digests matched, the wheel was installed outside the checkout,
and its licensed dashboard/CLI performed the explicit owned count, preserved
fixture bytes, restored settings/results without copying target databases and
required fresh login. Catalog remains 51 UI + 34 API + 15 DB. No external browser
requests or page errors occurred. Safe local evidence is recorded in
`docs/evidence/installed-database-273f96a.json`. This is local installed proof,
not yet remote exact-commit artifact acceptance or customer deployment.


Consolidated local regression completed 832 tests (831 passed, one Windows
permission skip). The unchanged Pages demo passed at 390/768/1440px with zero
API/external requests and execution disabled. Release verification now requires
DB result/fixture-locality/recovery evidence, and CI retains the mobile panel
screenshots. Exact-commit remote artifact acceptance remains pending.


## Exact-Commit Controlled Acceptance

Implementation 273f96af74e3c4d68688f953cab5abdab38b393b passed Core checks
40128832953: all twelve jobs succeeded. All twelve artifact archives matched their
reported SHA-256, byte size and implementation SHA; ZIP CRC checks passed, 210
PNGs validated and the inactive release's four inner files matched its manifest.
Free/source-licensed/installed-licensed browser reports independently confirm the
DB operator flow; licensed reports preserve results through recovery without
copying target fixtures. Evidence: `docs/evidence/database-ci-273f96a.json`.
The follow-up verifier/evidence commit 1758fb4 also passed Core checks 40128995531;
its artifacts have not been separately accepted here.

This closes the bounded DB integration checkpoint, not general database support
or overall owner acceptance. Customer databases, arbitrary roots/SQL, production
issuer infrastructure, public backend activation and customer deployment remain
outside this accepted scope. Owner dashboard sessions were not restarted.
