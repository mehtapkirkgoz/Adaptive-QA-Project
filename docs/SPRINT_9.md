# Sprint 9 — Custom Domain and Deployment

Started: 2026-10-22
Status: In progress; explicitly started by the owner.
Tracking: [issue #10](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/10)
Milestone: [#10](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/10)

Sprint 8 issue #9 and milestone #9 are verified closed. Its documentation commit
59a4abf also passed CI. The owner has not purchased a domain or server. Continue
free local preparation; do not buy services or activate external hosting.

## Delivery Steps

- [x] 9.1: Add validated, non-executing local/staging/production environment plans.
- [ ] 9.2: Package services and wire environment-specific runtime configuration.
- [ ] 9.3: Implement and demonstrate migration, backup, restoration and rollback.
- [ ] 9.4: Verify worker isolation, network/resource limits and deployment boundaries.
- [ ] 9.5: Add operational health/monitoring/logging and an operations guide.
- [ ] 9.6: Configure reviewed domain/DNS/HTTPS and controlled staging activation.
- [ ] 9.7: Verify staging end-to-end acceptance, restore/rollback and exact-commit CI.

The owner manages closure and any Sprint 10 start. Deployment activation needs
concrete infrastructure/hostname details and owner authorization; paid purchases
and customer targets remain unauthorized.

## First Increment: Environment Plans

`adaptive-qa deployment plan` validates a profile and prints its intended paths
and requirements. It does not create files, resolve secrets, provision accounts,
start services, change DNS or contact the network. Environment data paths are
separate children of an explicit absolute local root. Traversal, shared UNC roots,
filesystem-root storage and existing environment symlink redirection are rejected.

Local origins require numeric loopback HTTP and an explicit unprivileged port.
Staging/production plans require a DNS hostname with HTTPS/443; credentials,
application paths, wildcards, queries, fragments and ambiguous input are rejected.
The output records secure-cookie requirements but does not apply them to the
existing loopback dashboard. `activation_enabled` is always false. Runtime wiring
and HTTPS serving remain unfinished; a valid plan is not a deployment.

Example in the repository PowerShell terminal:

```powershell
python -m adaptive_qa deployment plan --environment staging --data-root "$((Get-Location).Path)/artifacts/environments" --origin https://staging.example.test
```

The example hostname is a placeholder. It is not contacted or registered. See
DEPLOYMENT.md for the deployment contract and current limitations.

Validation: 540 unit tests completed locally with 539 passing and one skipped
because this Windows account cannot create the symlink fixture. The other five
new environment/CLI tests passed; Linux CI will exercise the real symlink check.
Commit 49e5f5e passed CI run 39757636731. Domain, runtime HTTPS and hosting acceptance are
not complete.

## Offline Backup Increment

Added the operator-only deployment backup command for an already populated
environment. It requires explicit offline-maintenance acknowledgement, uses
SQLite snapshots rather than raw copying, includes committed WAL records,
checks integrity/digests and detects concurrent commits before publication.
Backups are bounded to 256 MiB and ten seconds per database and published only
as a complete pair. Source databases are not replaced or provisioned.

Seven focused tests verify real snapshot records/checksums, source preservation,
missing/corrupt databases, maintenance acknowledgement, WAL commits, deadline
cleanup and concurrent-commit rejection. Restore and rollback remain unfinished,
so step 9.3 is not complete. Docker CLI is installed but its Linux daemon is not
running; no container build or staging deployment has been claimed or activated.

Local regression validation: 547 tests completed, 546 passed and the Windows
symlink-permission fixture was skipped. Backup-specific tests all passed.
Same-commit backup CI evidence remains pending after push.
