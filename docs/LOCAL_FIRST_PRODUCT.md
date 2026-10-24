# Local-First Product Conversion

Owner authorization: 2026-10-23. Preserve the working engine and existing local
sessions while delivering a narrow single-device edition first. Sprint 10 remains
closed; this is product conversion work, not a reopened sprint. The prior rough
completion percentage is not a measured estimate for this changed scope.

## Target Model

- Free: no registered account; one active local site/project.
- Paid: a verified signed license unlocks multiple local projects; licensed local
  administration uses existing authentication rather than a customer-controlled ID
  as an authentication secret.
- Discovery, browser/API/database execution, targets, credentials, screenshots and
  reports stay in the customer environment. The central licensing boundary must
  never ingest those records or resolve the customer's target credentials.
- Future central services may retain account/password hashes, customer/license IDs
  and entitlement validity only. No central service or payment system is activated
  by this conversion. Initial offline license issuance/verification is acceptable.
- Multiple sites does not remove concurrent browser, queue, process or memory bounds.
- A user controlling the local files/runtime can bypass a free local cap. Do not
  claim an unbreakable offline or one-site-lifetime restriction.

## Delivery Sequence

- [x] Define the local/central boundary and retain legacy local authentication.
- [x] Add opt-in account-free local composition with ephemeral browser sessions,
  unchanged Host/Origin/CSRF guards and no account/password database creation.
- [x] Enforce one free local project transactionally and show the free edition UI;
  prove restart persistence, concurrent creation and real local execution.
- [x] Add typed signed-license claims, explicit trusted public keys, expiry and
  verification; no issuer private key or developer bypass shipped to customers.
- [x] Bind paid administration and multi-project entitlements to verified licenses;
  preserve existing local projects during upgrade and define safe expiry behavior.
- [x] Add customer-facing local commands and license import/status UX, plus
  packaged release/recovery checks; legacy managed licensed switching fails closed.
- [x] Verify free/paid isolation, malformed/expired/tampered licenses, concurrency,
  data locality and complete local acceptance with exact-commit CI/artifacts.
- [ ] Resume the remaining interactive/API/database product work under this model.

## First Free Edition Increment

Start a separate free workspace after building the React UI:

```powershell
python -m adaptive_qa dashboard free-serve --port 8766
```

Default local storage is artifacts/local-free/projects.sqlite. Existing account
mode and its database/port are not changed. The free UI opens directly without
registration, hides account/organization actions and disables creating a second
project. The server also checks capacity under BEGIN IMMEDIATE, so concurrent
creation cannot bypass the one-project cap. Changing the one saved target is
permitted: this is one active project, not a lifetime single-domain license.

Browser session/CSRF tokens are generated in memory, bounded to sixteen sessions
with eight-hour expiry. They are not registered accounts and disappear on server
restart; project data persists under the internal local identity. The account-free
app remains loopback-only and retains the existing HTTP request/egress guards.
No license endpoint, telemetry or external account service is called. Local
worker commands continue to process this local project database explicitly.

Verification: unit tests cover no-account bootstrap, missing CSRF, foreign Origin,
project persistence, one winner under concurrent creation and session expiry.
check_local_free.py verifies the built browser UI plus actual controlled local
discovery/LOGIN-001 execution, no auth.sqlite/dashboard_users creation, no central
requests and no script errors. These checks do not claim licensing is implemented.
The existing development account mode remains a compatibility path; customer
licensing enforcement and packaging are unfinished until the later milestones.

Local regression completed 706 tests (705 passed, one Windows permission skip).
The free browser execution, legacy authenticated browser flow and static demo
checks passed. Cross-site bootstrap refusal and expiry checks also passed after
the final session guard change. Exact-commit CI is pending after push.

## Offline License Verification Foundation

Ed25519 signatures verify a versioned, strictly typed entitlement payload against
explicit caller-supplied trusted public keys. The signed message binds the key ID
and canonical payload to this product. Unknown keys, modified payloads, duplicate
JSON fields, oversized documents, unsupported claims and invalid validity windows
fail closed with a generic error. Expiry is exclusive; no grace is inferred.

