# Non-Executing Public HTTPS Form Proposals

Follow-up to the owner's request to continue functional coverage. This foundation
reuses the existing local engine's typed login/search contracts and reference-only
inputs. It does not add a worker, queue route, UI submission control or customer
execution. PublicFormProposal.execution_authorized is always false.

A proposal pins the exact HTTPS document and a distinct endpoint on the same
origin, operation-specific field names, explicit completion mapping, saved project
fingerprint, input references and distinct positive/negative boolean response
expectations. URL syntax is bounded and canonical: default port 443, no credentials,
query, fragment, encoded path, dot segment or cross-origin endpoint. Private IP
literals and loopback names are rejected without DNS. DNS names are not established
as public by offline validation; a future worker must validate all resolved IPs,
pin its numeric peer and verify TLS hostname/certificates before contacting it.

Matching project validation requires existing data-change permission, even for
search, the exact saved document, one allowed origin and the current configuration
fingerprint. It grants no execution authority. The codec contains metadata only;
input reference names remain in the existing form contract, and actual values are
never resolved. Fingerprints bind the document, endpoint, field names, input
references, completion expectation, response expectations and future one-POST,
no-redirect/8192-byte request/1024-byte response limits.

The deliberately narrow response model is reused from the local contract. It is
not a promise that arbitrary login/search pages return boolean JSON. HTML responses,
redirect-based login, cookies, bearer authentication, third-party authentication,
CAPTCHA, checkout/payment and general business workflows are not supported by this
proposal. No result may be inferred from HTTP 200 alone.

## Verified Foundation

Seven proposal tests and ten existing local/interactive contract tests passed.
Construction, validation, codec round-trip and fingerprints run with DNS, sockets
and input resolution forbidden. Negative cases cover private/cross-origin URLs,
noncanonical paths/ports, missing permission, stale/wrong project configuration,
extra plaintext/authority fields, invalid response types and wrong field counts.
Changing endpoints, fields, inputs or completion/response assertions changes the
fingerprint. Existing local decoder, submission gate and process dispatcher reject
this proposal; no process is spawned. The 100-case catalog, current UI and saved
owner data are unchanged. Exact-commit CI remains pending for this new foundation.

## Next Required Implementation

Response-contract child acceptance: aaea425 / Core 40216894876, twelve successful
jobs and verified archives, 220 validated PNGs. Windows/Linux and installed-wheel
reports each passed the twenty-check internal submission proof. Evidence is in
evidence/public-child-ci-aaea425.json. This proves the scoped response child, not
a public browser workflow or customer deployment. The sections below retain the
sequence of implementation checkpoints; earlier pending statements are historical.


- [x] Separate reviewed execution authority from a non-executing proposal; do not
  broaden the existing local worker's accepted types.
- [x] Prove a one-shot HTTPS transport on owned TLS fixtures only: numeric IP pinning,
  verified SNI/certificates, no redirects/reconnect/retry/proxy/cookie inheritance,
  bounded bodies and response assertions, sanitized outcomes and uncertain delivery.
- [x] Add an internal supervised response-contract child with hard deadlines,
  cancellation, exact owner/project reference slots and private bounded IPC.
- [x] Prototype reviewed form control/action preconditions and require both the
  verified HTTP response and pinned UI transition on controlled fixtures.
- [x] Add an internal supervised public browser worker with guarded real document
  loading, per-input traffic restrictions and hard cancellation. Credential-bearing
  workflows deliberately produce no screenshots/traces; the parent owns and removes
  their private browser profile, including after a hard timeout.
- [ ] Add authenticated owner/queue/configuration admission before connecting UI
  controls; trusted caller-supplied owner/fingerprint metadata is not authentication.
- [ ] Require an explicit per-operation local review/confirmation. URL-only read-only
  checks must never silently acquire form-submission authority.

No public/customer form has been contacted or enabled by this foundation.

## Internal Controlled TLS Transport

