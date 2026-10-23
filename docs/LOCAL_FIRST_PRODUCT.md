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
- [ ] Bind paid administration and multi-project entitlements to verified licenses;
  preserve existing local projects during upgrade and define safe expiry behavior.
- [ ] Add customer-facing local startup/install and license import/status UX, plus
  packaged-release/backup/rollback compatibility checks for both editions.
- [ ] Verify free/paid isolation, malformed/expired/tampered licenses, concurrency,
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
