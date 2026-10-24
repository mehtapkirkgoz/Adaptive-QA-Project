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
  - [x] Add URL-independent read-only login/search assertions with deterministic
    label/role alternatives and typed project overrides; verify contrasting DOMs.
  - [x] Integrate those assertions into a supervised configured form executor;
    verify contrasting HTTP fixtures, explicit mapping transport and lifecycle.
  - [x] Integrate exact saved-URL form bindings, personal/shared admission and
    UI selection; verify controlled HTTP execution and both dashboard flows.
  - [ ] Verify exact-commit CI/artifacts for the configured form integration.
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

## Independent Login and Search Form Assertions

form_checks.py provides read-only LOGIN-001 and SEARCH-001 assertions without
sample URL, title, heading or mandatory sample test IDs. Existing deterministic
matching unions all role/label alternatives; missing/ambiguous controls raise a
typed ElementBindingError instead of selecting the first candidate. Explicit
ProjectElementMappings replace alternatives and enforce project identity. Bound
controls must be connected to the same form; unrelated sign-up/search/login
fields cannot be combined. Input types, password masking and enabled submit
controls are checked. No control is filled, clicked, reset or submitted.

Sixteen real Chromium DOM scenarios passed: English/Turkish labels, alternate
names, explicit mappings, foreign mapping refusal, hidden duplicates, ambiguous
forms/buttons, missing fields, exposed password, split forms, disabled controls
and a non-submit search button. There were zero network requests and zero input,
click or submit events. Thirteen existing element-contract unit tests also passed.
CI includes this owned-DOM drill; catalog count remains 100. These are assertion
foundations, not yet new public worker bindings, credentials/login execution or
proven external form compatibility. The next increment is supervised configured
form execution and controlled HTTP acceptance before dashboard activation.

## Supervised Configured Form Worker

run_isolated_form_test uses the existing bounded document-process supervisor with
an explicit form family. The document entry point still refuses form cases;
the form entry point accepts only read-only LOGIN-001 and SEARCH-001 assertions.
Typed project mappings travel through the bounded private configuration file,
are reconstructed and revalidated inside the child, and cannot belong to another
project or introduce unknown mapping keys. No credential is resolved or supplied.
Missing/ambiguous controls produce BLOCKED, a violated assertion produces FAILED,
and destination/coverage/loading failures produce ERROR. General form execution
is not yet exposed through dashboard admission by this increment.

Twelve real owned HTTP child runs verified English/Turkish login, search, explicit
mapping, missing/ambiguous controls, password masking, disabled submit, split forms,
blocked external resource, blocked POST and redirect refusal. Twelve PNGs decoded;
canary/write/input/click/submit contacts remained zero. Twelve focused process
checks passed, including real child cancellation, deadlines and callback failures.
The existing 17-scenario document HTTP drill also passed after the shared helper
change. CI runs these on owned fixtures only, without public-site traffic.
Core checks for ea8bba2 (run 39940043476) passed. Core checks for e817cf0 were
superseded/cancelled; ea8bba2 includes that integration and passed the full workflow.
This worker increment requires its own exact-commit CI after push.

The complete local regression passed 696 tests (695 passed, one Windows permission
skip). See CONFIGURED_FORMS.md for supported assertions and current limits.

## Read-Only Form Admission and Selection

LOGIN-001 and SEARCH-001 now expose a local_form/public_form binding only when
supported by discovery. Admission requires the exact saved path/URL, current
configuration fingerprint, selected UI status and the correct read-only case
family. LOGIN-002 and other interactive cases remain excluded. The shared worker
routes only those two generic form checks to run_isolated_form_test; controlled
root sample execution remains unchanged. General form/document runs retain unknown
comparison context. Current quotas, role checks, cancellation and scoped evidence
are shared with the existing run pipeline. No credential is resolved or supplied.

Login matching first binds one password field and uses its connected form as the
scope for username/email and submit alternatives. This prevents a separate email
registration form from creating a false ambiguity while preserving ambiguity
within the selected form and between multiple password forms. Search anchors to
its unique query field. Cross-form controls cannot combine; missing submit in the
anchored form is BLOCKED. Explicit project mapping persistence/UI is unfinished;
the dashboard currently uses default alternatives, while the internal worker
supports typed overrides. Custom names may therefore remain blocked.

