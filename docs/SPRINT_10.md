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
- [ ] 10.2: Integrate organization-scoped projects, API/UI access and worker controls.
  - [x] Persist separate organization projects and enforce transactional project quotas.
  - [x] Add authenticated, CSRF-protected organization/project configuration API routes.
  - [x] Add local organization/project configuration UI with role-aware controls.
  - [ ] Integrate queue/worker lifecycle and recovery.
- [ ] 10.3: Verify isolation and concurrency against two disposable organizations.
- [ ] 10.4: Implement and exercise authenticated outbound agent flow on controlled local fixtures.
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