Claims contain customer/license IDs, validity and project/concurrent-run limits
only. They cannot carry target URLs, credentials or test records. Verification
uses no network and ships no issuer private key or production trust anchor. Tests
use ephemeral signing keys. The pinned cryptography dependency supplies Ed25519.
Offline verification depends on the local clock; immediate remote revocation and
tamper-proof offline enforcement are not provided.

This foundation does not yet unlock paid projects. Licensed authentication,
transactional admission/worker enforcement, import UX and packaging remain open.
The full regression completed 711 tests (710 passed, one Windows permission skip);
five focused licensing tests also cover tampering, issuer trust, malformed signed
claims, bounded parsing and exact validity boundaries. The timestamp bound was
then hardened and the focused tests repeated. Dependency checks passed.

Previous free-edition commit 6f10a1d passed Pages and eleven Core jobs; the UI
catalog job failed because its new free-workspace check had no frontend build.
This increment adds the locked Node install/build before that check and uploads
its value-free report. Exact-commit CI is pending after push.

## Local License Persistence Increment

LicenseStore keeps one bounded signed document in a separate local SQLite file.
Imports verify inside a write transaction; invalid imports leave the prior license
intact. Each read verifies the signature and current validity again, so a cached
startup decision cannot extend an expired license. Expired documents remain on
disk for diagnosis/replacement and do not grant entitlements. Trusted public keys
are supplied separately by the application composition and copied at construction;
imported documents never establish issuer trust. No production key is shipped.

Four persistence checks verify restart/expiry behavior, rejected replacement and
local tampering, trust separation and eight concurrent imports yielding one whole
signed record. The five verifier tests also passed. This is internal persistence,
not yet an exposed import endpoint or paid-mode activation. Project/run admission
and worker enforcement remain unfinished; existing free/account behavior is intact.

Commit 3357c70 passed Core checks in run 40005490997, including the corrected
free-interface build and execution step. Exact-commit CI for this persistence
increment is pending after push.

## Licensed Workspace Integration

An explicitly provisioned password administrator maps to the same internal local
workspace identity as the free edition. Other valid accounts cannot inherit that
workspace. Password hashing, opaque sessions, CSRF and login throttling reuse the
existing authentication implementation. No customer ID is accepted as a password.
The internal licensed app composition omits organization routes for this narrow
single-device edition. No customer-facing licensed startup command is shipped yet.

Licensed project creation checks the current signed limit inside the project
database write transaction. Concurrent creation respects the cap. Upgrading leaves
existing project IDs/ownership intact; expiry or a reduced limit preserves readable
projects and history but refuses further licensed creation. No data is deleted.

Personal discovery/run admission and worker claims recheck the license. Claims
share a transactional concurrent execution count across both queues, capped by the
signed entitlement (at most four). Expired licenses leave queued work unclaimed;
active workers observe cancellation through their existing polling/deadline path.
Running work is stopped cooperatively, not at an impossible instantaneous expiry
boundary. Existing independent process deadlines remain in force. Authentication
remains available after expiry for reading local records.

These hooks apply when workers use LicensedLocalProjects. Customer CLI/runtime
composition must still ensure every customer worker selects that store rather
than the legacy development store; therefore commercial enforcement/packaging is
not declared complete. Import/status UX and backup/rollback compatibility remain
unfinished. Existing development and free compositions retain prior behavior.

Verification: the full regression completed 719 tests (718 passed, one Windows
permission skip). Five licensed integration checks passed after the final changes,
including password/CSRF-protected HTTP upgrade, expiry-preserved reads, parallel
creation, reduced limits and shared discovery/run worker capacity. Expiry polling
records cancel_requested so finalization cannot report an empty successful run.
Affected dashboard queue/worker tests were repeated after this change. Exact-commit
CI is pending after push.

## Customer Command Increment

The local command group now provides interactive administrator provisioning,
bounded signed-license import/status, authenticated loopback serving and dedicated
licensed discovery/run workers. See [licensed startup](LOCAL_LICENSED_SETUP.md).
Worker commands construct LicensedLocalProjects directly and do not fall back to
organization/development queues. Trust files reject duplicate/oversized input and
remain separate from imported licenses. No issuer service or signing key is created.