The personal browser drill exposes five document plus two form choices on a
non-root English fixture and executes DOC-001/LOGIN-001 with separate real children.
Both public UI scenarios use controlled snapshots to show seven choices and queue
then cancel a login-form run without external traffic. No external form execution
or authenticated login is claimed by these tests. Public Pages remains unchanged.

The configured HTTP drill also completed admitted personal LOGIN-001 and shared
SEARCH-001 runs through actual discovery, quota admission and separate child
execution. Both scoped PNGs decoded; canary/write/interaction contacts stayed zero.
The full personal/shared browser flows passed with no external requests or page
errors, and the static demo regression remained unchanged. Seventeen direct DOM
scenarios passed after adding anchored form filtering, including an unrelated
registration email field. The affected admission/binding unit checks were repeated.
Next: persist/review explicit project form mappings before supporting arbitrary
custom names from the dashboard; credentials and data-changing tests remain out
of this read-only profile. Exact-commit CI/artifact acceptance remains pending.

Historical CI assertion evidence is recorded in docs/evidence/form-foundation-ea8bba2.json:
all twelve jobs passed, and the downloaded UI catalog artifact digest/head commit
and sixteen original form scenarios were independently verified. That record does
not claim acceptance of the later worker or dashboard integration.

After updating the historical non-root binding expectation, the complete local
regression passed 698 tests (697 passed, one Windows permission skip). The test
still proves a discovered login path cannot silently execute against the root.

All 96 existing reusable fixture runs across English, Turkish and mapped variants
passed after the matcher change. README now separates current form capabilities
from historical sprint acceptance and corrects the closed Sprint 9/10 table rows.

## Saved Project Form Mappings

Personal/shared project settings now persist up to five known logical mappings,
with bounded exact label, button-role or test-ID alternatives and optional test-ID
scope. The panel's Custom form controls editor saves these with normal scoped
configuration; viewing/reloading preserves names, strategy and scope. Empty names
restore defaults. Omitted form_mappings in a legacy full configuration PUT also
restores defaults. No raw credential or arbitrary selector/script is supported.

Non-empty mappings are part of secret-free discovery/run snapshots and fingerprints.
Changing an override invalidates prior report admission and prevents stale pending
execution. Empty mappings retain historical fingerprints, without a database DDL
migration. The worker receives typed mappings for its project and validates them
again in the child. Controlled root form runs with overrides use the generic form
worker rather than the fixed sample binding and retain unknown comparison context.

Configured button-role names participate in structural discovery only when the
observed form contains the actual action and required field types. A configured
Continue name does not invent a form or change an assertion. Test-ID-only custom
actions do not prove feature applicability from snapshots; they may remain unknown
until additional structural evidence exists. Public plans remain non-executing.

The fixed pilot agent refuses custom-mapped or non-root/public configurations;
those runs remain available to the supported local worker. Managed selection and
component startup refuse older releases lacking form_configuration when saved or
historical run configuration contains non-empty mappings. Compatibility inspection
is bounded and read-only. This supplements schema compatibility; a schema-only
rollback plan does not itself approve this feature compatibility check.

Both real dashboard browser flows saved custom names and a test-ID strategy/scope,
reopened the project to verify persistence, reviewed controlled snapshot evidence,
queued/cancelled without external traffic, then cleared overrides and passed prior
local fixture flows. Owned HTTP acceptance used saved custom labels/button names
through personal login/shared search discovery, admission, child execution and two
scoped PNGs. Canary/write/interaction contacts stayed zero. The full regression
passed 703 tests (702 passed, one Windows permission skip); affected mapping and
runtime compatibility checks were repeated after final changes. Static demo
behavior remained unchanged. Exact-commit CI remains pending after push.

