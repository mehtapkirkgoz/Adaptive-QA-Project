# Sprint 7 — Web Dashboard and Project Management

Started: 2026-10-21, explicitly authorized by the owner after closing Sprint 6 issue #7.
Status: In progress
Issue: [#8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/8)
Milestone: [#8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/8)

## Delivery Phases

- [x] 7.1: Persist owner-scoped projects and verify cross-owner access boundaries.
- [x] 7.2: Add credential/session authentication and local web security controls.
- [ ] 7.3: Expose authenticated project/configuration APIs with secret references.
- [ ] 7.4: Build the React/TypeScript dashboard for project and plan review.
- [ ] 7.5: Bridge authorized run start/cancel/progress to separate worker execution.
- [ ] 7.6: Display owner-scoped history/results/evidence and test cross-owner denial.
- [ ] 7.7: Demonstrate the integrated local MVP and review exact-commit CI/evidence.

## Phase 7.1 Delivered

A separate SQLite dashboard project store persists random project IDs, owner
IDs, and bounded display names. Read/list/update queries constrain ownership
inside SQL. Missing and other-owner records produce the same outcome. Stable,
bounded pagination and parameter binding are implemented. No target execution,
queue mutation, credentials, raw secrets or evidence paths are stored here.

The typed actor is a trusted internal identity, not authentication. Future HTTP
handlers must derive it from validated server sessions, never request bodies or
owner headers. There are no public dashboard endpoints in this phase. Existing
queue storage remains separate until run ownership is explicitly integrated.

Eight real-database tests verify persistence, owner isolation, denied updates,
non-enumerating errors, pagination, identity preservation, bound SQL-looking names,
and invalid inputs. All 405 local unit tests pass. HTTP authentication, the web
panel and integrated run flow remain unfinished. No domain/deployment or customer
site execution is authorized by this sprint start.

## Phase 7.2 Progress

The internal authentication core provisions local accounts with unique random
salts and scrypt N=2^17, r=8, p=1 hashes. Passwords require at least 12 characters
and at most 256 UTF-8 bytes; no plaintext password is stored. Two KDF slots bound
concurrent expensive hashing. This is a local prototype, not open registration,
email verification, password reset, MFA, or a production identity service.

Successful login issues independent random session/CSRF tokens. Only their SHA-256
digests are persisted. Public grant representations omit tokens. Session lookup
derives the trusted project actor; expiry and logout revoke access. CSRF comparison
is session-bound, and at most ten sessions per account remain valid. Per-identity
admission permits five attempts per 60-second window with a bounded persistent
identity table; failed attempts consume admission before hashing, and unknown
accounts perform a dummy KDF. Missing/wrong/throttled credentials share one error.

The initial core increment passed nine real-storage/KDF tests and 414 total unit
tests. The HTTP increment below extends that baseline to 420 passing unit tests
and a successful real Chromium authentication check. Subsequent increments below
complete the local phase; integrated sprint acceptance still requires current CI.
Credentials
and tokens must never be accepted as frontend-supplied owner identities.

Reviewed implementation references:

- [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [Python 3.13 password KDF functions](https://docs.python.org/3.13/library/hashlib.html#key-derivation)

### Local HTTP authentication increment

The FastAPI composition root now provides login, current identity, and logout.
Only the fixed numeric loopback Host is accepted; forwarded headers and query
strings are rejected except bounded project-list pagination. Mutations require the exact configured Origin and JSON
content type. Actual body bytes are capped at 2 KiB, including chunked requests,
with a five-second receive deadline. Login has an additional process-local global
limit of twenty attempts per minute, including malformed credentials; the
persistent per-identity limit remains in force. This global limit assumes one
local server process and resets on restart.

Session cookies are host-only, HttpOnly, Path=/ and SameSite=Strict. The separate
readable CSRF cookie supplies the session-bound header required for logout.
Cookies intentionally lack Secure only for this numeric-loopback HTTP prototype;
this app is not a production HTTPS deployment configuration. Responses forbid
caching and framing, restrict content loading, and do not echo passwords or raw
session tokens. OpenAPI and interactive documentation endpoints are disabled.
There is no registration or run execution endpoint. Project mutations were added
in the subsequent increment below.

Six HTTP tests exercise real persisted accounts and sessions. A real Chromium
check verifies login identity, cookie attributes and JavaScript visibility,
missing-CSRF denial, logout, revocation and cookie removal. The browser check is
included in CI and writes a value-free local evidence report. The subsequent
increments add local operator commands and raw request-boundary coverage.
Prior increment CI passed at
`692d2eca918f5ad1dc2f3f461e5927ea36089dc4` (run 39648849144); this increment
requires its own CI result after push.

### Trusted local operator commands

`python -m adaptive_qa dashboard create-user` now provisions an account through
interactive, hidden password entry and confirmation. Redirected input is refused;
there are no password arguments, default credentials, or public registration.
`dashboard serve` binds only to numeric loopback, with one process, no proxy-header
trust or access logging, and a 32-connection concurrency limit. Both commands use
the same ignored dashboard database by default. No persistent account has been
created by development checks. The interface and project endpoints remain pending.

Six CLI tests verify real provisioning/login, absent credential output,
noninteractive and mismatched-password rejection, invalid-port rejection before
database creation, unavailable hidden input, and safe server options. The full
425-test suite passed before the final hidden-input regression test was added;
all six CLI tests then passed. Operator instructions are in SETUP.md.

### Phase 7.2 local delivery and phase 7.3 project API increment

Raw ASGI tests now exercise actual chunked bytes with absent/false Content-Length,
disconnects, a real five-second stalled-body deadline, duplicate security headers,
duplicate session cookie names, and unsupported body encoding. Denials retain
no-store response headers. Strict JSON parsing rejects duplicate keys, non-finite
constants and invalid encodings without echoing input. Local authentication
delivery is complete; production identity features remain outside this prototype.

Session-authenticated project APIs now support create, list, read and rename.
Mutations require the session-bound CSRF header as well as the existing Origin
check. Only project ID and display name are returned. Owner fields in JSON are
rejected; owner headers cannot change the session-derived actor. Other-owner and
missing projects return identical 404 responses. Pagination accepts only unique,
bounded limit/offset values on the project list; other query parameters are denied.

Six HTTP project tests verify persistence, cross-owner read/update denial,
non-enumerating errors, forged ownership, CSRF/anonymous denial, stable filtered
pagination, and masked invalid inputs. The Chromium check additionally creates,
renames, lists and reads a project using the actual cookie/CSRF flow. Project
target configuration, secret-reference APIs, React views, worker integration and
owner-scoped evidence delivery remain unfinished. Project APIs do not enqueue jobs
or execute plans, target requests, API calls, SQL, or AI calls.

All 436 unit tests passed locally. The final body-buffer allocation adjustment
was then rechecked with all four raw boundary tests. The real Chromium project
and authentication check also passed. Exact-commit CI is pending after push;
this is phase progress, not integrated sprint acceptance.
