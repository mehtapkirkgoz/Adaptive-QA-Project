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
- [x] 9.6a: Publish and verify the owner-approved HTTPS interface demo on GitHub Pages.
- [ ] 9.6b: Review backend staging activation; custom domain deferred by the owner.
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

## Read-only Backup Verification

Added `deployment verify-backup` with environment/format binding, bounded manifest
parsing, duplicate-key/file rejection, streaming checksums and SQLite integrity
checks. It opens immutable offline snapshots, creates no SQLite sidecars and
does not restore or replace live databases. Seven focused tests exercise the CLI
against changed live records, tampered snapshots, checksum-valid corrupt SQLite,
wrong environments, malformed manifests, traversal, deadlines and missing files.
Backup/verification tests also run in the existing Linux/Windows lifecycle jobs.
Restore, session invalidation and rollback are still unfinished; 9.3 stays open.

Local verification regression: 554 tests completed (553 passed, one Windows
symlink-permission skip). Dependency compatibility and Python compilation passed.
Exact-commit verification CI is pending after push.

## Inactive Recovery Preparation

`deployment prepare-restore` verifies and copies an offline bundle into a fresh
private recovery directory. It never replaces the live pair or activates services.
Copies have old sessions removed and active discovery/test work cancelled with
claim tokens cleared. Completed results remain unchanged. Digest, integrity,
foreign-key, size/time and core-table checks precede atomic pair publication;
failed attempts remove partial recovery files. No schema upgrades are performed.

Four recovery tests use real application stores to verify restored project data,
login after session revocation, cancellation of active work, preservation of
completed work, unchanged source/live bytes, distinct recovery IDs, CLI wiring,
maintenance acknowledgement, unsupported-schema rejection and deadline cleanup.
All 18 backup-related tests passed locally. This is an offline recovery drill;
runtime cutover, migrations and release rollback remain unfinished, so 9.3 is
still open. Domain/hosting requirements remain blocked on owner infrastructure.

Recovery regression validation: 558 tests completed locally, with 557 passing and
one Windows symlink-permission skip. Same-commit recovery CI remains pending.

## Inactive Release Packaging

Added committed-source release builds: a Python wheel, compiled dashboard ZIP,
dependency lock files and SHA-256/size manifest bound to the full source commit.
Only `git archive HEAD` sources are built; ignored data/secrets and working-tree
edits are excluded. Completed bundles are not overwritten and never activate
services. CI has a separate packaging/install-verification job and retains the
commit-named bundle for seven days.

A real local build from 63f8fa7 compiled TypeScript/Vite and built/installed the
wheel into a temporary directory outside the source checkout. Its installed
status command verified all 100 definitions (51 UI / 34 API / 15 database).
All four payload digests were verified. This uses existing locked interpreter
dependencies; empty-OS/container installation, fixtures, Chromium, runtime
configuration and public serving remain unfinished, so 9.2 remains open.

Packaging regression: 561 tests completed (560 passed, one Windows permission
skip), including three pre-installation tamper/commit/file-set rejection tests.
The real local build/install check passed; packaging CI is pending after push.
Backup commit 7aaf817 passed CI run 39783349779.

## Versioned Recovery-copy Migrations

Inactive recovery now validates required core columns and adopts SQLite schema
revision 1. Existing unversioned copies receive only known additive discovery,
run and evidence columns. Existing rows are retained; reapplying revision 1 is
idempotent. Unknown/future versions refuse downgrade, and inconsistent versioned
schemas are rejected instead of silently repaired. Migration metadata is stored
in recovery.json. All changes occur before publishing the copied pair; live
databases and backup snapshots remain unchanged.

Four real-SQLite migration tests and the four recovery tests passed locally.
Linux/Windows CI exercises both suites. Runtime startup/version gating, cutover,
release rollback and staging acceptance remain unfinished; 9.3 remains open.

Migration regression: 565 tests completed locally (564 passed, one Windows
permission skip). Recovery implementation 63f8fa7 passed CI run 39784224509.
Packaging job in run 39785109938 passed for 0536b63; its downloaded artifact
12428842277 had its archive digest/head verified and all four payloads checked.
The downloaded wheel installed outside the checkout and exposed all 100 cases.
See evidence/sprint9-release.json. The overall packaging run was still pending
at that artifact review; no full-run or staging acceptance is inferred.

## Runtime Schema Gates

Authentication and project stores validate schema revisions on each connection
before initialization or operations. Unsupported revisions stop without DDL or
application writes; revision 1 requires all core/additive columns and real
tables. Inconsistent versioned schemas are not silently repaired. Unversioned
local initialization is preserved without automatically marking it migrated.

Five real-SQLite tests verify byte-identical rejection of future auth/project
files, a revision changed after store construction, inconsistent queue schema,
valid revision-1 stores and unchanged legacy revision markers. Four recovery
tests also passed. Linux/Windows CI now runs the runtime gate tests explicitly.
This does not implement runtime cutover or establish older-release compatibility.

Packaging commit 0536b63 passed the complete eight-job CI run 39785109938.
Runtime gate regression: 570 tests completed locally (569 passed, one Windows
symlink-permission skip). Same-commit runtime CI is pending after push.

## Rollback Candidate Compatibility Preparation

