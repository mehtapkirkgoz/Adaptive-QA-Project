# Sprint 10 — Customer Management and Pilot Testing

Started: 2026-10-23
Status: In progress; explicitly started by the owner.
Tracking: [issue #11](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/11)
Milestone: [#11](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/11)

Sprint 9 issue and milestone are closed. Its accepted implementation and twelve
CI jobs remain recorded in SPRINT_9_ACCEPTANCE.md. Public Pages remains an
interface demo; automation remains local. No hosting purchases or customer targets
are authorized by this sprint start.

## Delivery Steps

- [x] 10.1a: Define typed organization roles and fail-closed quota decisions.
- [x] 10.1b: Persist organization membership with transactional privilege/revocation checks.
- [x] 10.1c: Implement atomic run admission, active claims and daily usage reservations.
- [x] 10.2: Integrate organization-scoped projects, API/UI access and worker controls.
  - [x] Persist separate organization projects and enforce transactional project quotas.
  - [x] Add authenticated, CSRF-protected organization/project configuration API routes.
  - [x] Add local organization/project configuration UI with role-aware controls.
  - [x] Integrate scoped discovery queue/worker lifecycle and recovery.
  - [x] Integrate scoped test-run admission/results/evidence and recovery.
  - [x] Finish membership administration and scoped usage visibility for onboarding.
- [x] 10.3: Verify isolation and concurrency against two disposable organizations locally; repeat in CI.
- [ ] 10.4: Implement and exercise authenticated outbound agent flow on controlled local fixtures.
  - [x] Add project-bound, expiring/revocable credential core and replay checks.
  - [ ] Add authenticated outbound transport, scoped leases/results and actual local agent drill.
- [ ] 10.5: Document onboarding/support and prioritized pilot findings.
- [ ] 10.6: Verify exact-commit CI/artifacts and report readiness for owner review.

## First Increment

organization_policy.py defines owner/admin/member/viewer permissions, typed
membership identities and bounded project/pending/active/daily quota decisions.
An owner membership cannot authorize another organization or user. Unknown and
untyped actions are denied. Admin cannot manage the organization itself.

This is a policy foundation, not live organization access or quota enforcement.
Trusted membership persistence, last-owner protection, transactional admission,
usage accounting and HTTP integration remain unfinished. Existing owner-scoped
project access and global queue limits stay authoritative. No caller-provided
membership claims may grant runtime access. Six unit tests cover the role matrix,
two-organization isolation, malformed claims, immutable identities and quota
boundaries. Same-commit CI is required after push.

The owner controls closure and any subsequent scope. Never claim synthetic local
pilot findings are real customer feedback or enable customer execution implicitly.

## Persistent Membership Increment

OrganizationStore adds organization and membership tables through the existing
project store's schema-gated connection. Creation atomically persists an owner
and typed quota. Membership writes use BEGIN IMMEDIATE and re-read the caller's
role inside the write transaction. Revocation/demotion takes effect on the next
operation. Admins cannot promote members to admins, change peer admins or change
owners; owner transfer/removal is disabled, so the last owner cannot disappear.
Other-organization and nonexistent access share the same not-found outcome.

Six real SQLite tests passed for reopening, quota persistence, two-organization
isolation, administrative boundaries, owner preservation, revocation and unchanged
historical owner-project isolation. These internal tables are not yet connected
to HTTP or workers. Membership user IDs must originate from authenticated server
identity resolution; there is no public invitation endpoint or automatic grant.
Quotas are stored but not yet reserved/enforced transactionally.

## Atomic Run Admission Increment

OrganizationAdmission persists a local reservation ledger without starting work.
BEGIN IMMEDIATE encloses membership reads, quota counts and reservation/claim
writes. Eight parallel attempts admit exactly two pending reservations in the
fixture; two parallel claims admit exactly one active reservation. Exact opaque
claim tokens and organization/user bindings prevent another tenant or stale claim
from releasing capacity. Role revocation blocks new claims and converts an active
claim's release to cancelled. Pending cancellation frees pending capacity but
never refunds daily admitted-run usage. Daily buckets use UTC admission time;
crossing midnight does not free outstanding pending/active capacity.

Six SQLite tests passed for concurrent admission/claim, stale tokens, two-tenant
isolation, cancellation/daily rollover, revocation and invalid clocks. The prior
complete suite ran 600 tests (599 passed, one Windows symlink-permission skip).
The six new admission tests passed separately; new exact-commit CI remains pending.

The ledger is an internal foundation, not yet the existing job queue. Project
quota enforcement, membership resolution through authenticated API/UI, atomic
queue linkage, crash/recovery handling of reservations and worker integration
remain required before organizational execution is enabled. Existing queue
limits and target policies stay authoritative. Stored quotas are not customer
billing, and finished reservations do not imply successful test assertions.

## Organization Projects and Authenticated API

Separate organization-project tables preserve historical personal-project
ownership. Owner/admin configuration permission is resolved from current stored
membership inside every write transaction. Project quota checking and insertion
share that transaction. Eight concurrent creation attempts cannot exceed the
two-project fixture limit. Viewers can read but cannot configure; removal denies
subsequent reads. Secret reference names use organization/project scope and never
resolve values during configuration. An organization ID is not a personal actor.

The local API exposes organization listing/creation/detail, scoped project
listing/creation/rename/detail and saved configuration. Every mutation uses the
existing cookie session, CSRF, strict Origin/Host, body limit and exact-field
validation. Missing privileges and missing resources share the existing 404
response. Quota refusal returns 409. No organization execution endpoint is exposed.
Four SQLite project tests and three real ASGI tests passed, including revocation,
cross-organization isolation, secret scope, anonymous denial and zero queued work.
The public Pages demo is unchanged by the owner's explicit instruction.

## Local Organization UI

The signed-in local dashboard now has an expandable Organizations panel. It
lists memberships, creates organizations/shared projects, displays role/project
quota, and reads/saves shared URL/host/secret-reference settings. Current data-change
policy is preserved. Viewer controls are disabled; all permissions are rechecked
by the API regardless of UI state. Switching organizations clears prior project
state and ignores late selection responses. No organization execution control is
shown before queue/worker integration exists. DemoWorkspace was not changed.

TypeScript/Vite production build passed. check_organization_ui.py exercised real
Chromium against disposable local accounts and stores: owner create/save, viewer
read-only access, revocation after reload and hidden other-organization data.
It recorded zero queued runs, external requests or page errors. Desktop/mobile
screenshots and a value-free report are retained; CI repeats this check. Seven
new project/API tests passed. Full local regression: 613 tests, 612 passed and
one Windows symlink-permission skip. Exact-commit CI is pending after push.

## Scoped Discovery Worker and Recovery

Organization discovery now has separate persisted jobs with organization/project
and submitting-user binding. HTTP submission only queues controlled loopback
discovery. The local panel can review the resulting non-executing plan; viewer
dispatch/cancel controls are disabled and API authorization is independently
enforced. Worker claims re-read membership and configuration before any execution;
revocation or policy changes cancel queued/active work and discard late reports.
Claims are opaque, single-use and absent from public responses. The existing
worker retains the OS execution/recovery lock and supervised crawl deadlines.

Global discovery admission counts personal plus shared jobs in either direction
under the same SQLite write lock; organization discovery also has a bounded
pending cap. Personal jobs are processed first, then organization discovery on an
explicit discovery-once invocation. The managed launcher checks selected-package
support before invoking this fallback, preserving older package compatibility.
Discovery plans never authorize test execution. Organization test runs remain
unimplemented and are not exposed through the UI/API.

Offline restore cancels pending/running shared discovery and pending/active
admission reservations, clearing claims in the recovered copy while preserving
source/live bytes and shared projects. Operator recovery also refuses a live
worker and never replays interrupted work. Six queue tests, one real recovery
test and one ASGI dispatch/role test cover these boundaries. The real Chromium
flow now queues shared discovery, invokes the actual worker against the local
fixture and reviews its plan with execution_authorized=false. It still records
zero test runs, external UI requests or page errors. Full local regression ran
621 tests: 620 passed and one Windows symlink-permission fixture was skipped.
TypeScript/Vite build passed. Same-commit CI remains pending after push.

## Shared Test Runs, Evidence and Atomic Quotas

Shared run admission now inserts the quota reservation and queued run in one
SQLite write transaction. A failed run insert rolls back the reservation. Current
membership, settings and completed scoped discovery are required; only selected
read-only UI cases bound to the controlled local root can be dispatched. Global
100-job and per-user five-job bounds include personal plus shared runs in both
directions. Pending, active and UTC daily organization limits use the persistent
ledger; cancellation frees outstanding capacity without refunding daily usage.

Claims bind the same opaque token in both the run and reservation. Membership and
settings are rechecked at claim, cancellation checks, result insertion and final
publication. Revocation/policy change discards late results and cancels work.
Individual assertion outcomes remain distinct from completed lifecycle. Partial
results survive cancellation/recovery; unattempted cases receive no invented
outcome. Recovering interrupted work releases only the exact linked claim and
never replays execution. Offline restore cancels both shared runs and reservations
while retaining earlier assertions/PNGs and original live database bytes.

The authenticated shared API now supports explicit run dispatch, history/detail,
cancel and opaque scoped PNG retrieval. Current viewers can read but cannot
dispatch/cancel. Expired evidence is immediately unavailable, with bounded indexed
cleanup under the worker. Raw adapter messages, secrets, claims and paths are not
returned. Shared historical comparisons/reruns are not enabled by this increment.

The local UI selects up to ten explicit cases from reviewed discovery and shows
run results/evidence links. The existing supervised UI worker processes shared
work after personal work under its OS lock, inner deadlines and private temporary
evidence directory. The managed launcher checks selected-package support before
using the fallback. The public interface demo remains unchanged.

Eight queue tests passed for parallel admission/active limits, transaction rollback,
revocation, daily usage, policy changes, tenant isolation, expiry, stale claims and
partial recovery. A new real-SQLite restore test and authenticated ASGI evidence
test passed. Real Chromium queued LOGIN-001/SEARCH-001, the actual worker passed
both cases and persisted two PNGs, and anonymous/revoked evidence requests were
denied. Zero UI external requests/page errors occurred. Production build passed;
full local regression completed 631 tests (630 passed, one Windows symlink
permission skip). New exact-commit CI remains pending after push.

## Membership Administration and Usage Visibility

Owner/admin can now list scoped members and add or change an existing provisioned
account by email through the authenticated local API/UI. Authorization precedes
account lookup and is rechecked in the membership write transaction. Members and
viewers cannot enumerate account emails. Admins cannot create/administer admin
peers or change owners; owner transfer/removal remains disabled. Unknown emails
do not create accounts or send invitations. Provisioning remains an interactive
local administrator operation. Membership removal affects subsequent API reads,
worker claims and result/evidence publication checks.

Local creation is capped at twenty owned organizations per user and one hundred
members per organization, including its owner. These checks share the write
transaction and do not prevent editing an existing member at capacity. The
bounded roster exposes only current organization's member emails/roles to its
managers. No public user search or password/token data is returned.

The access panel also displays pending, active and UTC daily admitted-run counts
alongside organization limits. Counts are a consistent read snapshot at refresh;
they never authorize work. Actual dispatch/claim still reserves quota atomically.
Cancellation does not refund the daily admission counter; another organization's
usage remains inaccessible. These counters are not billing or API-model costs.

New tests cover bounded organization/member creation, scoped usage after
cancellation, authorized existing-account resolution, owner/admin privilege
boundaries and denial before account lookup. The real browser flow adds a viewer
through the UI and verifies the daily snapshot after two actual UI assertions in
one run. Production build and focused tests passed. Full local regression completed
635 tests (634 passed, one Windows symlink-permission skip). Exact-commit CI remains
pending after push. Sprint 10 is not yet ready for closure; agent/pilot and final
consolidated acceptance remain unfinished.

## Consolidated Two-Organization Drill

check_organization_isolation.py creates two disposable organizations/accounts in
one local database and runs actual bounded discovery for each. Sixteen concurrent
dispatch attempts admit exactly two pending runs per organization. Claiming
admits one active run in each organization and no second active run in either.
Two explicitly interrupted claims become error, with no invented assertion.
The remaining workers execute LOGIN-001/SEARCH-001 for both organizations: two
completed runs, four passed assertions and four validated persisted PNGs.

Cancellation frees capacity but does not refund daily admission; each organization
reaches its independent three-admission daily cap. Foreign results/evidence,
viewer dispatch and revoked reads are denied. No customer sites are contacted.
The safe report is artifacts/organizations/isolation.json and CI retains it with
the existing organization UI evidence. Exact-commit CI/artifact acceptance is
still required; this is a controlled local drill, not real customer pilot feedback.

## Agent Credential Foundation

AgentRegistry enrolls only through a trusted internal operator call by the
organization owner. Each credential binds one organization/project and expires
within one day (default one hour). Enrollment requires exactly the controlled
loopback root, only the loopback allowed host and data-changing policy disabled.
At most ten unexpired/unrevoked agents are allowed per organization.

The generated high-entropy bearer is returned once as a masked SecretValue and
is never stored in plaintext. Authentication compares SHA-256 digests in constant
time and transactionally advances a strictly increasing bounded sequence number.
Concurrent replay is accepted at most once. Each check revalidates current issuer
privilege, project scope, local target/policy, revocation and expiry. Trusted server
identity objects are internal context, never client-provided authorization.

Offline restore revokes every recovered agent credential, preventing old sequence
counters from reviving a bearer. A real recovery test verifies refusal in the copy
while the original database/credential remains unchanged. Five credential tests
and seven backup/recovery tests passed locally; Linux/Windows CI includes these.
This core does not listen, poll, dispatch or execute. HTTP transport, scoped work
leases/result acknowledgement, credential handoff and the real outbound-only
local agent demonstration remain unfinished; no customer agent deployment is claimed.
