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
