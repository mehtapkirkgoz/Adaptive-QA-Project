# Local Operations and Published Demo

## Runtime Boundaries

The public GitHub Pages site is a static interface demo. Its sample projects and
reports do not execute tests or contact target sites. The authenticated Python
application, SQLite stores and browser workers stay local. Never expose the
prototype through a public tunnel or change its host/origin guards to make Pages
call it. Public backend/container deployment remains unimplemented and unauthorized.

Use Python 3.13, locked dependencies, a built frontend and installed Chromium as
documented in SETUP.md. Release packages do not include Python, Chromium, OS
libraries or controlled fixtures. Packaging alone is not runtime provisioning.

## Environment Storage and Local Start

Choose one private absolute data root. Keep local, staging and production data in
their respective child directories. Do not place them in frontend/dist,
frontend/dist-demo or a web server's static root. Windows operators must inspect
private ACLs; POSIX backup/recovery roots request mode 0700.

From the repository PowerShell terminal, prepare a local plan:

```powershell
$qaDataRoot = Join-Path (Get-Location).Path 'artifacts/environments'
python -m adaptive_qa deployment plan --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765
```

The plan creates nothing. To provision a local account, use the interactive CLI
with `$qaDataRoot/local/auth.sqlite` as its `--database`. Enter the email and
password privately at the prompt. Do not place a password on a command line,
in a workflow, repository file or report.

```powershell
python -m adaptive_qa dashboard create-user --database "$qaDataRoot/local/auth.sqlite"
python -m adaptive_qa dashboard serve --database "$qaDataRoot/local/auth.sqlite" --ui-directory frontend/dist --port 8765
```

The server binds only 127.0.0.1:8765 with strict Host/Origin controls and forwarded
headers disabled. Its project database is the sibling projects.sqlite. Existing
environment data is reused; the server must not be started against an arbitrary
backup or recovery directory without a reviewed compatibility/cutover decision.

## Explicit Local Worker Invocations

In a separate terminal after reviewing a plan and explicitly queueing work:

```powershell
python -m adaptive_qa dashboard discovery-once --database "$qaDataRoot/local/projects.sqlite"
python -m adaptive_qa dashboard run-once --database "$qaDataRoot/local/projects.sqlite"
```

Each command processes at most one eligible queued job. It is not an unbounded
worker daemon or production supervisor. Existing process locks, ownership checks,
timeouts, cancellation and local-target policies still apply. Test plans never
start work by themselves. Keep the controlled fixture on port 8000 available
when its explicit local cases require it. No customer-site execution is enabled.

## Bounded Storage Health

```powershell
python -m adaptive_qa deployment storage-health --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765
```

Exit 0 means both fixed stores passed path/size, supported revision/core-column,
SQLite integrity and foreign-key checks. Exit 2 means storage is unavailable or
incompatible. The output includes only environment, database kind, readiness and
safe revision/reason fields. Missing databases are never created. Checks use
read-only SQLite connections, a one-second lock wait and a two-second progress
budget per database; databases above 256 MiB require an operator capacity review.

The scope is database storage only: ready does not mean the web process, worker,
Chromium, DNS or remote service is healthy. Check the local UI and explicitly
review a controlled run for end-to-end readiness. A SQLite WAL environment may
require its existing shared-memory/lock files; read-only SQL is not a forensic
promise that the SQLite filesystem will never use sidecars.

## Logging and Incident Response

The local server disables HTTP access logs. Storage-health outputs no rows,
credentials or absolute paths and uses generic failure reasons. Keep raw browser
traces, screenshots and database files private; publish only reviewed safe reports.
Central monitoring, persistent log rotation, OS resource quotas and a supervised
worker service remain pending. No background alert service is provisioned.

When health fails, stop new run admission, inspect private storage permissions,
locks, free disk space and the expected environment/version. Do not repair a
versioned schema by guessing missing columns or running an older binary. For a
crashed worker, first verify its process tree is stopped; the explicit
recover-discovery/recover-runs commands handle interrupted persisted work under
their existing lock policy. Do not repeatedly restart a live conflicting worker.

## Backup, Recovery, Rollback and Retention

Follow DEPLOYMENT.md: stop services, acknowledge offline maintenance, create and
verify a backup, then prepare recovery into a fresh inactive directory. Recovery
revokes sessions and cancels active jobs in the copies. Review migration metadata,
checksums, restored project records and login behavior before considering cutover.
The rollback-plan command compares metadata/revisions only and never activates a
release. Actual service cutover/rollback is still pending.

Owned screenshots expire after seven days by default. The operator's
`dashboard prune-evidence --database ... --limit 100` removes a bounded batch of
expired/unknown-age evidence under the existing policy. Reports retain their
execution outcome. Offline backup retention/encryption/key management require an
owner policy; no automatic deletion or upload of backups has been added.

## Demo Publication and CI

PAGES_DEMO.md describes the HTTPS interface and publication workflow. Only built
demo assets are uploaded to Pages. Backend/docs-only pushes do not republish it.
CI separates dashboard/security, UI catalog/isolation and browser integrations
into bounded jobs. Review every job and exact source commit/artifact evidence;
a partial, cancelled or timed-out run is not sprint acceptance.
