# Post-Sprint Local Product Review

Started: 2026-10-23, explicitly authorized by the owner after closing milestone 11.
Sprint 10 issue/milestone are closed. Its frozen acceptance remains historical.
This follow-up does not enable purchases, public backend hosting or customer tests.

## Current Work

- [x] Verify Sprint 10 milestone closure and preserve the existing local session.
- [x] Review personal/shared project selection through real local Chromium flows.
- [x] Show discovered case names, searchable identifiers/names, visible/selected
  counters and a bounded list in both execution panels.
- [x] Preserve hidden selections when filtering, enforce the ten-case limit and
  clear selections explicitly. Reset stale shared selections when candidates change.
- [x] Verify actual discovery, two-case execution, report/evidence, roles and
  revocation after the UI changes; zero external requests/page errors.
- [x] Verify same-commit CI for the selection/target/document increments through
  2e2b8bd: all twelve jobs passed; four downloaded artifact digests and reports verified.
- [x] Make saved target execution eligibility explicit before queue submission;
  verify unsupported saved targets never dispatch in personal/shared browser flows.
- [ ] Extend reusable execution beyond fixed sample bindings using contrasting
  controlled fixtures before enabling any owner-authorized external targets.
  - [x] Add an explicit canonical document-path binding for the existing five
    independent document cases; remove sample title/heading assumptions only
    for those bound cases, retaining pinned egress and process deadlines.
  - [x] Verify three contrasting HTTP documents and five real negative defects
    through separate child processes, including denied write/canary requests.
  - [x] Integrate reviewed discovered local document bindings into admission/planning
    before widening dashboard execution scope.
    - [x] Route already-admitted root document cases through the independent
      executor in the common personal/shared worker; retain current admission.
    - [x] Bind non-root cases to the exact saved/discovered canonical local path;
      keep cross-document execution context unknown rather than infer comparability.
    - [ ] Add actual page-content context binding before comparing general document runs.
- [ ] Implement a configuration-driven public-target discovery/execution profile
  with existing public-address validation, pinned egress and process deadlines.
  External validation still requires an owner-authorized target; no external site
  has been contacted by these local fixture checks.
  - [x] Add typed public HTTPS/controlled-local discovery profiles and a shared
    supervised collector; verify static validation, mixed DNS refusal, cancellation
    and configured local starts without external traffic.
  - [x] Connect the public profile to authenticated dashboard admission/report scope.
  - [x] Validate bounded discovery on an owner-authorized demo HTTPS target; Core
    checks for dashboard admission 1d202d0 passed (run 39938002105).
  - [x] Integrate configured document execution into reviewed dashboard bindings;
    verify explicit selection, exact saved URL, cancellation and scoped results.
- [ ] Address operator enrollment/agent startup and bounded unattended maintenance
  from PILOT_FINDINGS.md with separately verified increments.
  - [x] Add an explicit bounded maintenance-once operator command for expired
    agent leases and personal/shared evidence pruning.
  - [x] Add a managed maintenance-once role with 30-second default/60-second
    maximum process deadline, component leases and selected-wheel execution.
  - [ ] Add and review unattended scheduling/lifecycle separately; no system
    scheduler or perpetual background service has been activated.

The last three items are future engineering work, not accepted capabilities.
Do not remove destination guards, infer ownership from a public URL or count
fixture variations as additional catalog cases. API/database business assertions
still need explicit contracts and secret references. Public Pages remains unchanged.

## Selection Verification

The personal and organization browser drills now check ID/name search, empty
search results, preservation of checked hidden tests, clearing and the ten-case
limit before running the existing real end-to-end scenarios. The shared list no
longer stretches the page with dozens of unlabelled identifiers. Normal app
build passed; personal/shared browser checks passed locally.

check_dashboard_ui.py accepts an optional --port for isolated verification when
the owner's normal server is already listening on 8765. It uses disposable
accounts/storage and never stops the owner's server.

## Saved Target Support

The local app now explains whether the saved URL/host settings match the current
controlled root worker. Unsupported targets remain configurable and reviewable;
their discovery action is disabled with a concrete explanation. This UI mirrors
the current restriction but grants no authorization: server/worker checks remain
authoritative. API/database bindings are not inferred from a URL. The message
uses saved settings so unsaved edits cannot imply an executable configuration.

Both browser flows saved https://example.test/ without visiting it, verified the
unavailable explanation and disabled dispatch, then restored the controlled
fixture and completed actual discovery/UI tests. The shared host textarea has
an explicit accessible name so repeated saved-setting edits remain addressable.
The demo regression passed at 390/768/1440 pixels with zero API/external requests
and no enabled execution. No public demo behavior was changed.

## Independent Document Worker Foundation

