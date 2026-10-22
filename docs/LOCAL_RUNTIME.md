# Managed Local Runtime and Rollback

This explicitly activated runtime is limited to the local profile. It never
enables staging/production origins, public interfaces or customer-site execution.
GitHub Pages remains a separate static demo. Existing non-executing deployment
and test-plan commands remain non-executing.

Sprint 10 packages also support membership-scoped local discovery/UI work. The
same discovery-once/run-once role processes one personal job first, then one shared
job if the personal queue is empty. Selected older packages without these modules
do not receive this fallback. Shared membership/configuration, admission/evidence
and recovery checks remain in the selected application, under the existing lease
and worker lock/deadline controls. This does not enable customer-site execution.

## Prerequisites and Trust

Use the locked interpreter dependencies, Chromium and controlled fixture from
SETUP.md. Provision the environment's local auth/projects databases as described
in OPERATIONS.md. Keep its filesystem private. Stop unmanaged legacy dashboard
and worker commands before maintenance; managed leases cannot identify arbitrary
programs that open SQLite directly.

Build an exact reviewed source commit with scripts/build_release.py. The optional
`--commit <40-character-sha>` builds a reviewed historical commit from Git history.
Prepared wheels are pure Python, with fixed application/dist-info contents; UI
and wheel archives have bounded file counts/sizes and reject traversal, symlinks,
duplicate entries and startup hooks. Only reviewed artifacts should be trusted:
checksums detect changes, not authenticity. No pip/npm or network call occurs
during local preparation; dependencies must already be installed.

## Explicit Preparation and Selection

PowerShell example, replacing the candidate directory and commit placeholders:

```powershell
$qaDataRoot = Join-Path (Get-Location).Path 'artifacts/environments'
python -m adaptive_qa deployment local-prepare --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765 --candidate "<absolute-release-directory>" --candidate-commit <full-commit-sha> --offline-maintenance --trusted-release
python -m adaptive_qa deployment local-select --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765 --release-id <full-commit-sha> --offline-maintenance
python -m adaptive_qa deployment local-status --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765
```

Preparation verifies candidate hashes/schema support and extracts into a fresh
`local/runtime/releases/<commit>` directory. It executes no candidate code and
never overwrites a prepared release. Each installed file has a checked inventory;
unexpected/missing/changed files cause refusal. Bytecode writes are disabled in
managed components so package inventories remain stable.

Selection updates one atomic current.json pointer after acquiring exclusive
maintenance locks and checking the existing data/schema. It starts no process.
For subsequent selections, supply `--expected-selection <selection-id>` from the
last local-status result; stale selection IDs are refused. Record the previous
release and data binding before switching. Selection never migrates live stores.

## Bounded Managed Components

```powershell
python -m adaptive_qa deployment local-run --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765 --role serve --duration-seconds 900
```

In separate terminals, after an authenticated user explicitly admits work:

```powershell
python -m adaptive_qa deployment local-run --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765 --role discovery-once --duration-seconds 180
python -m adaptive_qa deployment local-run --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765 --role run-once --duration-seconds 180
```

Each component holds its own OS process lease until it exits. Admission locking
prevents a switch racing component startup. Managed components can coexist, but
duplicate roles and maintenance while any component is active are rejected.
Existing queue worker locks further serialize execution. The stable trusted
launcher can start older reviewed application wheels; application and child
worker imports resolve to the selected wheel, not the editable source checkout.

The HTTP service binds only numeric loopback, disables forwarded headers/access
logs, retains strict Host/Origin and request-size guards and allows 32 concurrent
connections. An `x-adaptive-qa-release` response header identifies the selected
source commit. It is metadata, not authorization. No authentication/data policies
are weakened. Runtime logs contain only component role, release and outcome.
The component outcome describes process completion, not assertion success. Review
persisted run results for passed/failed/skipped/blocked cases. An execution-error
job causes a nonzero managed-component exit; an empty queue can complete normally.

The serve duration defaults to 900 seconds and is capped at 3600. Single-job
components default/cap at 180 seconds; their stricter existing run/case budgets
still apply. On interrupt or deadline, the supervisor terminates its process tree.
Stopped/deadline exits return code 2; successful single-job completion returns 0.
This is bounded local supervision, not an unattended production daemon, container
sandbox or OS memory/CPU quota implementation.

## Restored Data and Binary Rollback

Stop managed components, create/verify an offline backup and prepare recovery as
described in DEPLOYMENT.md. To select the copied data explicitly:

```powershell
python -m adaptive_qa deployment local-select --environment local --data-root "$qaDataRoot" --origin http://127.0.0.1:8765 --release-id <new-release-sha> --recovery-id <recovery-id> --expected-selection <current-selection-id> --offline-maintenance
```

Recovery copies have sessions revoked, active jobs cancelled and known additive
migrations applied. Original live databases and backup bundles are retained.
Review their private permissions and contents before starting a component.

For a binary rollback, stop components and select the previous prepared release
with its current expected-selection ID. By default selection preserves the
current data binding, including recovery data: changing a binary never implicitly
reverts to old live data. `--live-data` is an explicit separate choice, mutually
exclusive with `--recovery-id`. Revisions must match candidate support; unknown
versions do not receive a guessed downgrade. Start the previous release and verify
its header, login, projects and persisted run/evidence. New writes must remain.

## Verified Drill and Remaining Production Work

scripts/check_local_runtime.py uses disposable stores and real built releases to
demonstrate old/live → new/restored → old/restored. It checks active-server switch
refusal, restored session revocation, login, a project created after upgrade,
separate packaged discovery/UI workers, two real assertions and persisted PNGs,
result preservation after binary rollback, lease release and deadline cleanup.
It never tests a customer site. CI repeats this on Linux and Windows and uploads
only a value-free report, never databases, passwords or raw runtime directories.

Public backend TLS, production service management, OS quotas, central alerts and
secret/backup infrastructure require a separate reviewed hosting decision. They
are deferred under the owner's current Pages-demo/local-automation scope, and
must not be described as demonstrated by this local drill.