Next product work: validate the resulting local UX with the owner, then implement
separately bounded interactive login/search contracts with explicit secret
references and data-change policy. Structural form checks still never fill fields,
resolve a credential, sign in or submit a search. Overall product acceptance is
pending; closed sprint tracking is not reopened.

## Interactive Contract Preparation

While the final local-first UI CI job was still installing Chromium, independent
non-executing interactive login/search contracts were prepared. See
INTERACTIVE_FORMS.md. They bind typed environment references, project/configuration,
fixed postconditions and conservative data-change permission. Four focused checks
passed for no secret/network access, rejected plaintext, policy/configuration drift
and assertion/input fingerprint changes. No submission worker or catalog execution
was enabled. Finish local-first remote acceptance before wiring controlled execution.

## Controlled Interactive DOM Transition Proof

Local-first CI acceptance was verified in commit 3a79091. The next independent
interactive increment adds an internal DOM probe and sixteen Chromium transition/
negative scenarios under INTERACTIVE_FORMS.md. No queued submission worker or
external network form submission is enabled. The fixture runner fulfills documents
and denies all subsequent requests, records no screenshots and disposes contexts.
Inputs are referenced and resolved only after preconditions; results are sanitized.
Continue with hard child supervision and owned HTTP fixture proof before product
admission. Exact-commit CI for this increment is pending after push.

## Supervised Controlled DOM Process

The fixed-fixture interactive DOM probe now has bounded parent/child transport,
hard process deadline, pre/active cancellation and sanitized callback/result
handling. Seven supervisor tests and eight actual Chromium child scenarios passed.
No HTTP endpoint submission, catalog admission or customer interaction is enabled.
CI verifies supervision and real browser deadlines on both supported OS runners;
continue with the owned HTTP fixture/transport work in INTERACTIVE_FORMS.md.

## Pinned Owned HTTP Interactive Document Fixtures

The supervised fixed-fixture probe now supports one pinned initial HTTP GET using
the existing destination guard/proxy. Eight child/browser cases passed against
contrasting owned documents, with zero network submissions, unexpected requests
or canary contacts. Subsequent HTTP/WebSocket traffic remains denied. This proves
document loading and client-side transitions, not endpoint credential submission.
Continue with the explicit owned submission-endpoint contract/transport described
in INTERACTIVE_FORMS.md; no customer/site activation or catalog admission is added.
Exact-commit CI for this increment is pending after push.

## Canonical Private Transport Paths

CI run 40048206855 passed eleven jobs but the Windows packaged-runtime probe
exited before producing a child result; this is not accepted CI evidence.
The owned temporary directory is now resolved before child argv construction,
so Windows short-name/junction TEMP aliases cannot conflict with the strict
canonical-path check. The child path/link checks remain enforced. Eight supervisor
tests, including a noncanonical-directory regression, and eight actual local
Chromium process scenarios passed. Exact-commit Windows/Linux CI must verify
whether this resolves the runner failure before endpoint transport is extended.

## Explicit Owned Submission Contract

Commit a30bc03 passed all twelve CI jobs in run 40051558174, including Windows
and Linux packaged-runtime probes. The canonical-path fix is remotely verified.

OwnedSubmissionContract now binds a typed form contract to one of four fixed
positive/negative login/search documents and its exact same-origin owned POST
endpoint. Field names/order, encoding, body limit, single attempt and no redirects
are fixed metadata included in its digest. Saved project identity, configuration
fingerprint and data-change permission must match before constructing the gate.

The child-local one-shot gate validates bounded URL-encoded UTF-8 values without
resolving references, opening sockets, persisting or returning values. Invalid
method/endpoint/encoding, duplicate/extra/missing fields, empty or oversized values
and control characters fail closed and consume the attempt. Six tests cover scope
expansion, policy drift, secret/network inactivity, malformed requests and distinct
search/Unicode bindings. No transport is connected yet: the next step is pinned
one-shot owned HTTP transport plus browser integration/redirect/canary checks.
Existing read-only proxy policy, catalog, queues and external execution are unchanged.

## Pinned One-Shot Owned Endpoint Transport