run_isolated_sample_test now accepts an explicit document_path for DOC-001 through
DOC-005 only. This binding visits a canonical path on the existing controlled
127.0.0.1:8000 fixture origin and evaluates the registered rule without requiring
the Adaptive QA Sample title or heading. It cannot redirect another case into an
arbitrary executor, add hosts, change methods or enable customer execution.
Paths with authority/scheme escapes, query/fragment, percent encoding, traversal,
controls or non-ASCII text are rejected before process creation. The existing
proxy/route guards, fresh context, bounded process tree, cancellation and evidence
validation remain in force. No dashboard target restriction was widened.

check_document_execution.py executes five existing cases on information, commerce
and account documents with unrelated titles (15 passed executions), then verifies
five specific broken documents produce failed assertions rather than success or
generic loading errors. Twenty PNGs are validated; a forbidden destination canary
and POST receiver remain untouched. These fixture variations do not increase the
100-case catalog. CI repeats the drill in the UI catalog job. Discovery-backed
general document admission/UI integration remains the next unfinished step.

Foundation local regression completed 659 tests: 658 passed and one Windows
symlink-permission skip. The earlier selection increment 9588cce passed Core
checks run 39914643399; saved-target increment 42db9b4 CI remains in progress.
The document foundation requires its own same-commit CI after push.

## Discovery-Backed Root Document Runs

The normal personal/shared worker now routes the five already-eligible root
document cases through the independent binding. Existing membership, discovery,
configuration, quota, result/evidence and cancellation checks remain authoritative.
The HTTP drill discovers an information page with an unrelated title, explicitly
admits five cases through each queue and verifies ten passed persisted outcomes,
ten scoped PNGs and released shared active capacity. Admission alone remains
non-executing. No root-path or external-target restriction is widened.

Document runs deliberately omit a comparable execution context until actual page
content can be bound to it; differing documents must not be pooled into flaky
signals based only on a sample source fingerprint. Worker/consistency regressions
cover this conservative behavior. The context source inventory also includes the
new document-path validator. Non-root admission/UI support remains unfinished.

## Verified Follow-Up Evidence

Implementation 2e2b8bd9cae181c9fc9436972d74d2f0d5bce244 passed all twelve
jobs in run 39915903166 and 660 Linux unit tests. Earlier 9588cce, 42db9b4 and
892c190 Core checks also succeeded. Four downloaded archives (UI catalog,
organization/browser and both packaged runtimes) passed SHA-256/head verification.
Their actual reports confirm document execution, named/filtered selection,
unsupported-target non-dispatch and both-platform runtime/rollback. See
evidence/post-review-2e2b8bd.json. This supersedes the historical pending CI notes.

The maintenance increment has its own tests/CI requirement and does not inherit
acceptance from that earlier commit. No unattended service has been installed.
Its local full regression completed 666 tests: 665 passed and one Windows
symlink-permission skip. Six maintenance tests include an actual CLI subprocess,
live/expired lease handling, partial-outcome preservation, bounded evidence
cleanup and worker-lock refusal. Both-platform CI repeats these checks.

The managed-role increment passed ten runtime tests, deployment/schema checks
and the real Windows package/restore/rollback drill using committed helper release
875adac plus the current trusted supervisor. Maintenance completed from that
selected wheel and was refused for the historical wheel lacking the module.
Both component leases released, source database bytes/backup remained intact and
ordinary discovery/UI execution still passed. CI will repeat this with the exact
combined commit on Linux/Windows; it remains pending until that run completes.

## Saved Non-Root Document Targets

The local profile now accepts canonical paths on the same fixed fixture origin,
not only its root. The discovery child receives the validated start path and
retains the same crawl/request/process budgets and read-only pinned egress.
Plans expose local_document bindings only for DOC-001–DOC-005. Personal/shared
admission rechecks that each binding exactly equals the saved configuration path.
It rejects another inspected route, a forged root binding or a login/form case
on a non-root document. No new schema or client-supplied execution path is used:
the admitted configuration snapshot remains the worker's target authority.

The worker also refuses a final navigation URL that differs from the bound
document. A same-origin redirect therefore produces an execution error rather
than a false pass against another page. General document runs remain excluded
from comparable/flaky contexts until actual page context can be established.

The panel filters runnable cases using the same saved-path contract and explains
the five-case non-root capability. Actual browser acceptance saved a non-root
URL, queued discovery, showed exactly five document choices with no login choice,
then completed DOC-001 through the separate worker. Both full personal/shared
browser checks passed. The HTTP drill independently passed five admitted cases
on each of two non-root documents, persisted ten PNGs, detected five defects,
rejected redirected bindings and observed zero forbidden canary/write contacts.
The full unit regression completed 671 tests (670 passed, one Windows permission
skip); the later redirect guard was also exercised by the real HTTP drill.

