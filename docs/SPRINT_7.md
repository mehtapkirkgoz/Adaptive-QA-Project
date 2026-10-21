# Sprint 7 — Web Dashboard and Project Management

Started: 2026-10-21, explicitly authorized by the owner after closing Sprint 6 issue #7.
Status: In progress
Issue: [#8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/8)
Milestone: [#8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/8)

## Delivery Phases

- [x] 7.1: Persist owner-scoped projects and verify cross-owner access boundaries.
- [ ] 7.2: Add credential/session authentication and local web security controls.
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
and a successful real Chromium authentication check. Phase 7.2 remains in progress.
Credentials
and tokens must never be accepted as frontend-supplied owner identities.

Reviewed implementation references:

- [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [Python 3.13 password KDF functions](https://docs.python.org/3.13/library/hashlib.html#key-derivation)

### Local HTTP authentication increment

The FastAPI composition root now provides login, current identity, and logout.
Only the fixed numeric loopback Host is accepted; forwarded headers and query
strings are rejected. Mutations require the exact configured Origin and JSON
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
There is no registration, run execution, or project mutation endpoint yet.

Six HTTP tests exercise real persisted accounts and sessions. A real Chromium
check verifies login identity, cookie attributes and JavaScript visibility,
missing-CSRF denial, logout, revocation and cookie removal. The browser check is
included in CI and writes a value-free local evidence report. Local account
provisioning/server launch commands and additional request-boundary integration
coverage remain before phase 7.2 is accepted. Prior increment CI passed at
`692d2eca918f5ad1dc2f3f461e5927ea36089dc4` (run 39648849144); this increment
requires its own CI result after push.
