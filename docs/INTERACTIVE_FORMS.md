# Controlled Interactive Form Contracts

This is a non-executing foundation, prepared while local-first remote acceptance
is pending. No worker, UI admission, new catalog scenario or external form
submission is enabled by this increment. Existing LOGIN-001/SEARCH-001 structural
checks still do not fill fields or submit forms. The 100-case catalog is unchanged.

## Fixed Input and Assertion Contract

A frozen InteractiveFormContract binds one project and the exact saved-configuration
fingerprint to a typed login or search operation. Login takes two distinct typed
environment references (username/password); search takes one query reference.
Plaintext input values, unbounded reference names and arbitrary operation strings
are rejected. Construction, validation and fingerprinting never resolve a secret
or contact a target. Future project admission must additionally authenticate the
owner and verify scoped reference names; this model does not grant that authority.

The contract pins an explicit completion mapping: login.accepted/login.rejected or
search.results/search.empty. Changing the completion mapping, input references or
configuration changes its digest. A future worker must prove the completion marker
was absent before one permitted submission and visible afterward; an already
visible marker cannot establish a successful transition. This assertion requirement
is included in the digest but is not implemented as execution in this increment.
AI must not replace a failing assertion or choose a different expected result.

Both operations require explicit project data-change permission, including search:
a form can create sessions, audit records or other side effects. There is one
submission maximum and a bounded five-to-thirty-second operation timeout. These
limits supplement the existing outer process deadline; retries must not repeat a
submission. A changed project/configuration blocks the contract. Project host
allowlisting alone is not enough to authorize a form submission.

## Next Execution Work

After local-first CI/artifact acceptance, add a separately supervised controlled
fixture worker. Before resolving input references it must validate current licensed
admission, exact saved target/profile, form ownership and unique enabled controls,
form action/method and destination/IP guards. Initial proof stays on contrasting
owned loopback fixtures. Customer/public-site credential submission is not enabled.

Input values must remain out of argv, saved configurations, JSON reports and
screenshots. Evidence capture requires an explicit masking/redaction strategy;
structural screenshot code must not be reused blindly after filling a password or
query. Child output is bounded and sanitized; cancellation/deadline/ambiguity must
stop execution. Only after positive/negative, no-retry, wrong-destination,
credential-canary and cleanup checks pass should a separate admission/UI integration
be considered. Keep existing plans non-executing and do not mark catalog entries
executable until their workers and acceptance evidence exist.

## Controlled DOM Probe Increment

An internal probe now exercises client-side form transitions on controlled local
URLs using a caller-owned fresh context that denies all other network traffic.
This is not a supervised child worker or dashboard admission. Its runner fulfills
the initial document from an in-memory fixture and aborts every other request; no
real login endpoint or external site receives inputs. No screenshot/trace is taken.

The probe validates project/configuration/data-change permission, unique connected
controls, field types, effective form/button action/method/target and an absent
completion marker before resolving environment references. It checks the action
and marker again after filling to catch input handlers that mutate them. It
attempts one click and requires the pinned marker afterward. Results use fixed
sanitized messages rather than Playwright exception text. The caller must dispose
the context, retain a network-denial signal and eventually provide hard process
supervision before this can become an executable product scenario.

Sixteen real Chromium scenarios passed: accepted/rejected login, Turkish names,
results/empty search, pre-existing or input-triggered markers, wrong form/button
action, POST method, ambiguous submit, unmasked/missing password, absent transition,
input-mutated action and a denied credential-canary request. Blocked preconditions
resolve no references; no scenario submits more than once. A missing transition
fails and a network attempt returns error. Four contract tests also passed.
The meaningful 100-case catalog and all external execution permissions are unchanged.
Next: supervised child transport/deadline/cancellation and contrasting owned HTTP
fixtures, then explicit licensed admission/UI integration.

## Supervised Fixed-Fixture DOM Probes

A separate interactive_process child now receives only typed project/contract
metadata, environment reference names and a fixed fixture ID through bounded
private JSON. Values are not resolved in the parent or placed in argv/configuration.
The child revalidates exact fields/types/project/fingerprint and fixed fixture
bindings. It fulfills the single initial document from a committed in-memory
registry and denies all subsequent HTTP/WebSocket traffic. No server endpoint
receives a submission, no arbitrary HTML input is accepted and no evidence
screenshot/trace is produced. This remains internal verification, not catalog
execution, licensed queue admission or a general interactive website worker.