ReviewedPublicForm is a separate exact-fingerprint confirmation wrapper. It is not
proof of a person's identity or endpoint ownership; future authenticated local
admission must provide that authority and prevent job/review replay. Public proposals
remain non-executing and existing local workers/gates still reject both types.
The internal PublicSubmissionTransport has no queue or UI route and must not be
called from an event-loop/web handler without a supervised child.

Nine new owned TLS tests and 22 proposal/local submission tests passed. The gate
consumes even a malformed attempt and admits at most one concurrent attempt per
transport instance. All DNS answers must be public; only the first validated numeric
peer is attempted. TLS verifies its authorized hostname with system trust, without a
production connector or verification override. Requests do not inherit environment
proxies, cookies or authorization headers. Responses must meet exact bounded boolean
JSON assertions; redirects, credential echoes, duplicate fields, oversized/encoded
responses and wrong types are errors. Lost POST responses retain uncertain delivery
and are never retried. Inputs and raw exception text stay out of outcomes/reports.

The TLS harness redirects an already validated public test identity to an owned
loopback socket using test-only monkeypatches and a temporary CA. It does not prove
Internet/customer deployment or enable a production private-network bypass.
CI now runs this proof on Windows/Linux and uploads a safe report with lifecycle
evidence. Hard total deadlines, cancellation, scoped reference resolution, owner/
configuration admission and browser completion/evidence checks remain unfinished;
socket timeouts alone do not bound slow streams. No UI/customer activation is added.

## Supervised Response-Contract Child

The internal run_isolated_public_submission runner validates the confirmed proposal,
exact project/configuration snapshot and canonical owner/project input slots before
spawning. Metadata is bounded reference-only JSON in a private temporary directory;
argv contains paths only. The child revalidates metadata, checks all DNS answers and
pins the selected peer before resolving environment inputs. The transport reuses
that pinned target rather than resolving again. Actual values stay inside the child.
TLS key logging is disabled, including inherited SSLKEYLOGFILE. No screenshot or raw
HTTP response is produced. Results contain fixed codes and a conservative submission
count, never raw exceptions or inputs.

The parent has a finite total deadline and kills its owned process tree on timeout,
cancellation or a failed cancellation source. Accepted/rejected outcomes mean only
that the fixed HTTP boolean response contract matched; they are not TestResult or
catalog/browser passes. Lost response, killed child or invalid child output retains
uncertain delivery and never causes replay. Existing local/browser workers remain
unchanged and reject public proposal/review types. No queue/UI admission is connected.

Local validation: 888 regression tests completed with one Windows permission skip.
The focused owned transport/process proof now has twenty checks: real TLS child
submission, blocked private DNS before reference resolution, missing inputs, slow
stream termination, cancellation/failed callback cleanup, malformed result rejection,
owner/reference isolation and earlier TLS/one-shot failure boundaries. Final TLS key
logging and result-schema guards are included in the focused proof. The installed
release verifier now also requires this proof outside the checkout, with parent and
supervised child package paths pinned to the installed wheel. Exact-commit CI/artifact
acceptance is pending for this new child increment.

Next work is browser control/action validation and completion/evidence, then separate
authenticated queue/admission confirmation. Do not map a response-contract acceptance
to a successful website workflow or silently submit forms from the automatic URL flow.

## Controlled HTTP/UI Transition Prototype

The internal public_form_probe module validates exact project/owner reference slots,
editable connected controls, masked password types, effective form action/method,
field names and an absent pinned completion marker before resolving inputs. Its
trusted caller must freeze unrelated traffic and pin the POST peer before input
resolution, compare the browser's exact POST with the reviewed input serialization,
and forward only the asserted boolean response. After filling it rechecks action,
field names, marker absence, page identity and network cleanliness. A marker alone
cannot pass: the matching accepted/rejected HTTP outcome and the explicit UI marker
must both be observed after one attempted submission. Fixed sanitized messages are
returned; this prototype takes no screenshots or traces.

Fourteen real Chromium scenarios passed using owned documents fulfilled in memory
and four actual POSTs to an owned loopback TLS harness: positive search, Turkish
login, negative search, pre-existing/input-triggered markers, wrong action/fields,
unmasked/ambiguous controls, changed action, blocked canary/altered body, marker-only
spoofing and absent completion after a valid HTTP response. Preconditions resolve
zero input references where appropriate. Nothing contacts a customer/Internet site.
This is an internal prototype, not a supervised public browser worker or UI feature.