The separate OwnedSubmissionTransport now sends only the admitted POST through
DestinationGuard's exact numeric loopback peer validation. It forwards no browser
cookies, Authorization headers or arbitrary request headers. Two-second socket I/O
limits supplement (and do not replace) required future child process supervision.
Redirects, encoded/chunked responses and non-fixed JSON outcomes are rejected;
response bodies/headers and request values are never returned as result evidence.
Connection/response uncertainty reports an unknown attempt count and consumes the
gate; there is no automatic retry. The existing browser/read-only proxy is untouched.

Eight unit tests passed. Five actual local endpoint scenarios passed: accepted,
rejected, redirect, unexpected echoed response and dropped response. Exactly five
POSTs reached the owned endpoint; zero canary/other requests or retries occurred.
CI repeats this script on Windows/Linux and uploads its value-free report.
This transport is not yet connected to Chromium, child IPC, catalog or product
admission. Next: supervised browser submission using this exact gate, retaining
pre-fill action/field checks, absent-before/present-after postconditions and the
same cancellation/deadline controls. No public/customer POST is enabled.

## Supervised Owned Browser Submission Proof

Transport implementation 9b41637 passed CI run 40055689526. The new explicit
owned_submission source revalidates its fixed endpoint binding before parent
spawn and again after child decoding. All secrets still resolve only after DOM,
project, action/method/encoding and absent-completion checks in the child.
The route stays disarmed during filling; just before the one click it binds the
exact URL-encoded expected values to the request. An altered value, premature
fetch, wrong action/field or extra request cannot reach the endpoint. Only that
exact body is forwarded through the separate numeric-IP-pinned transport; the
read-only browser proxy still admits only the initial GET. Browser UTF-8
URLSearchParams encoding has an explicit supported content-type variant.

A successful result requires both one matching endpoint outcome and the expected
new UI marker. Negative login/search outcomes use their own explicit postcondition.
Unexpected responses, dropped responses, redirects and duplicate submissions fail
closed without retry, echoed values, cookies or screenshots. Active cancellation
after the server receives the POST terminates the owned child and reports unknown
completion rather than claiming zero activity or retrying.

Twenty-two focused unit tests passed. Fourteen actual supervised Chromium scenarios
passed against contrasting owned controls: fourteen documents and nine POSTs,
zero canary/unexpected requests or malformed forwarded bodies. The prior eight
in-memory and eight document-only HTTP scenarios also passed unchanged, with zero
POSTs. CI now repeats the new browser proof on Windows/Linux and uploads a separate
value-free report. Exact-commit CI for this browser increment remains pending.

This remains an internal fixed-fixture proof. Product/paid queue admission, scoped
saved secret bindings, reusable completion mappings and user-visible controls are
not yet connected. Next implement that admission contract while retaining the
non-executing plan and existing data-change/licensing/project boundaries. No
arbitrary/customer endpoint or public-site credential submission is enabled.

## Saved Owner-Scoped Interactive Review

Browser implementation d0860a6 passed all twelve CI jobs in run 40060073175,
including the new owned submission proof on Windows/Linux. Saved interactive
review now reads one owner-scoped settings snapshot and revalidates all saved
reference names against the exact owner/project/slot. Login uses the existing
username/password slots; search has a separate optional search_query slot.
References remain names only and are not resolved by review or HTTP.

The review binds the entire validated saved configuration, including scoped input
references and form mappings, to the fixed owned endpoint and operator-supplied
explicit completion mapping. Revalidation rejects changed settings, removed
references, altered target/policy/mappings and cross-owner access without silently
refreshing the reviewed configuration. Free local identity/project limits remain
unchanged. The expected positive/negative logical postcondition must match the
chosen fixture; reviewers cannot substitute the opposite outcome.

POST /api/projects/{project_id}/interactive/review accepts only fixture_id,
completion (the existing typed mapping structure), and optional timeout_seconds.
It requires an authenticated local session, trusted origin and CSRF token, and
returns an explicitly non-executing summary/digest with no input references or
values. It cannot create a job, launch a process, reserve paid capacity or grant
execution authority; existing discovery/test plans remain non-executing.

