# Sprint 4 — API Testing

Start date: October 21, 2026 (Europe/Istanbul)
Status: In progress — phases 4.1 through 4.5 completed locally.
Tracking: [issue #5](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/5).
Milestone: Pending creation and association by the repository owner.

## Goal

Execute configured API checks against a controlled local fixture, with explicit
authentication references, structural/business assertions, redacted outcomes,
and enforced destination, mutation, response-size, and execution limits.

## Phases

- [x] 4.1: Define API configuration, request, and assertion contracts.
- [x] 4.2: Implement bounded pinned-destination transport and safe reporting.
- [x] 4.3: Add controlled positive/negative API coverage toward 60 combined cases.
- [x] 4.4: Add explicit UI/API validation bindings.
- [x] 4.5: Verify missing configuration, secrets, mutation policy, redirects, and deadlines.
- [ ] 4.6: Verify same-commit CI/artifacts and close after acceptance.

## Phase 4.1 Deliverables

Immutable API configuration references an authorized project origin and an optional
environment-based bearer token. Raw authentication strings are rejected. Requests
use explicit ASCII paths, typed methods, bounded query pairs, and bounded JSON
bodies. Read methods cannot carry bodies; non-read methods must declare data changes.
Limits reject unbounded timeouts, oversized responses, path traversal, duplicate
query keys, and invalid/non-finite JSON bodies.

JSON assertions use typed path components and explicit exists/type/equality/range/
length operators. This is a bounded assertion subset, not full JSON Schema or
OpenAPI validation. Query/body/expected operands are excluded from repr; later
reports must serialize only explicit safe outcome fields, never whole request models.
All 280 unit tests pass, including 12 API contract cases. No transport or runnable
API coverage is claimed at this checkpoint. Remote verification follows push.

## Phase 4.2 Deliverables

The transport authorizes and connects to the fixed local origin through the
existing numeric-IP guard. It does not follow redirects or use environment proxy
settings. Socket and response-size limits apply; encoded responses are rejected.
The isolated hard total deadline for slow streams is a separate phase 4.5 gate.
Requests resolve bearer tokens only from environment references and reject header
controls. Mutating methods require both a declared data change and project policy.

Strict JSON parsing rejects duplicate keys, non-finite literals, and floating-point
overflow. Assertions distinguish booleans from numbers and missing paths from null.
Results contain only case ID, status, duration, and generic reasons/assertion
indexes. Payloads, headers, tokens, and expected operands are never serialized.
Missing configuration/authentication produces blocked outcomes; assertion and
transport failures remain distinct. All 290 unit tests and a real pinned local
health request pass. Customer execution and public API transport remain disabled.

## Phase 4.3 Deliverables

The stateless local API fixture supports health, items/search, authentication,
scope rejection, HEAD, payload validation, and quantity business rules. Twenty
distinct API definitions pass against real HTTP, bringing combined coverage to
60 cases without changing the forty-case UI registry. See [API catalog](API_CATALOG.md).
The fixture generates no persistent backend data. Non-read methods still declare
data changes and require explicit project authorization. The harness generates
its bearer token in memory/environment and checks it is absent from safe reports.

All 292 unit tests and 20 API scenarios pass locally. A separate CI API job writes
outcome-only result records and a report under `local-api-evidence`. Hard total
API isolation and hostile-response boundaries remain phase 4.5 work; execution
is still restricted to the controlled loopback origin.

## Phase 4.4 Deliverables

Explicit project/UI/API identifiers bind a trusted passing UI result to configured
API assertions. Missing/wrong-project configuration or failed UI prerequisites
prevents API execution. Each API result must retain its case identity; adapter
errors and wrong identities become errors. Independent layer outcomes are kept
and neither layer changes the other's expected result.

A combined static-UI/stateless-API fixture verifies the same configured no-results
search input across a real isolated UI run and API response. Four checks cover
success, failed UI, missing API configuration, and an intentional API mismatch.
The bridge report contains result metadata only and is retained with browser
evidence. These repeated validations do not increase the 60-case catalog count.
All 299 unit tests pass locally. This is an explicit sample binding, not inferred
customer endpoint discovery or automatic execution of a generated plan.

## Phase 4.5 Deliverables

The API adapter runs each case in a hidden isolated child process with a hard
total deadline and cancellation support. The parent validates result identity,
size, status, and absence of payload evidence. Private temporary inputs contain
configuration/test data only; bearer values are resolved in the child from the
environment. Temporary inputs/results are removed after execution. Reports must
never publish these private input files. Socket/size limits remain independently
enforced; process-tree cleanup may require additional teardown time after deadline.

Twenty real boundary checks verify missing configuration/secrets, denied writes,
invalid/injected authentication, reflected-token/header redaction, oversized and
malformed responses, duplicate keys, numeric overflow, unsupported encoding/media,
redirect credential isolation, slow-header/body deadlines, idle timeout, and
prestart/active cancellation. Canary contacts stay zero. API catalog and UI/API
bridge runs use the isolated adapter. All 307 unit tests pass locally; the 20
API scenarios and four bridge checks also pass. Same-commit CI/artifact acceptance
is the remaining gate. No public/customer API execution is enabled.

## Acceptance Criteria

- [ ] Controlled positive and negative API cases pass.
- [ ] Missing API configuration has an explicit non-execution reason.
- [ ] Secrets and response payloads do not appear in reports/logs.
- [ ] Target and mutation policies and execution budgets are enforced.
- [ ] UI/API bindings preserve independent expected outcomes.
- [ ] Catalog counts reflect runnable behavior, not cosmetic variations.
- [ ] Remote CI and downloaded artifacts are verified before closure.

## Boundaries

Do not infer customer API endpoints or credentials from a site URL. Initial
execution remains confined to registered local fixtures. Public/customer API
execution, private network access, database validation, AI, and deployment
remain outside the initial adapter. A small explicit JSON assertion contract
will not be described as full JSON Schema/OpenAPI support.

## Baseline

Sprint 3 was accepted with 40 runnable UI cases, 268 unit tests, 96 variant runs,
40 reversed runs, and verified CI/artifacts. The owner confirmed milestone #4 closed.
API cases remain blocked by the existing UI-only planner until a compatible API
execution/configuration contract is implemented. No API coverage is claimed yet.