CI and installed release verification now require the same fourteen-case prototype
with accurately limited scope reports. Exact-commit acceptance for this prototype
remains pending; aaea425 acceptance above covers only the preceding response child.
Continue with the real guarded browser worker, masked evidence and authenticated
queue/admission review. The URL-only automatic flow stays read-only.

## Supervised Guarded Browser Increment

The new internal public_browser_process entry point requires the separately confirmed
proposal, matching project snapshot and exact owner/project reference slots. It uses
the shared bounded private child transport and caller cancellation hook. A fresh
persistent browser profile is created only inside the parent-owned temporary directory;
it is never a user's normal browser profile. Closing, cancellation and timeout remove
that directory. Windows sharing/access locks receive at most twelve bounded cleanup
attempts; persistent failures are surfaced, never silently ignored. One early pre-fix
synthetic development profile remains in local TEMP because a manual cleanup command
was blocked by tool policy. New proof runs verified removal of every new profile;
no owner workspace or real customer input was involved in that failed test.

Real document loading uses the existing numeric-IP egress proxy with HTTPS verification,
QUIC/HTTP2/non-proxied WebRTC UDP restrictions, a single exact main document and at most
one hundred read requests. Redirect navigation, extra frames and popups are rejected.
Service workers/downloads are disabled. After destination preflight and before reading
inputs, unrelated traffic is frozen. Only the one exact endpoint, method and serialized
reviewed body may be forwarded through the verified one-shot HTTPS transport. A second
POST is blocked without overwriting the first delivery's count. The browser receives
only the matched flat boolean JSON response. Both that response and the pinned DOM
transition are required for a pass. No screenshot, trace or raw page/response body is
returned. Debug/TLS key logging and unrelated canonical project reference variables
are removed from child environment inheritance.

Seventeen supervised real browser scenarios passed on owned TLS documents/endpoints:
positive login/search and negative search, same-origin script loading, pre-existing
markers, wrong actions, marker-only/missing/contradictory transitions, canary/altered
body/duplicate POST, private DNS, untrusted browser TLS, document redirect, missing
input and a slow TLS response. Eight owned POSTs occurred in total; no case submitted
more than once. The slow response was killed with uncertain delivery. All seventeen
private profile directories were removed. Full regression: 895 tests with one existing
Windows permission skip; 34 focused proposal/transport/child tests also passed.

The positive browser harness uses an ephemeral owned certificate SPKI pin through a
TEST-ONLY launch-options monkeypatch, alongside the test-only numeric connector.
Production exposes neither override and explicitly retains ignore_https_errors=False;
the untrusted-browser-certificate scenario runs without that test pin and sends no POST.
These are controlled fixture proofs, not Internet/customer deployment acceptance.
CI now runs the browser proof on Windows/Linux and requires it again from the installed
wheel outside the checkout. Exact-commit artifact acceptance is recorded below.

Saved personal-project review foundation now supports an explicit `public_https`
metadata profile. Saving remains syntax-only, including when data changes are disabled;
review requires the exact saved owner/project references, explicit completion mapping,
one matching HTTPS origin and data-change permission. Revalidation rejects changed
settings. Review performs no DNS, input resolution or queue admission. The existing
local execution queue rejects this separate review type. Six focused tests cover
ownership, stale settings, policy, profile/origin validation and non-execution.
The full 900-test regression passed with one existing Windows permission skip;
the subsequently added local-queue rejection test passed in the six-test focused suite.
Core 40221004605 at fde37698c766055da13bc40ad215f1ad85841d57 completed all twelve
jobs successfully. All twelve archives passed SHA-256/size/ZIP checks and 220 PNGs
were validated. Windows, Linux and installed-wheel browser reports each contain the
expected seventeen scenarios/eight owned POSTs with every new private profile removed;
three supervised transport reports each passed twenty-one tests. Exact evidence:
[public-browser-ci-fde3769.json](evidence/public-browser-ci-fde3769.json).