Eighteen focused persistence/settings/HTTP tests passed. Next: transactional queue
admission and claim-time revalidation, current license/shared capacity checks,
reference-only worker IPC and cancellation/results without screenshots. Until
those are connected, no interactive run is exposed through the product. Real
customer/public credential submission remains outside this fixed-fixture scope.

## Transactional Owned Interactive Queue and Worker

A separate internal owned-fixture queue now admits only a current typed saved
review, under BEGIN IMMEDIATE. It persists the assertion/configuration digests and
completion metadata, not resolved values. It revalidates saved scoped references,
data-change policy and the exact owned target at submit and claim; stale jobs
become errors before any child starts. A fresh random claim token binds work,
prevents double finalization and is removed on finish/recovery. No interrupted or
uncertain submission is automatically retried.

The trusted worker holds the existing OS worker lock and passes only references
to the supervised owned-submission child. Cancellation polls current ownership,
settings and license state. Results retain only status and known/unknown attempt
count, never adapter messages, screenshots or bodies. Pending work is bounded;
interactive/test-run admission shares its run limits. Licensed concurrency counts
interactive jobs together with existing discovery/test workers in both directions.
Expired licenses prevent admission/claim and request cancellation of running work.

Both local-first and legacy offline restore paths cancel optional interactive
work and invalidate its claims. The new table is optional for older workspaces;
no closed sprint or frozen catalog membership is changed. Explicit custom input
mappings currently fail closed at admission until their child IPC is implemented,
rather than silently using defaults. HTTP review still cannot enqueue or run work;
no new execution endpoint or public/customer submission has been enabled.

Eight queue tests passed for owner/claim isolation, atomic pending limits and
concurrent claims, claim-time configuration drift, cancellation/recovery, scoped
worker inputs, real signed-license expiry/concurrent capacity and offline restore.
Existing run admission (7), local backup (5), licensed behavior (6), and legacy
backup/recovery (22) tests passed. The real browser proof additionally created a
fresh free workspace, saved scoped references, queued and executed one real
Chromium job successfully; no plaintext password was stored. Combined fixture
contacts: fifteen documents, ten POSTs, zero canary/unexpected/bad-body contacts.
CI repeats that saved queue/worker proof on Windows/Linux in the existing script.
Exact-commit CI remains pending after push. Next connect carefully bounded local
operator controls and explicit review-digest confirmation, and verify mapped-input
transport before any broader reusable execution.

## Project Input Mappings Reach the Owned Child

Queue implementation a1432dd passed CI run 40063915642. Typed saved input mappings
now cross the bounded private child IPC and are revalidated against the exact
project and the five supported input/submit keys before spawn and after decoding.
The child passes them into the existing deterministic matcher; explicit project
overrides replace defaults and ambiguity remains blocked. No arbitrary selector,
completion assertion replacement or cross-project mapping is admitted.

Thirty focused interactive contract/review/queue/process tests passed. The actual
browser proof now additionally executes a saved queue job whose three login labels
are absent from the default aliases, using explicit project mappings. A second
mapped fixture with two matching username controls is blocked before a POST.
Combined proof: seventeen documents, eleven POSTs, zero canary/unexpected/bad-body
contacts, no screenshots or persisted plaintext password. CI repeats this on both
OS runners. The prior admission restriction on custom input mappings is lifted
only for this tested fixed owned-fixture workflow; public/customer targets and
existing non-executing plans retain their prior scope.

Next: bounded local operator admission with explicit current review-digest
confirmation, scoped job history/cancellation and licensed/free worker commands.

## Confirmed Local Operator Admission

Local free/licensed APIs now expose bounded owned-fixture job admission/history,
status and cancellation. Admission requires the exact contract digest returned by
an explicit fresh review, plus the same fixture, completion mapping and timeout.
A stale digest, changed policy/assertion/settings, plaintext inputs or missing
session/CSRF is rejected. The queue independently revalidates current saved state
inside its transaction. HTTP never launches a child or resolves an input value.
These execution routes are absent from the legacy organization/account composition;
only local-first editions expose them. Review remains non-executing in all editions.

