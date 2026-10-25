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

- [ ] Separate reviewed execution authority from a non-executing proposal; do not
  broaden the existing local worker's accepted types.
- [ ] Prove a one-shot HTTPS transport on owned TLS fixtures only: numeric IP pinning,
  verified SNI/certificates, no redirects/reconnect/retry/proxy/cookie inheritance,
  bounded bodies and response assertions, sanitized outcomes and uncertain delivery.
- [ ] Add supervised child deadlines, cancellation, configuration/owner checks,
  secret handling and evidence masking before any queue/UI admission.
- [ ] Require an explicit per-operation local review/confirmation. URL-only read-only
  checks must never silently acquire form-submission authority.

No public/customer form has been contacted or enabled by this foundation.
