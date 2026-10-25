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
- [ ] Add a supervised public browser worker with guarded real document loading,
  per-input traffic restrictions, hard cancellation and masked evidence. The
  in-memory document prototype does not establish that runtime boundary.
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