Routes:
- POST /api/projects/{project_id}/interactive/jobs: review fields plus confirmed_contract_fingerprint.
- GET /api/projects/{project_id}/interactive/jobs: latest twenty owned jobs.
- GET /api/projects/{project_id}/interactive/jobs/{job_id}: sanitized status/result.
- POST /api/projects/{project_id}/interactive/jobs/{job_id}/cancel: empty JSON object.

Trusted local operators can process exactly one job, or recover interrupted claims:

```powershell
python -m adaptive_qa dashboard free-interactive-once --database artifacts/local-free/projects.sqlite
python -m adaptive_qa dashboard free-recover-interactive --database artifacts/local-free/projects.sqlite
python -m adaptive_qa local interactive-once --workspace artifacts/local-free --trusted-keys publisher-public-keys.json
python -m adaptive_qa local recover-interactive --workspace artifacts/local-free --trusted-keys publisher-public-keys.json
```

Free commands refuse a workspace with any licensing marker. Paid commands construct
the licensed store and require the caller's trusted public-key file; claims still
check license validity and shared capacity transactionally. Recovery cancels/errors
interrupted work without resubmission. No account or secret value is added by free
commands. The target scope is still the four fixed owned local fixture endpoints.
The public Pages demo and real customer/public-site execution scope are unchanged.

Seven HTTP and seven free/paid CLI tests passed. Next add local UI controls that
show this scope clearly, clear confirmation after edits/admission, and display
unknown submission completion without offering an automatic retry.

## Local Interactive Operator UI

The real local-first dashboard now shows controlled interactive controls only for
the four exact supported saved fixture URLs. It requires saved data-change
permission and the operation's scoped references, then lets the operator review an
explicit completion test ID/timeout and separately confirm one submission.
Editing either field or admitting a job clears the review and confirmation. A
failed/uncertain queue response clears confirmation and refreshes history instead
of automatically resubmitting. Job history supports cancellation and distinguishes
known counts from unknown completion. Browser screenshots remain disabled for
interactive target execution; UI verification screenshots contain no input values.

The built free local UI was verified in a fresh disposable workspace/server on
port 8893, preserving the owner's existing running session. Desktop/mobile proofs
cover review without target access, confirmation invalidation, queue/cancel and a
clearly synthetic unknown worker outcome. There were zero target/external requests,
page errors, registered accounts or mobile overflow. Both screenshots were
visually reviewed. TypeScript/production/demo builds and the existing Pages demo
browser checks passed: catalog 51 UI + 34 API + 15 database, no API/external request
and no execution in the demo. CI uploads the new local UI evidence. Exact-commit
CI for the operator API and this UI increment remains pending.

The public demo behavior and legacy organization UI are unchanged. This is not
an arbitrary-site login adapter: general HTTPS remains bounded read-only. Next
verify exact-commit artifacts for the combined owned interactive pipeline, then
prioritize reusable endpoint/response bindings and operator configuration rather
than claiming customer deployment from these local fixture proofs.

## Exact-Commit Interactive Verification

Implementation 153d473f6cae7b9060ab8faba442c36f055e6b3e passed all twelve jobs
in CI run 40067846716 and 783 unit tests. All twelve downloaded artifact ZIPs
matched their GitHub SHA-256 digests, sizes and source head; ZIP integrity and
208 PNGs were validated. Four inner release file digests and inactive activation
state were also checked. Evidence is recorded in evidence/interactive-ci-153d473.json.

Both Windows/Linux runtime artifacts independently confirm fourteen browser
scenarios plus saved/default/mapped queue execution: seventeen documents, eleven
POSTs, zero canary/unexpected/bad-body contacts, no target screenshots or persisted
plaintext password. Ambiguous mappings were blocked before submission. The local
UI artifact proves confirmation clearing, cancel/history and synthetic unknown
completion wording with zero target/external requests, page errors or accounts.
The downloaded mobile screenshot was visually inspected. This verifies the owned
interactive pipeline only; general/customer interactive execution and overall
owner product acceptance remain pending.