The parent enforces a finite process deadline, pre/active cancellation, sanitized
callback errors and owned process-tree cleanup using the existing cross-platform
termination implementation. Output is bounded and admits only fixed message/status
combinations. A terminated or failed child reports attempted_submissions=null when
the count is unknown, rather than asserting zero or making an automatic retry.

Seven supervisor tests passed for pre-spawn policy checks, strict reference-only
transport, sanitized results and real owned-child deadline/cancellation/callback
cleanup. Eight actual child/Chromium cases passed for positive/negative login/search
transitions, missing completion, denied canary traffic, a busy renderer deadline and
active cancellation. Every owned root process exited. CI repeats unit supervision
and actual browser probes on Windows and Linux. Shared process-tree termination
has separate cross-platform descendant lifecycle coverage.

Next: prove contrasting owned HTTP fixtures under a separately reviewed submission
transport. Preserve target/IP guards and never reuse the read-only policy to allow
arbitrary POSTs. Licensed admission, form endpoint/method binding, process-safe
secret resolution and redacted evidence must be verified before exposing this
through the product. The 100-case catalog and current external execution scope
remain unchanged. Exact-commit CI for this increment is pending after push.

Verification checkpoint: the full regression completed 745 tests (744 passed,
one Windows permission skip). The seven supervisor tests passed after the final
child-start error handling/test change; all eight actual Chromium child scenarios
passed. The preceding DOM-only implementation 49b81e4 also passed all twelve CI
jobs in run 40042269203. This supervised increment awaits its own exact-commit CI.

## Owned HTTP Document Fixture Proof

The same supervised probe can now load the initial document from the fixed owned
HTTP fixture origin instead of fulfilling it from memory. The transport source is
an exact typed/validated IPC field; fixture IDs still bind the operation and exact
127.0.0.1:8000 path. The existing EgressProxy/DestinationGuard pins and checks that
one initial GET and its peer IP. The child verifies that the proxy authorized
exactly one request and that a 200 HTML document loaded at the exact bound URL.
All later requests and WebSockets remain denied, including form submissions.

Eight actual Chromium child scenarios also passed against the owned HTTP server
with contrasting control names. Eight initial documents were received; zero
non-GET requests, unexpected GETs or contacts to the separate 8001 canary server
were observed. Login/search transitions remain client-side fixture demonstrations,
not credential validation by an HTTP authentication endpoint. Seven transport
tests and the eight in-memory scenarios also passed after the source-field change.
CI repeats both document sources on Windows/Linux and uploads separate reports.
No screenshot/trace, product admission or external/customer interaction was added.

Next required work is a separately bound owned-fixture submission endpoint contract
and one-shot request transport. Do not loosen the read-only discovery proxy or
treat this document-only HTTP proof as permission to send arbitrary POST requests.
Existing plans stay non-executing and the catalog stays at 100 meaningful cases.

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

Regression checkpoint: 757 tests completed (756 passed, one Windows permission
skip). The final browser proof also passed all fourteen scenarios after exact-body
arming and cancellation-after-POST coverage were added.

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

Operator admission regression: 783 tests completed (782 passed, one Windows
permission skip). The earlier interrupted local invocation produced no acceptance
result; this completed fresh run is the regression checkpoint.

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

The full existing fourteen-scenario supervised browser proof and saved/mapped
queue probes passed again after the shared response-dispatch refactor: seventeen
documents, eleven POSTs, zero canary/unexpected/bad-body contacts.

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

The original fourteen browser scenarios plus saved/default/mapped queue proof also
passed after the IPC changes: seventeen documents, eleven POSTs, zero canary,
unexpected or malformed forwarded requests. Exact-commit CI remains pending.

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

Regression checkpoint: 796 tests completed (795 passed, one Windows permission
skip). The seven saved-binding tests also passed after the final fixed-route
source-conflict guard. Static demo build/browser checks passed unchanged, with
zero API/external requests and execution disabled. Exact-commit CI is pending.
