# Sprint 7 — Web Dashboard and Project Management

Started: 2026-10-21, explicitly authorized by the owner after closing Sprint 6 issue #7.
Status: In progress
Issue: [#8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/8)
Milestone: [#8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/8)

## Delivery Phases

- [x] 7.1: Persist owner-scoped projects and verify cross-owner access boundaries.
- [x] 7.2: Add credential/session authentication and local web security controls.
- [x] 7.3: Expose authenticated project/configuration APIs with secret references.
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

### Phase 7.3 configuration delivery

Owner-scoped GET/PUT configuration endpoints now persist the bounded target URL,
one to ten distinct normalized exact hosts, an explicit boolean data-change
policy, and optional secret references. The existing ProjectConfig contract
validates target membership. Credentials, URL query/fragment values, extra fields,
wildcards and malformed hosts are rejected. Full replacement removes omitted
references; invalid input preserves the previous saved configuration.

Each secret slot has a generated owner/project/slot-specific environment variable
name. Arbitrary names and references from another owner, project or slot are
rejected. API responses mask values and never resolve references or reveal
environment presence. The database contains reference names only. No target
connections, DNS lookups, SQL, AI or job creation occurs on save. Future worker
resolution must retain these ownership constraints.

Six persistence tests and three additional HTTP tests verify settings persistence,
rename independence, atomic rejection, policy reset, reference removal,
cross-owner isolation, CSRF denial and environment non-resolution. A real Chromium
check saves and reads target settings and a masked login-password reference.
Prior commit `2f4c4147ad9b59366645f312db54eddd469cd02e` passed GitHub CI run
39650505615; the current increment requires its own CI result. React dashboard
implementation is the next unfinished phase. See DASHBOARD_API.md for contracts.

All 445 local unit tests and the real Chromium authentication/project/settings
check passed for this increment. Current-commit CI remains pending after push.

### Phase 7.4 partial delivery: React project workspace

The pinned React/TypeScript/Vite frontend now provides sign-in/out, paginated
owner projects, create/rename, target and allowed-host settings, data-change policy,
and masked reference selection. Loading, empty, error and successful-save states
are explicit. Password inputs clear after submission; credentials/session tokens
are not kept in browser storage. Desktop and narrow mobile layouts were visually
reviewed using fixture screenshots. No run buttons imply executable support.

The loopback Python server optionally serves only built index/assets with the API
on the same origin. CSP permits local scripts/styles without unsafe-inline or
external resources. Source files and databases are not served. Request replay now
delivers the bounded body once and then preserves disconnect handling, fixing a
static-file response hang found by the real browser check.

The build performs strict TypeScript checking. The browser acceptance script uses
temporary accounts/storage to verify invalid login, cleared password input,
owner-filtered listing, create/rename, settings, reload persistence, masked values,
mobile width and logout persistence. It rejects JavaScript errors or external
requests. CI builds with Node 24, runs that script and retains fixture screenshots.
Two HTTP tests additionally verify static-file security and private-file denial.
Plan review is not implemented, so phase 7.4 remains incomplete. Previous commit
cc8216f passed CI run 39652672378; this increment needs its own CI result.

All 447 unit tests, the TypeScript/Vite build, the built dashboard browser check,
and the existing authentication/project/settings browser check passed locally.

### Phase 7.4 partial: conservative saved-plan review

The owner-scoped plan endpoint and React review section now display catalog and
decision counts, per-case reasons, and explicit non-execution status. Previewing
uses the existing planner with an empty, explicitly limited crawl: no discovery
job exists yet, so zero inspected pages and unknown features are retained. All
75 catalog definitions remain blocked; configured references are not API/database
adapter bindings. Data-change permission never authorizes execution. No target
connection or secret resolution occurs. Unsaved form changes are excluded, and
the preview clears on configuration save, project switch or logout.

Three service tests and one HTTP test verify no fabricated findings, no network
or secret resolution, owner isolation, missing configuration, and no authorization
when data changes are enabled. Chromium checks review counts, all 75 decisions,
and the explicit lack of execution permission. Phase 7.4 remains partial until
worker-backed discovery can supply evidence. Prior UI implementation fdd17e1
passed CI run 39688525407; this increment requires current-commit CI.

All 451 local unit tests, strict TypeScript/Vite build and the actual built React
browser check passed. Current implementation CI will be checked after push.

### Phase 7.5 foundation: owner-bound discovery dispatch

A separate dashboard discovery queue now binds every job to its owner and project
inside the project database. Submission atomically checks ownership, saved settings
and admission, then stores an immutable configuration snapshot without secret
references. Only the fixed `http://127.0.0.1:8000/` root fixture is admitted; arbitrary
targets and routes remain disabled. At most five active jobs per owner and one
hundred globally are admitted. These are local admission limits, not commercial
quotas or a production capacity claim.

Owner reads/cancels constrain both project and user inside SQL; missing and
other-owner jobs share one error. Trusted workers claim queued work atomically
with a random claim token that public job views and repr omit. Claim checks gate
finalization. Queued cancellation prevents claiming; active cancellation persists
and wins over success/error finalization. Finished claims cannot be reused. The
legacy unowned test queue is unchanged and is not exposed by dashboard routes.

Six real-storage tests cover persistence, frozen policy, excluded references,
ownership, wrong-project denial, cancellation precedence, forged claims, concurrent
claim uniqueness and bounded/local-only admission. No dashboard job HTTP endpoints,
worker loop, discovery process, progress UI or report persistence is wired yet.
Crash recovery and actual hard-deadline/cancellation integration remain necessary
before this queue is used by a worker. Phase 7.5 remains incomplete. Previous
implementation fd06142 passed CI run 39694904241.

All 457 local unit tests passed for this dispatch-core increment. Current-commit
CI remains pending after push. No browser flow changed in this increment.

### Phase 7.5 discovery supervision and recovery controls

The existing guarded local discovery supervisor now accepts a trusted cancellation
callback, checks it before spawn, while waiting and before accepting results, and
terminates the owned process tree on active cancellation or hard deadline. Partial
results are discarded and return explicit cancellation/time limitations with a
non-executing plan. Callback failures also clean up the child. Destination guards,
the fixed local target and read-only browser policy remain unchanged.

Dashboard discovery recovery acquires the same OS worker lock intended for the
executor. It refuses a live worker lock, marks interrupted running work as error,
finalizes interrupted cancellation as cancelled, clears claim tokens, and never
replays work. Queued jobs are preserved. A future worker must hold this lock for
its complete execution; no worker loop or job endpoint is wired yet.

Four supervisor tests launch real owned replacement Python children to verify
pre-cancellation, active cancellation, timeout and cleanup after callback failure.
Two queue tests cover interrupted states, stale claims and active-lock rejection.
CI runs supervisor tests on both Linux and Windows process jobs. These tests
validate supervision, not additional website scenarios. Previous implementation
7796f2b passed CI run 39700937077. Phase 7.5 remains incomplete until actual
worker/report and HTTP integration is delivered.

All 463 local unit tests and five guarded real-browser discovery scenarios passed.
The existing timeout mock was updated to represent a still-running child under
the polling supervisor; real-child timeout/cancellation tests independently verify
termination. Current-commit Linux/Windows CI remains pending after push.
