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

## Required Before Hosting

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
