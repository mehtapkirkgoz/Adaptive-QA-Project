# Deployment Preparation

Current scope: free local preparation for Sprint 9. There is no deployed public
service, purchased domain/server or enabled production profile. The existing
dashboard remains its accepted loopback-only prototype. Worker destination guards,
read-only admission, deadlines and non-executing plans are unchanged.

## Isolated Environment Plans

```powershell
python -m adaptive_qa deployment plan --environment local --data-root "$((Get-Location).Path)/artifacts/environments" --origin http://127.0.0.1:8765
python -m adaptive_qa deployment plan --environment staging --data-root "$((Get-Location).Path)/artifacts/environments" --origin https://staging.example.test
python -m adaptive_qa deployment plan --environment production --data-root "$((Get-Location).Path)/artifacts/environments" --origin https://qa.example.test
```

These commands print plans only. Each environment gets intended auth/projects
database and backup paths under its own directory. No directory, account,
database, service, DNS record or secret is created. Example hostnames are
placeholders. `activation_enabled=false` is deliberate; secure-cookie and public
origin requirements have not yet been wired into a public server.

The operator must use an absolute local storage root below the filesystem root.
Traversal, UNC/shared roots and existing environment-directory redirection are
rejected. Runtime activation must independently validate concrete database files,
permissions, locks and service configuration; planning alone does not guarantee
filesystem isolation against later administrator changes.

## Offline SQLite Backup Bundles

After stopping the environment's web/worker processes and verifying private
storage permissions, the operator can back up existing environment databases:

```powershell
python -m adaptive_qa deployment backup --environment staging --data-root "$((Get-Location).Path)/artifacts/environments" --origin https://staging.example.test --offline-maintenance
```

The confirmation flag acknowledges operator maintenance; it does not stop or
prove the absence of running services. Both auth.sqlite and projects.sqlite must
already exist as regular, unredirected files. The command never provisions them.
It uses SQLite's backup API, including committed WAL data, checks integrity and
records file lengths/SHA-256 digests in an environment-bound manifest. Concurrent
commits detected during the pair capture invalidate the bundle instead of
publishing it. Still stop services; this check is not distributed coordination.

Each database is limited to 256 MiB and a ten-second progress/verification budget;
hashing is streamed. The bundle is published under a random ID only after both
snapshots pass. Partial bundles are removed. The original databases are retained.
Output contains the bundle ID/environment/count, not records or credentials.

The backup directory uses POSIX mode 0700 where supported; Windows operators
must verify inherited private ACLs. Backups contain sensitive database content
and must never be served as web assets or uploaded as CI artifacts. Checksums
detect corruption, not authenticity, and do not encrypt/sign a backup. Backup
retention and a complete runtime rollback drill are still pending.
No real operator database was backed up during development; verification used
disposable fixtures only.

### Verify Before Planning a Restore

Use the returned bundle ID to verify a private, offline bundle in its original
environment:

```powershell
python -m adaptive_qa deployment verify-backup --environment staging --data-root "$((Get-Location).Path)/artifacts/environments" --origin https://staging.example.test --bundle-id <bundle-id>
```

Replace `<bundle-id>` with the lowercase 32-character ID; the placeholder is not
a literal command argument. Verification requires the exact manifest/database
pair, bounded manifest/file sizes, matching environment and checksums, and SQLite
integrity checks. It rejects duplicate JSON keys, duplicate database entries,
redirected files and extra WAL/SHM files. Snapshots open in read-only immutable
mode; keep the bundle offline and privately controlled while it is checked.
Verification does not restore data, invalidate sessions or change live databases.
The result explicitly reports `restored=false`. Checksums remain corruption checks,
not proof of authenticity or application/schema compatibility. Successful
verification is a prerequisite for a future reviewed restore, not permission to
replace running databases.

### Prepare an Inactive Recovery Pair

After stopping services and checking private storage permissions:

```powershell
python -m adaptive_qa deployment prepare-restore --environment staging --data-root "$((Get-Location).Path)/artifacts/environments" --origin https://staging.example.test --bundle-id <bundle-id> --offline-maintenance
```

Replace the ID placeholder as above. This command verifies the original bundle,
copies its database pair with bounded time/size and digest checks, and publishes
the copies together under `recovery/<recovery-id>` within the same environment.
It never replaces auth.sqlite/projects.sqlite in the live environment. Temporary
copies are removed on failure. A fresh recovery ID is used for every attempt.

