# Explicit Local API Review

The existing API catalog contains controlled example contracts. Website discovery
does not establish API endpoints or make those contracts applicable to another API.
The catalog remains 34 API definitions, within the unchanged 100-case total.

`local_api_review.py` adds an internal reusable read-only contract path. An operator
supplies a typed ApiCase with an explicit request path, HTTP status and bounded JSON
assertions. No endpoint or expected response is inferred from the website URL.
Only the owned `http://127.0.0.1:8000` origin and its exact hostname allowlist are
supported. GET/HEAD requests have no body, query, authentication or data-change
authority. This does not enable public/customer API execution.

Reviewing is offline and does not resolve environment references. Its fingerprint
binds all project fields and the complete case contract. The internal execution
entry point requires the exact confirmed fingerprint and current typed project;
changed settings/assertions invalidate the review before dispatch. Execution uses
the existing isolated API child, numeric destination guards, 15-second total
deadline and cancellation callback. Raw response bodies are not persisted.

The entry point is not a dashboard route or customer worker. Before exposing it to
customers, add owner-scoped saved API settings/review, current license/capacity
admission, queue leases/cancellation, explicit UI confirmation and corresponding
end-to-end evidence. A direct internal function does not supply those permissions.
Existing saved plans remain non-executing and API-token references alone do not
establish an executable binding.

Three unit checks cover offline review, confirmation/configuration drift, restricted
origins and request authority, and bounded child dispatch. The owned HTTP proof uses
two contrasting endpoints and configurable boolean assertions: two expected passes
and one expected failure, exactly three GET requests. Review, stale configuration
and pre-dispatch cancellation produce no requests. CI repeats the proof and uploads
its value-free report with the API evidence.

## Saved Settings and Scoped Review

Project configuration now accepts optional `local_api_binding` metadata with four
exact fields: `path`, `expected_status`, `json_field`, `expected_boolean`. The first
saved profile is an unauthenticated GET with one explicit top-level boolean
assertion, a 2xx/4xx status and a bounded normalized path. It requires the exact
owned API origin above. Unknown fields, values masquerading as booleans/statuses,
query strings and authority/path escapes are rejected. Null removes the binding;
invalid replacements preserve the prior saved configuration.

Local free/licensed apps expose POST
`/api/projects/{project_id}/local-api/review` with an empty JSON object. It requires
the existing local session, Origin and CSRF checks and reads one owner-scoped saved
snapshot. The review fingerprint includes the complete saved settings plus the
typed API contract, so changing policy, references or assertions changes it.
The response explicitly says `execution_authorized: false`. It does not resolve
references, contact the endpoint, create a run or reserve licensed capacity.

The current dashboard preserves this metadata on unrelated saves; an API editor
and queue admission are not implemented yet. This endpoint therefore provides
review only. Three persistence/HTTP checks verify restart, foreign ownership,
configuration drift, invalid replacement/removal and session/Origin/CSRF guards.

The HTTP configuration endpoint explicitly accepts the optional binding as well
as the persistence layer. A browser regression caught a missing field in that HTTP
allowlist; it was corrected and the HTTP tests now save valid/invalid replacements
through the real PUT endpoint. The free browser drill also verifies that reloading
and saving unrelated dashboard settings preserves a previously saved API binding,
alongside real discovery/LOGIN-001 execution and zero external browser requests.
The shared-settings regression completed 805 tests (804 passed, one Windows
permission skip); focused HTTP and browser checks passed after the allowlist fix.
