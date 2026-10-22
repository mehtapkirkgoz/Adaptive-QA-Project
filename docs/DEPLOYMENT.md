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
detect corruption, not authenticity, and do not encrypt/sign a backup. Retention,
restore, session invalidation and a complete rollback drill are still pending.
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