All 43 local-edition/runtime tests passed, including four command checks for
no-network import/status, safe replacement, strict trust files, loopback startup
and licensed worker composition. Six legacy dashboard CLI tests also passed.
These tests do not yet demonstrate packaged licensed browser execution or graphical
license management. Those acceptance and packaging tasks remain open. Exact-commit
CI is pending after push; prior c57a2c0 was still running when inspected.

## Graphical Local License Management

The authenticated licensed workspace now shows current license status, project and
concurrent-run limits, expiry and a signed-document import form. The server exposes
license routes only for the licensed composition. Reads require the designated
administrator session; imports also require the existing Origin and CSRF checks.
No public key, customer ID or test record is returned. Invalid imports preserve
the previously installed document. Status refreshes every thirty seconds; worker
and admission checks still verify current validity independently of UI status.

A real built-interface browser check on an owned temporary loopback server passed:
password login, preserved free project, absent status, valid import, invalid import
rejection and authenticated reload. It observed zero external requests/page errors.
The existing free UI/discovery/browser execution also passed unchanged. Eight
focused free/licensed HTTP tests passed, including unauthenticated/CSRF/foreign
Origin rejection, exact expiry and license routes absent in free mode. The new
browser check runs in CI and uploads a value-free report. Customer packaging and
licensed execution acceptance remain open; exact-commit CI is pending after push.

## Packaged Foundation and Licensed Execution Proof

The release verifier now installs the committed wheel outside the checkout and
checks local command parsing, ephemeral signed-license validation, preserved free
project ownership, multi-project access and expired-license rejection without data
deletion. This extended check passed against committed release 25d64e4; the bundle
stayed inactive and retained the 100-case catalog. CI repeats it for the next exact
commit. This is not an installer or complete customer binary rollback acceptance.

The licensed browser check now also saves a controlled loopback target, queues
discovery and executes LOGIN-001 through separate actual local CLI worker
processes. The result passed and the authenticated reload retained the license.
The browser observed no external requests or page errors.

Two compatibility guards prevent silent loss/bypass: the old auth/project-pair
backup refuses workspaces containing license.sqlite, and managed legacy runtime
data selection refuses those workspaces because its worker composition does not
enforce licensing. The dedicated local licensed commands remain available.
Nineteen backup/runtime tests passed. A complete edition-aware backup/restore path
is still required; refusing an incomplete old backup is not backup completion.

## Edition-Aware Offline Backup and Recovery

The local backup/restore commands snapshot the project database plus authentication
and signed-license databases when present, using the SQLite backup API. Free-only
workspaces remain account-free. Operations require explicit offline-maintenance
confirmation, bounded regular files, integrity/checksum validation and a fresh
publication directory. Concurrent writes/file-set changes reject publication.
Snapshots do not contain issuer trust files or environment-variable secret values.

Recovery never overwrites the live workspace or activates a runtime. It preserves
project IDs/results/evidence and the raw signed document, invalidates sessions,
cancels pending work/leases and revokes restored agent credentials. License checks
remain external to recovery: current time and separately configured publisher keys
are required again, so restoring does not renew a license. Snapshot contents are
private and unencrypted; protect them with customer-controlled storage.

Five recovery checks cover free/paid file sets, session/queue sanitization, original
license expiry, tampering, existing destinations and writes during backup. CLI
backup/restore also passed. Free server startup now refuses an existing licensing
state file instead of silently reopening a licensed workspace without its policy.
The dedicated licensed server still permits authenticated reads after expiry.

Commit 25d64e4 passed both Core and Pages CI. General regression completed 730 tests (729 passed, one Windows permission
skip). All 51 local-edition/runtime checks passed after final changes;
exact-commit CI will follow push. Managed licensed binary switching
and a complete packaged recovery/browser drill remain unfinished.

## Offline Publisher Tooling and Package Recovery Evidence

The publisher-only script issue_local_license.py can explicitly generate an issuer
key pair outside the repo and sign strictly typed customer entitlement documents.
It is excluded from the customer wheel, refuses overwriting outputs and never
prints private signing material. See OFFLINE_LICENSE_ISSUANCE.md for protected
key storage and customer delivery. No real issuer key/customer license was created;
tests use ephemeral keys and observed no network access. Two issuance tests passed
for verification roundtrip, output preservation, invalid claims and repo refusal.
No billing/account service or unbreakable offline enforcement is claimed.