Internal personal-project admission now requires `submit_public` with the exact
current contract fingerprint. Legacy `submit` still rejects HTTPS reviews. The shared
transactional queue preserves existing local snapshot shapes and capacity accounting;
HTTPS snapshots carry an explicit profile. Claims, cancellation, result finalization
and recovery revalidate saved settings and retain claim-token checks. The worker dispatches
only to the supervised public browser process and stores status/attempt count, never
adapter messages or inputs. Thirteen focused tests cover review and queue behavior;
the existing eight local queue tests also pass. Full regression: 906 tests passed with
one existing Windows permission skip; the two final snapshot/finalization tests also
passed in the focused suite. No public HTTP route is enabled yet.

Local free/licensed HTTP integration adds separate HTTPS review and confirmed-job
endpoints inside the existing single-device branch. The local session, Origin/CSRF,
strict body schema, owner lookup and data-change controls apply to both endpoints.
Shared authenticated mode exposes neither endpoint. Review and enqueue never resolve
inputs or contact targets. Four HTTP tests cover non-execution, current confirmation,
CSRF/Origin, missing projects, stale configuration, permission and shared-mode exclusion.
The complete 912-test regression passed with one existing Windows permission skip.
The owner preview remains on the previously accepted native-check runtime; these new
workflows have not been activated there.

The owned TLS browser driver now also verifies five saved-review/queue scenarios:
positive search/login, expected-negative search, duplicate POST and missing input.
All five produced the expected statuses, four total owned POSTs, sanitized persisted
results and cleaned private profiles. This runs without HTTP/UI activation or customer
targets. CI requires it on Windows/Linux and the installed-wheel verifier runs it away
from the checkout as well. Exact-commit acceptance for this driver increment is pending.
The queue report explicitly marks its controlled fixture queue admission as enabled;
public backend and owner-preview activation remain false. This distinguishes the real
queue demonstration from the earlier direct-browser-only proof.

The same English workspace now includes an optional HTTPS form profile in its existing
form settings. Automatic URL checks remain read-only. Review shows the one POST endpoint
and exact expected status/boolean before separate permission confirmation. Saved setting
or marker edits clear the confirmation. The source UI proof saved/reviewed/confirmed
and cancelled an HTTPS job without contacting any target; both existing owned local
login/search worker executions still passed. Mobile screenshots were visually inspected
and had no overflow. TypeScript/Vite build and the existing interactive dashboard proof
also passed. This is a deliberately narrow optional contract workflow, not general
automatic end-to-end form discovery.

Next: exact-commit queue/HTTP/UI acceptance and installed proof, then preserve/upgrade
the owner preview only after those checks pass. Do not add automatic public form submission to the URL-only flow.
Keep shared/multiuser public workflows disabled until separately specified. Existing
local interactive bindings, closed Sprint 10 tracking and the public demo remain intact.

Preview build isolation: the existing process on port 8766 serves `frontend/dist`
directly. A source build briefly replaced its files during verification; the accepted
c48eaff dashboard was restored from the SHA-256-verified release archive, assets first
and index last, without restarting the process or touching the workspace database.
The served index was checked against that restored bundle. Future candidate builds
must use a separate output directory and `ADAPTIVE_QA_VERIFY_UI` for UI proofs while
the preview uses this folder. Release builds already use an isolated source export.

Installed verification completed locally for the inactive 61dba4b bundle: all four
manifest files verified, the 100-case catalog preserved, licensed/local UI recovery,
native checks, twenty-one transport tests, seventeen direct browser scenarios and five
saved queue scenarios passed. The actual bundled interface also saved/reviewed/confirmed
and cancelled an HTTPS workflow with zero target contacts, while two existing local
form submissions passed through installed worker processes. The verifier now requires
this installed form UI proof in CI. Core 40223033502 at 61dba4b was cancelled, not
accepted; do not substitute the local proof for exact-commit CI acceptance. Core
40222978429 at 020450a completed successfully; its archive acceptance is next.
