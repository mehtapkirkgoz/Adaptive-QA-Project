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