Committed release fc137f6 was built and installed outside the checkout. Its
extended release check passed signed entitlement/expiry validation, ownership
preservation and edition-aware free backup/recovery; all four bundle files and
the 100-case installed catalog were verified. The release remained inactive.
Current CI must still supply exact-commit remote acceptance before marking the
conversion accepted. Managed licensed binary switching remains unavailable and
refuses licensed data; supported manual package/local-command recovery does not
claim that legacy managed switching supports it.

## Consolidated Local Conversion Checkpoint

Implementation 1c3704c passed the final 735-test regression (734 passed, one Windows
permission skip), both real browser/CLI fixture flows and installed-wheel checks
outside the checkout. Local evidence/digests and remaining limits are recorded in
LOCAL_FIRST_ACCEPTANCE.md and evidence/local-first-1c3704c.json. This does not mark
remote CI/artifact acceptance or overall product acceptance complete. Continue the
remaining packaged paid recovery drill and licensed runtime compatibility work,
then verify exact-commit CI/artifacts before resuming broader execution expansion.

## Installed Paid Recovery Follow-Up

Release 67f6f85 passed the installed-wheel licensed browser/CLI drill outside the
checkout, followed by stopped-workspace snapshot/recovery, invalidated old browser
session, fresh password login and preserved license/results. Source and installed
server/worker flows passed. Evidence is in LOCAL_FIRST_ACCEPTANCE.md and
evidence/installed-licensed-recovery-67f6f85.json. CI now repeats this installed
drill in the UI job and includes its report in local-license artifacts.

The customer local command path now has free/paid startup, import/status, signed
entitlement enforcement, actual controlled execution and offline recovery checks.
Managed legacy binary switching stays unsupported and fails closed for licensing
state. Next required acceptance work is exact-commit CI/artifact inspection, not
a claim that legacy management or customer deployment was enabled. Keep overall
product acceptance pending and continue the remaining authorized work afterward.

## Remote Conversion Acceptance Verified

Implementation 799e390 passed all twelve CI jobs in run 40018710391 and 739 unit
tests. All twelve artifact downloads/head SHAs/digests, 206 PNGs and inner release
digests were verified. Installed licensed execution/recovery evidence passed. See
LOCAL_FIRST_ACCEPTANCE.md and evidence/local-first-ci-799e390.json. Overall product
acceptance remains pending; unsupported legacy managed licensed switching remains
explicit. Continue the remaining controlled interactive form implementation in
INTERACTIVE_FORMS.md, then broader reusable execution work. Existing public/customer
submission restrictions and non-executing plans remain authoritative.

Controlled interactive follow-up now includes scoped saved review, transactional
queue/licensing/cancellation, mapped-input child execution, explicit local operator
confirmation and real local UI controls for four owned fixtures. See the latest
INTERACTIVE_FORMS.md checkpoints. General-site interactive submission and overall
product acceptance remain pending; the public demo remains non-executing.

Reusable owned-loopback endpoint/field/boolean-response bindings now reach saved
configuration, explicit owner review/confirmation and supervised queue workers.
The corresponding local UI editor now supports explicit saved review and confirmed execution on owned fixtures. See the latest
INTERACTIVE_FORMS.md checkpoints; general HTTPS remains read-only.

Reusable local UI-to-worker execution has passed for positive login and negative
search, including unsaved-edit guards, removal and mobile layout. Next verify the
combined exact-commit CI artifacts and remaining product limits. General HTTPS
remains read-only; overall owner acceptance remains pending.

The licensed operator can now use `local worker-cycle` for one bounded pass over
discovery, read-only runs and confirmed interactive jobs. Existing per-queue
workers retain licensing, cancellation and deadline checks; no background service,
job admission, automatic recovery or retry is introduced. Eight local CLI tests
passed, including empty unlicensed queues and fail-stop behavior. Exact-commit
CI for this increment remains pending push.

Free mode now offers the same bounded pass without an account:

```powershell
python -m adaptive_qa dashboard free-worker-cycle --database artifacts/local-free/projects.sqlite
```

This uses the free project store, creates no authentication database and refuses
an existing licensing-state marker. Use `local worker-cycle` after upgrading the
workspace to paid mode. Both commands share the same three existing workers;
neither admits new jobs, retries interrupted submissions or installs a service.
The CLI checks passed for account-free empty queues and refusal of licensed state.