Next implementation target: separate reusable local endpoint/field/response
bindings from the fixed fixture registry, prove them on contrasting owned local
fixtures, then connect scoped saved configuration. Keep public HTTPS read-only;
no customer credentials or private-network activation are authorized by this proof.

## Reusable Owned Local Endpoint Bindings

The new LocalFormBinding separates operation input names, document/POST endpoint
paths and strict positive/negative boolean JSON response assertions from the four
fixed fixture IDs. Bindings still require the exact owned 127.0.0.1:8000 origin,
normalized distinct document/endpoint paths, matching project/fingerprint and
data-change permission. Cross-origin/port/alias/query/fragment/encoded/ambiguous
paths are rejected. Input names and typed response status/field/boolean assertions
are bounded and included in the contract digest. No values resolve at construction.

The existing one-shot pinned transport accepts this typed local binding while
preserving the frozen fixture contract's exact response rules. Reusable responses
must contain exactly one declared boolean field, with the expected status; extra
fields, echoes, duplicate fields, string/numeric booleans, redirects, encodings and
unexpected responses fail closed. Cookies/authorization are not forwarded, no
response text is returned, and uncertain network completion is not retried.

Five new binding tests, nine existing gate/transport tests and thirty interactive
contract/review/queue/process tests passed. Eight real owned HTTP scenarios passed
with independent /account/access -> /session/check and /catalog/find -> /v2/query
bindings, different input names and response fields/statuses. Exactly eight POSTs,
zero canary/bad requests and no retries were observed. The original five fixed
endpoint scenarios also passed. CI repeats reusable transport proof on Windows
and Linux. No catalog case was added or claimed executable.

This reusable binding is not yet admitted by the saved configuration/API/queue or
browser child; those remain restricted to the four accepted fixed fixtures. Next
carry the typed binding through bounded supervised IPC, prove contrasting browser
forms, then add owner-scoped saved configuration/review confirmation. Public HTTPS
and customer/private-network submission permissions remain unchanged.

## Supervised Reusable Local Browser Bindings

Reusable transport implementation 6b7b863 passed CI run 40071483894. A new typed
reusable-local entry point now carries the explicit endpoint/field/response binding
through bounded private IPC to the existing owned browser supervisor. Parent and
child independently reject conflicting fixture IDs, changed form contracts,
wrong project/fingerprint, malformed/extra response fields and unsupported origin
metadata. Existing fixture dispatch and optional mapping compatibility remain.

The child uses the same pinned initial GET, disarmed-before-click route, exact
expected request body, one-shot pinned POST, process deadlines, cancellation,
secret locality and sanitized result bounds. It fulfills only the configured safe
boolean response outcome/status to the owned page, without forwarding raw response
text/headers. Passing still requires the explicit new UI marker and the matching
server outcome; a fake client-side success marker without an endpoint request
produces an error. No retry, screenshot or external endpoint is enabled.

Forty-five focused binding/gate/interactive tests passed. Thirteen actual supervised
Chromium scenarios passed on independently configured /portal/access -> /auth/check
and /store/lookup -> /search/resolve documents, with custom mapped input/button
labels, field names and response booleans/statuses. Positive/negative login/search,
wrong fields/actions, preexisting marker, denied canary, fake success, absent marker,
duplicate submission, redirect and dropped response were verified. Thirteen
documents and eight POSTs reached the owned fixtures; zero canary/bad requests.
CI repeats the proof on Windows/Linux and uploads its value-free report.

This entry point remains internal. Saved configuration/review/API/queue and local
UI continue to admit the four fixed fixtures only. Next connect typed reusable
bindings to owner-scoped saved settings and explicit review confirmation without
loosening public HTTPS read-only policy or activating customer/private networks.

## Saved Reusable Local Binding Admission

Supervised binding implementation c67e7ac passed CI run 40075398787. Project settings
now accept one optional local_form_binding containing only operation, exact owned
document/endpoint URLs, ordered input names and typed accepted/rejected boolean
response assertions. Syntax validation never resolves values or authorizes a run;
metadata can remain saved when data-change permission is revoked. Removing the
binding disables reusable review. Existing configurations normalize unchanged.