Within the copies, existing dashboard sessions are deleted so old session tokens
cannot authenticate. Queued, running and cancel-requested discovery/test runs are
cancelled and their claim tokens cleared. Completed results and project records
remain available. Users must log in again after an eventual reviewed cutover.
SQLite integrity and foreign-key checks must pass before publication. Unexpected
application tables or missing core tables cannot be assumed compatible; required
core columns are checked and triggers/views are rejected. The copied databases
receive only the versioned additive migrations described below. Full
release/schema compatibility review remains required.

`recovery.json` records the source bundle, environment and safety actions without
credentials. The result has `activation_enabled=false`. No service, worker,
queued job or network request starts. The source backup and existing environment
databases remain intact. The recovery directory contains sensitive data and
requires the same private ACLs as backups; do not upload it as a CI artifact.
This demonstrates offline data recovery, not an implemented live cutover,
application release rollback or staging deployment.

### Recovery Schema Revision 1

Migrations execute only inside unpublished recovery copies under the same
bounded SQLite progress handler. Existing live databases and the backup remain
unchanged. SQLite `user_version=0` means the existing unversioned local format;
revision 1 validates required core columns and adds the known optional discovery
report, run claim/results/lineage/contracts/context and evidence-expiry columns
when absent. Existing values are preserved. Reapplying revision 1 adds nothing.

Both copied databases are stamped revision 1. A future/unknown revision is
rejected without a guessed downgrade. A revision-1 database missing a required
column is rejected rather than silently repaired. Recovery metadata records each
database's old/new revisions and added column names. No destructive migration,
in-place upgrade, general SQL migration input or down-migration is supported.
Revision checks currently protect recovery preparation; runtime stores have not
yet adopted a version-gated startup contract. Do not activate a prepared copy or
run an older release against it without a reviewed compatibility check.

## Inactive Release Packaging

From the repository root, run:

```powershell
python scripts/build_release.py
python scripts/check_release.py artifacts/releases/<full-commit-sha>
```

Replace the SHA placeholder with the commit printed by the build. The builder
uses `git archive HEAD`: only committed sources are built, even if the working
tree contains edits. It does not publish working-tree changes, ignored secrets,
databases or test evidence. Commit reviewed changes before building their release.
Build tools download dependencies through pip/npm; no paid service is used.

The bundle contains one Python wheel, compiled dashboard.zip, both dependency
lock files and release.json. The manifest binds each payload's SHA-256/size to
the full source commit and records Python/Node versions. A completed bundle is
published only after successful builds; an existing commit directory is never
overwritten. Build timestamps/tool resolution can vary: byte-for-byte reproducible
builds are not claimed. Checksums are corruption checks, not release signatures.

The verifier checks the exact file set/digests, commit and dashboard ZIP, installs
the wheel into a temporary directory away from the source checkout and invokes
its real status/catalog entry point. All 100 definitions must be present. This
uses the current interpreter's already installed locked runtime dependencies;
it is not a proof of deployment in an empty operating system or container.
Python/Node runtimes, OS libraries, Chromium and controlled fixtures are not
bundled. Browser worker packaging and deployment activation remain unfinished.

CI builds/verifies this bundle separately and retains its commit-named artifact
for seven days. Downloaded artifacts still require digest/commit verification
and owner review before use. No release is activated or deployed by CI.

## Hosting Acceptance Requirements

- Separate staging/production data, accounts, secrets and backup policies.
- Reviewed packaging, immutable release identity and explicit migrations.
- A demonstrated backup restore and rollback procedure before activation.
- Concrete owner-provided domain/server details, TLS/DNS and trusted ingress.
- Secure cookies and strict public-origin/host validation without accepting
  arbitrary forwarded headers or weakening worker destination restrictions.
- Isolated worker execution, network/resource limits and process cleanup.
- Health, privacy-preserving operational logs, monitoring and an operator guide.
- Controlled staging end-to-end evidence and an owner-reviewed release plan.

Purchases remain with the owner. No paid service, external deployment or customer
test is authorized by generating a plan. Follow SPRINT_9.md for implementation
and acceptance; do not mark the sprint complete from these preparation commands.