The combined reusable form/editor checkpoint ae36b32 now has complete remote
evidence: Core run 40083889591 passed all twelve jobs; twelve artifact digests,
210 PNGs and four inner release digests were verified. See
evidence/reusable-ci-ae36b32.json. Later worker-cycle CI remains separate; overall
owner acceptance and general-site interactive support are still pending.

The reusable editor browser drill now invokes the actual account-free worker-cycle
CLI in a separate process instead of calling its interactive worker directly.
Positive login and negative search both passed through saved UI configuration,
explicit confirmation, CLI dispatch, supervised browser execution and refreshed
persisted results. Empty discovery/run queues remained empty. Only two owned
documents and two submissions were observed, with no malformed/external request
or UI error. CI runs the same proof; no owner session was restarted.

The interactive panel now includes expandable worker startup guidance with the
correct free or licensed command, explicit example-path replacement and saved
environment variable names only. It explains why queued jobs wait and why unknown
submissions are not retried. Opening guidance never starts work or resolves values.
The real UI/CLI/browser proof and production/demo builds passed after this change;
the existing owner server was not restarted.

Both free and licensed browser acceptance drills now execute actual discovery and
LOGIN-001 runs through the bounded CLI cycle as separate processes. Each drill
verifies the other queues remain idle. Free mode still creates no account store;
paid mode still verifies upgrade preservation, signed import, password login and
offline recovery with a fresh session. Both source drills passed with zero external
requests or page errors. CI will repeat the paid drill against its installed wheel;
this local source run does not replace that packaged evidence.

Remaining API work now has an internal explicit read-only review/confirmation path
for contrasting owned loopback endpoints, separate from the example catalog.
Three contract checks and a real isolated HTTP proof passed: two declared passes,
one declared failure, exactly three GET requests and none during review, stale
dispatch or pre-cancellation. See LOCAL_API_EXECUTION.md for the remaining saved
settings/queue/UI work. This is not customer-facing API admission or catalog growth.

The explicit local API binding can now be saved with the project and reviewed via
an owner-scoped, session/Origin/CSRF-protected local endpoint. Review remains
non-executing; changed full saved settings invalidate its digest. Existing UI saves
preserve the metadata, while invalid replacements leave prior settings intact.
Three real persistence/HTTP checks and six existing settings checks passed.
Next connect transactional licensed queue admission and operator UI confirmation;
no saved API execution route or additional catalog case is enabled by this step.

Internal saved API dispatch now has transactional confirmed admission, current
settings/license/capacity checks, claim tokens, cancellation, no-retry finalization
and offline-recovery cleanup. Two saved explicit endpoints passed through the real
supervised API worker. Six queue checks passed, including signed expiry and shared
running capacity. Public review remains non-executing; customer CLI/HTTP admission
and operator UI are not enabled yet. See LOCAL_API_EXECUTION.md.

Saved API jobs now have local scoped HTTP admission/history/cancellation and
separate free/licensed one-shot CLI workers/recovery. Sixteen HTTP/CLI checks and
the real saved-configuration -> reviewed confirmation -> HTTP queue -> CLI child
proof passed on owned endpoints. Review still grants no execution authority by
itself. The three-queue worker cycle is unchanged; API has its own explicit command.
Next add the operator editor/review/confirmation UI; public/customer API targets
and authentication are still outside the enabled profile.

The real local configuration form now edits the explicit API binding without
request values or credentials. Save/reload/preserve/remove passed in the free
browser drill, with zero API jobs created, external requests or page errors.
Draft API edits participate in unsaved-change protection. Production/demo builds
passed and the public demo stays non-executing. Next add API review/confirmation/
history UI; no public/customer API profile is enabled.

Saved API review/confirmation/history/cancellation controls now reach the real
local dashboard. The free UI -> HTTP confirmation -> queue -> separate CLI worker
-> refreshed passing result proof passed, with one actual GET and a second job
cancelled before execution. Unsaved edits invalidate confirmation; mobile layout
was checked visually. Production/demo builds passed. Remaining acceptance is exact-
commit remote evidence and paid/installed operator integration; public/customer
API targets and authentication remain outside this enabled profile.