Owner-scoped review builds the real contract from saved metadata, actual scoped
reference slots and an explicit operator-supplied completion mapping. The full
saved configuration and binding/response/field definitions enter its digest.
The same transactional queue revalidates that digest at submit/claim and uses the
reusable supervised child only for a typed LocalFormBinding. Existing fixed
fixture dispatch, license/shared capacity, cancellation, recovery and result
sanitization remain. No arbitrary environment reference or plaintext input is
accepted by the new admission routes.

Local-only POST routes /api/projects/{project_id}/interactive/local/review and
/api/projects/{project_id}/interactive/local/jobs take completion, optional timeout,
and (for jobs) confirmed_contract_fingerprint. Saved metadata supplies the target;
requests cannot override it. Fixed-fixture routes still require an explicit string
fixture ID and do not silently select reusable dispatch. All local jobs share the
existing bounded owned history/status/cancel routes and worker commands. Reviews
remain non-executing and no request directly launches Chromium.

Seven new persistence/HTTP/worker tests passed. The real reusable browser proof
now additionally saves two contrasting bindings through authenticated HTTP, reviews
and explicitly confirms each, and runs real scoped queue workers: positive login
and negative search both passed with one POST each. Combined contacts: fifteen
documents, ten POSTs, zero canary/bad requests; no plaintext credential persistence.
Thirty existing interactive tests, six binding tests, six settings tests and seven
fixed HTTP tests passed. TypeScript/production build and local UI proof passed.

The UI preserves saved reusable metadata during ordinary configuration edits and
hides the older fixed-fixture panel when such a binding is configured, avoiding
silent fallback. The browser UI test verifies preservation without target access.
A reusable binding editor/review panel is still needed; metadata can currently be
configured through the authenticated local API. Response support remains one
strict boolean JSON field and in-page form transitions; arbitrary HTML/native
navigation/authentication protocols are not claimed. General HTTPS remains
read-only and no customer/private-network activation is authorized.

## Reusable Local Form Editor and Confirmed UI Execution

Saved binding implementation 804e7fc passed CI run 40079778219. Local free/licensed
project settings now provide a typed reusable binding editor: operation, exact POST
endpoint, ordered HTML field names and positive/negative boolean JSON assertions.
Changing operations resets the operation-specific defaults explicitly. Saving
normalizes the draft and never starts a test. Disabling the editor removes the
saved binding. Inputs describe metadata only; credential/query values remain in
scoped worker environment references and are never entered through this editor.

The interactive panel uses saved reusable configuration and its dedicated review/
admission routes, with an explicit positive/negative expected outcome and completion
test ID. Any unsaved target, policy, reference, mapping or binding change blocks
review and clears existing confirmation. Outcome/marker/timeout edits also clear
confirmation. A fresh review and separate one-submission confirmation remain
required; the old fixed-fixture workflow remains supported when no reusable
binding is configured. Host and select controls now have stable accessible names.

A built-UI end-to-end proof used a fresh disposable free workspace/server on port
8894 and an owned fixture server. The operator configured/saved positive login and
negative search entirely through the UI, reviewed and confirmed each, then actual
supervised queue workers passed both runs. Exactly two initial documents and two
POSTs reached the fixtures; saving/reviewing made no target requests. The latest
persisted results and refreshed UI history were both checked. Unsaved-edit blocking,
confirmation invalidation, binding removal, mobile layout and metadata-only inputs
were verified. No UI external request, page error, malformed request or credential
value persistence occurred. Mobile screenshots were visually inspected.

TypeScript/production/demo builds, the new reusable UI proof, the prior interactive
operator UI proof, and the unchanged Pages demo checks passed. The demo still has
100 catalog definitions, zero API/external requests and execution disabled. CI now
runs/uploads the new UI-to-worker proof and screenshots. Exact-commit CI remains
pending after push. Next verify/download the combined exact-commit artifacts and
review remaining product limitations; general HTTPS still permits read-only
checks, and no public/customer credential submission or hosting activation is enabled.