Added schema support declarations to release manifests and future-schema probes
against the externally installed wheel. `deployment rollback-plan` verifies a
candidate's exact commit/payloads and compares its declared support with both
offline database revision markers. Missing declarations or unsupported versions
are not guessed compatible. The plan is read-only and non-executing; it never
installs/imports candidates, changes a release pointer or activates services.

Four tests cover CLI non-execution/unchanged bytes, missing/mismatched support,
tampering/wrong identity and offline/checkpoint requirements. A real a71bc2c
bundle was rebuilt with the new builder, installed outside the checkout and
passed both future-schema runtime probes and its 100-case catalog check. An
offline drill with that bundle matched revision 1, rejected a future revision
and preserved the matched database bytes. CI repeats the drill and retains safe
JSON evidence. These checks do not demonstrate actual service cutover/rollback;
9.3 and staging acceptance remain open.

Local regression: 574 tests completed (573 passed, one Windows permission skip).
The final bounded-file checks also passed the four focused rollback tests.
Same-commit compatibility-plan CI remains pending after push.

## Owner Scope Update: GitHub-hosted Interface Demo

The owner deferred a custom domain and selected a public GitHub Pages interface
demo with real automation remaining local. After the private repository's Pages
settings required an upgrade/public visibility, the owner explicitly authorized
making the entire repository public. No paid upgrade or backend hosting is
authorized. Runtime/operations/rollback work remains required; a static demo does
not establish staging backend acceptance.

Implemented a separate demo build with overview, sample site categories, the
accepted 100-definition catalog with search/layer filters and a clearly synthetic
report. It performs no API/network target requests and persists nothing. Normal
local sign-in/project/run behavior remains in the default build. The stale
Sprint 07 UI badge was replaced with Local Workspace.

Real browser verification under /Adaptive-QA-Project/ passed at 390/768/1440
widths, including catalog counts/search/empty state, example report labeling,
reload and sample-project selection, with zero API/external requests or page
errors. Both TypeScript/Vite builds passed. Desktop/mobile screenshots and safe
browser report are in ignored artifacts/demo. Publication workflow is manual and
uploads only frontend/dist-demo. See PAGES_DEMO.md. Publication/URL verification
is pending until the workflow and Pages settings are applied.

Repository visibility was changed to public and verified in GitHub Settings at
the owner's explicit request. Local unit regression completed: 574 tests, 573
passing and one Windows symlink-permission skip. The real demo browser checks
and both production/demo frontend builds passed.

Previous implementation 4db5e1e passed CI run 39786903454; runtime a71bc2c also
passed CI run 39786355350. Earlier 6e28abb run 39785596059 was cancelled; it is
not claimed as successful evidence. Later accepted CI includes those changes.

The first demo implementation's core CI run 39788675051 passed its demo/UI
checks but the long browser job reached its 15-minute limit during later UI
isolation checks. It is recorded as cancelled, not accepted. Pages source was
saved as GitHub Actions after the owner-authorized public visibility change.
Added a main/frontend-scoped push trigger to register/bootstrap the Pages
workflow and keep future demo-only changes publishable without backend hosting.

Split the previous monolithic browser CI job into dashboard/security, UI
catalog/isolation and browser integrations. Each retains its 15-minute job limit,
all previous scripts and unchanged runtime child deadlines/target policies.
Independent jobs no longer spend a shared browser budget. Evidence is retained
under separate artifact names; no check or scenario was removed. Full same-commit
CI remains required before acceptance.

## Live Demo Verification

Pages deployment run 39825476044 succeeded for commit
3bd37092fef9c22920120e2696e2a3da5a5d8547. GitHub Settings displayed the live
HTTPS URL https://mehtapkirkgoz.github.io/Adaptive-QA-Project/ and enforced HTTPS.
The live page was opened in the owner's right-side browser panel.

`check_live_demo.py` contacts only that explicitly authorized public demo. It
verified HTTP 200 over HTTPS, all 100 catalog definitions, the 34-case API filter,
synthetic report labels and mobile width, with zero API/external requests or page
errors. The test engine was not executed. Safe live report and desktop/mobile
screenshots are in artifacts/demo. See evidence/sprint9-pages.json. This verifies
the static UI publication, not an online Python/worker runtime or Sprint 9 closure.

## Local Storage Health and Operations

Added the operator-only `deployment storage-health` command with fixed-path,
size, revision/core-column, integrity and foreign-key checks. It never provisions
missing stores or outputs records, credentials or absolute local paths. Read-only
connections use a one-second lock wait and a two-second progress budget per
database. Exit 0 means database storage ready; exit 2 means unavailable. It does
not claim web/worker/Chromium or deployment readiness.

Six tests passed for safe ready output/unchanged database bytes, missing-file
non-provisioning and CLI exit, future/corrupt stores, shared hardlinks, deadlines
and exclusive-lock handling. Linux/Windows CI includes these checks. OPERATIONS.md
documents local startup, explicit worker invocations, privacy, failure response,
backup/recovery/rollback boundaries and retention. Central monitoring, service
supervision, resource quotas and actual cutover/rollback remain pending.

Storage/operations regression: 580 tests completed locally (579 passed, one
Windows symlink-permission skip). Same-commit CI remains pending after push.