Maintenance commits 875adac and a017781 have successful Core checks. The non-root
increment requires its own exact-commit CI after push. The general public-host
profile is still unfinished; this feature does not authorize external execution.

## Configured Discovery Foundation

The internal configured worker is documented in CONFIGURED_DISCOVERY.md. It
preserves the local wrapper, uses bounded temporary configuration instead of
target values in command arguments, and keeps the existing process deadline and
pinned egress. Resource route denials now explicitly limit coverage, preventing
false absence. Three configured fixture runs, the existing real document drill
and 678 unit tests completed locally (677 passed, one Windows permission skip).
The following increment connects the dashboard public profile; real external
HTTPS acceptance remains pending.

## Authenticated HTTPS Discovery Admission

Personal and organization settings now explain public HTTPS discovery capability.
Saving and queuing never resolve DNS or execute tests. The separate bounded
worker uses saved exact-host scope, pinned public egress and cancellation checks.
Reports reject foreign snapshots and rebuild the non-executing 100-case plan;
public targets have no runnable UI/API/database binding. Existing local document
execution remains available. Both real dashboard browser checks queued/cancelled
HTTPS jobs without dispatch or external requests, then passed local worker flows.
The static Pages demo passed unchanged. Real external HTTPS acceptance awaits a
concrete owner-authorized target; this increment does not claim that acceptance.
Core checks for 99002c8 completed successfully (run 39935492689).
Exact-commit CI for this admission increment remains pending after push.

Local regression: 681 tests completed (680 passed, one Windows permission skip).
Personal/shared browser flows and the static demo check passed with zero external
requests and no JavaScript errors.

## Configured Document Worker Foundation

The internal document_process worker accepts typed project configuration for the
existing DOC-001–DOC-005 rules. It shares discovery profile validation and pinned
egress, allows only GET/HEAD, blocks WebSockets/service workers/downloads and uses
fresh contexts. It refuses non-HTML/non-200 responses, target-changing redirects
and passing verdicts with policy-denied resources. Child configuration/output are
bounded; timeout, cancellation and callback failure terminate the owned process
tree. No dashboard public execution binding has been enabled by this increment.

The configured local drill passed ten checks on two contrasting document paths,
detected five distinct defects, rejected a redirect and incomplete resource
coverage, and observed zero canary/write contacts. Five focused supervisor tests
passed. These fixture variants do not add catalog cases.

After explicit owner authorization, Books to Scrape (https://books.toscrape.com/)
was used as a public sandbox. Discovery inspected five pages with 21 guarded
requests, stopped at page_limit and retained a non-executing plan. A separate
explicit DOC-001 run passed with one screenshot. This is a bounded public demo
observation, not broad customer acceptance or proof of all five external rules.
The earlier owner-supplied site produced no usable page; an additional bounded
HEAD check returned HTTP 403 with no guard denial. No access control bypass or
retry loop was attempted. Raw external reports/screenshots remain ignored local
artifacts. Public dashboard activation and exact-commit CI for this new worker
remain unfinished.

Regression completed 686 tests (685 passed, one Windows permission skip). The
17-case owned HTTP drill passed again after evidence-path validation was added.
CI runs that drill on owned fixtures only, never against the public demo.

## HTTPS Document Selection and Execution

Personal and organization queues now admit only the five independent document
cases when their public_document binding exactly equals the saved HTTPS URL and
the current completed discovery fingerprint. Another inspected path/host, stale
configuration, login/form case or forged local binding cannot authorize execution.
Saving, discovery and plan review remain non-executing; explicit selection queues
a separate run. Roles, tenant scopes, global/owner/organization admission limits,
cancellation, deadlines and evidence authorization are retained. The worker
rechecks configuration before dispatch and persists only supported document results.
Document runs retain unknown comparison context rather than imply comparability.

Both dashboard browser drills now exercise five public document choices, no login
choice, explicit run queuing and cancellation without external traffic. Their
existing real local fixture flows continue to run afterward. Unit coverage checks
personal/shared routing, exact URL/case family, no DNS during admission and changed
configuration preventing child dispatch. Public Pages remains unchanged.

A separate owner-authorized Books to Scrape drill used temporary accounts/storage,
real public discovery (five pages), explicit five-case admission and separate real
child execution. DOC-001 through DOC-005 passed; all five scoped PNGs decoded.
This public demo observation is not customer-site or private-network acceptance.
No API/database/login/form executor is inferred from the URL. The full regression
completed 689 tests (688 passed, one Windows permission skip). This increment's
exact-commit CI remains pending after push.