Licensed operator integration passed the API editor -> explicit confirmation ->
licensed CLI -> visible result flow against an expected-false local fixture, then
preserved the binding/result through offline recovery and fresh administrator login.
Exactly one GET and no external browser requests/page errors were observed. The
installed-wheel acceptance script now requires this proof; packaged and exact-
commit remote evidence remain next.

Release 3091a81 passed the installed licensed API operator/recovery drill outside
the source checkout, with the four release digests verified, one owned GET, zero
external browser requests/page errors and preserved API binding/result after
fresh login to recovered storage. The full 814-test local regression passed with
one Windows permission skip. See evidence/installed-api-3091a81.json. Continue
exact-commit remote acceptance before declaring this API checkpoint accepted;
general public/customer API authentication remains unimplemented.

Remote API checkpoint 3091a81 now has ten successful completed jobs and ten
downloaded/verified exact-head artifact archives, 63 validated PNGs and four inner
release digests. Its saved API HTTP-to-CLI proof passed remotely. Windows packaged
runtime and UI catalog/isolation were still running; do not mark remote acceptance
complete until those jobs and their artifacts are verified. See
evidence/api-ci-3091a81.json for this partial checkpoint.

Run 40105056865 finished with eleven passing jobs and one Windows installed-check
timeout at 30 seconds. All twelve artifact archives/210 PNGs/four release digests
are verified; free/paid/installed API UI evidence passed. Remote acceptance remains
failed, not complete. The packaging-only combined verification now has stage logs
and a bounded 120-second budget; target-test deadlines are unchanged. Continue
fresh installed/CI acceptance and investigate the logged stage if it fails again.

Fresh release f62882c passed installed validation locally after the packaging
budget/diagnostics change. Stage logs completed the combined check in 2.13 seconds;
the installed licensed API UI/CLI and offline recovery proof also passed, with one
GET, zero external browser requests/page errors and all four bundle digests checked.
See evidence/installed-api-f62882c.json. This does not explain the old Windows CI
stall or establish remote success: verify f62882c's exact-commit CI/artifacts next.

Controlled API operator acceptance is now verified at 68af26a / Core run
40105470724: twelve successful jobs, 814 scaffold tests, twelve artifact digests,
210 PNGs and four inner release digests. Free UI confirmation/cancellation and
installed licensed API execution/recovery passed remotely. See
evidence/api-ci-68af26a.json. The older failed 3091a81 run remains recorded; the
separate f62882c packaging-diagnostics adjustment still needs remote verification.
Continue remaining bounded database product integration under the local-first
model while preserving those acceptance boundaries. Customer/public API auth and
overall owner acceptance remain unfinished; do not expand execution scope silently.

The first reusable database profile now reviews an explicit application table and
expected record count on owned SQLite fixtures. It generates count-only SQL,
binds the private root identity/current configuration to confirmation and uses
the existing read-only isolated child. Two contrasting fixtures passed, an incorrect
count failed, an outside-root reference was blocked, cancellation passed and file
hashes stayed unchanged. All 37 database-focused checks passed. See
LOCAL_DATABASE_EXECUTION.md for remaining saved settings/queue/CLI/UI work; no
customer database admission or catalog expansion is enabled.

Count-only DB metadata can now be saved and reviewed from a single owner-scoped
snapshot through a protected local endpoint. The database path remains a scoped
environment reference; reviewing neither resolves it nor opens a target database.
Foreign references, SQL/path metadata and stale owner access are rejected. All 40
DB-focused checks, six settings checks, production/demo builds and the free browser
save-preservation drill passed. No DB execution route/UI editor is enabled yet.
Continue confirmed queue/worker integration with a fixed workspace/project fixture
root, shared licensing/cancellation/recovery and no HTTP-selected filesystem roots.

Internal confirmed DB queue/worker integration now pins the owned workspace/project
fixture root, shares API/UI/form pending and licensed running capacity, revalidates
settings, supports cancellation/explicit recovery and sanitizes outcomes. Eight
queue checks and real saved-queue pass/fail/outside-root-block proofs passed with
unchanged fixture bytes. Offline recovery cancels DB claims; target databases are
not copied into application backups. Continue HTTP/CLI and explicit UI integration
on controlled fixtures only. No customer database connector or catalog growth is
enabled; current acceptance remains bounded to the documented local profiles.
