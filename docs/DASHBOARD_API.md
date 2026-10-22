# Local Dashboard API

Status: Sprint 7 in progress. Bind only to numeric loopback using the documented
`dashboard serve` command. This is a local HTTP prototype, not a public deployment.
No default account exists. See SETUP.md for interactive provisioning.

## Authentication

`POST /api/auth/login` takes exactly `email` and `password` in a JSON object.
Successful responses contain only the user ID and set host-only Strict SameSite
session/CSRF cookies. Session cookies are HttpOnly. Tokens must not appear in URLs
or logs. `GET /api/auth/me` returns the current user ID. `POST /api/auth/logout`
requires the readable CSRF cookie value in `X-CSRF-Token` and revokes the session.

All mutations require `Content-Type: application/json` and the exact configured
Origin (`http://127.0.0.1:8765` by default). Authentication failures return a generic
401. Other invalid input returns a masked 400; missing/wrong Origin is 403 and an
unsupported content type is 415. Bodies are bounded to 2 KiB and five seconds.
All responses use `Cache-Control: no-store`. Forwarded headers, ambiguous security
headers/cookies and compressed request bodies are rejected.

## Projects

Every project request requires a valid session cookie. Mutations also require
`X-CSRF-Token`. Caller-provided owner identities never authorize access.

| Method | Path | Input | Success |
|---|---|---|---|
| POST | `/api/projects` | Exactly `{"name":"Project name"}` | 201, project ID and name |
| GET | `/api/projects` | Optional `limit` (1–100), `offset` (0–100000) | 200, projects, limit, offset |
| GET | `/api/projects/{project_id}` | None | 200, project ID and name |
| PATCH | `/api/projects/{project_id}` | Exactly `{"name":"New name"}` | 200, project ID and name |

Names must be nonblank strings of at most 100 characters without control
characters. Project IDs are server-generated lowercase UUID hex strings. Invalid
IDs return 400; missing and other-owner valid IDs both return the same 404.
Lists contain only the signed-in owner's projects, newest first. Duplicate or
unknown pagination keys are rejected. Query strings on other endpoints are denied.

## Project Configuration and Secret References

`GET /api/projects/{project_id}/configuration` returns `configured: false` until
settings are saved, plus `available_secret_references` for the four supported
slots: `login_username`, `login_password`, `api_token`, and `database_path`.
Reference names are generated from the authenticated owner ID, project ID, and
slot. Use these exact names; arbitrary environment variables and references from
another project, owner, or slot are rejected.

`PUT` on the same path replaces the entire configuration. It requires a session,
CSRF header, exact Origin and JSON content type. The exact input fields are:

```json
{
  "base_url": "http://127.0.0.1:8000/",
  "allowed_hosts": ["127.0.0.1"],
  "allow_data_changes": false,
  "secret_references": {}
}
```

The target URL is bounded to 512 characters and cannot contain credentials,
query parameters or fragments. One to ten distinct normalized exact hostnames
are required; the base URL must match one. Wildcards and ports in host entries
are rejected. The data-change policy must be a JSON boolean. References are an
optional subset of the supported slots inside the required `secret_references`
object; replacing that object with `{}` removes the saved references.

Saved responses include the target settings and reference names with each value
shown as `[REDACTED]`. This API neither resolves environment variables nor reports
whether they exist. It never accepts raw passwords, tokens or connection paths.
Reference binding authorizes no execution or secret read by itself; future workers
must enforce the same owner/project binding when resolving them.

Missing and other-owner configurations have the same 404 response. Invalid
configuration returns a masked 400 and leaves the previous saved settings intact.
Saving performs no DNS lookup, target connection, SQL validation, AI call or job
submission. General target execution remains disabled. Run
execution endpoints are not implemented yet.

## Saved-configuration Plan Preview

`GET /api/projects/{project_id}/plan` requires the owner's session and returns
409 until target settings are saved. It uses only stored settings, not unsaved
form edits. It does not perform discovery, resolve secrets, enqueue jobs or visit
the target. Cross-owner and missing projects share 404; anonymous access is 401.

The response separates total catalog size (75 definitions) from selected,
skipped and blocked decisions, includes per-case reasons and seven feature
statuses, and always has `execution_authorized: false`. Current discovery status
is `not_run`, with zero inspected pages and unknown feature states. Consequently
all cases remain blocked: UI prerequisites lack evidence, while API/database
cases also need explicit adapter bindings. Enabling data changes or adding secret
references does not create such evidence or authorize execution. This is a
conservative preview; worker-backed discovery and execution remain unfinished.

## Owned Discovery Jobs

All paths below are under `/api/projects/{project_id}` and require the owner's session:

| Method | Path | Behavior |
|---|---|---|
| POST | `/discovery` | Exactly `{}`; enqueue local discovery, return 202 |
| GET | `/discovery` | At most 20 newest jobs, excluding reports |
| GET | `/discovery/{job_id}` | Status and reduced report if completed |
| POST | `/discovery/{job_id}/cancel` | Exactly `{}`; cancel queued work or request active cancellation |

Mutations require Origin and CSRF. Extra owner/target/execution fields are denied.
HTTP requests never run browsers or start workers. Use the separate
`dashboard discovery-once` operator command. Only saved root settings for
`http://127.0.0.1:8000/` are admitted, with five active jobs per owner and 100 globally.
Invalid configuration/admission returns masked 400; missing/other-owner/wrong-project
jobs share 404. Lists never include worker claim tokens or report payloads.

Completed reads include `configuration_current`, comparing the frozen target,
hosts and data-change policy with current saved settings. The UI refuses to use
a mismatched report as the current plan. Historical reports are preserved. Plans
never authorize execution. Cancelled/error jobs do not expose a success report.
The UI restores recent jobs, polls active states and supports cancellation/review.
Polling stops on unmount, terminal state or error. This is read-only discovery;
starting UI/API/database test runs remains unfinished.

## Explicit UI Test Runs

All paths below are under `/api/projects/{project_id}` and require the owner's session:

| Method | Path | Behavior |
|---|---|---|
| POST | `/runs` | Exactly `discovery_job_id` and `case_ids`; queue an admitted run, return 202 |
| GET | `/runs` | At most 20 newest owned runs with bounded per-case outcomes |
| GET | `/runs/{run_id}` | Read owned status, requested IDs and recorded results |
| POST | `/runs/{run_id}/cancel` | Exactly `{}`; cancel queued work or request active cancellation |

Mutations require Origin/CSRF. `case_ids` must be an array of one to ten distinct
selected read-only UI IDs bound to the local root in an owned completed, current
discovery report. The server rejects stale/incompatible evidence, other owners,
extra fields and unsupported cases. Admission never executes tests in HTTP.
Run the separate `dashboard run-once` worker against the controlled fixture.

The panel requires explicit checkbox selection before Start selected tests is
enabled. It restores/polls history, supports cancellation and displays each
actual outcome and duration. Completed job status is not a claim that all tests
passed. Unattempted cases have no outcome. Results omit claim tokens, raw adapter
messages and filesystem paths. Missing/other-owner/wrong-project runs share 404.
Authenticated screenshot delivery is described below. API/database and mutating
test runs are unsupported by these endpoints.

## Run Reports and JSON Export

Owner-session GET endpoints under `/api/projects/{project_id}/runs/{run_id}`:

- `/report`: complete persisted-result report.
- `/report/status/{status}`: filtered rows for passed, failed, skipped, blocked,
  cancelled or error. Unknown filters return 400.
- `/report/download`: complete JSON attachment named `test-run-report.json`.

All three are read-only, no-store and enforce project/run ownership. Anonymous
access returns 401 and other-owner/missing records return 404. Query parameters
remain rejected. Filtering does not change aggregate counts. Lifecycle state,
catalog size, requested cases, recorded outcomes and unrecorded cases are separate.
No success/skip status is invented for an unattempted case. The report contains
reduced persisted messages and optional opaque evidence IDs, never screenshot
bytes, raw adapter text, credentials or filesystem paths. Export is a snapshot
at download time; an active run may have additional outcomes later.

## Reruns and Historical Comparison

`POST /api/projects/{project_id}/runs/{run_id}/rerun` requires owner session,
Origin/CSRF and exactly `discovery_job_id` and `case_ids`. It queues a fresh run
(202) with `rerun_of` lineage. The parent must be finalized; selected IDs must
be a non-empty subset of the parent's requested IDs and admitted by current
discovery/configuration. Existing target, read-only and quota restrictions apply.
Neither old results nor screenshots are copied into the new run.

`GET /api/projects/{project_id}/runs/{run_id}/compare/{baseline_id}` compares two
different finalized owned runs. Saved policy and common case contract hashes
must match; otherwise `comparable=false` with an explanation and no change rows.
Legacy runs without contract hashes cannot establish comparability. Rows contain
only case IDs, recorded statuses or null, and a change category. Active/self
comparisons return 400; anonymous/other-owner access remains 401/404. Neither
comparison nor export executes tests. Fixture state may differ; this API does
not infer flaky tests or performance regressions.

## Screenshot Evidence Storage

`GET /api/projects/{project_id}/runs/{run_id}/evidence/{evidence_id}` requires the
owner's session and exact project/run/evidence binding. Recorded outcomes contain
an opaque `evidence_id` only when a validated optional screenshot was captured.
Anonymous access returns 401; another owner, run or unknown ID returns 404.
Path/query overrides are rejected. There are no public artifact URLs or upload APIs.

The response is bounded image/png, with no-store, nosniff and a fixed display
filename. The server reads a run-bound database BLOB, not a caller-specified path.
Worker import accepts at most one UUID-named PNG from the trusted screenshot
directory, with a 5 MiB byte cap, dimensions up to 20,000 per side/40 million pixels,
regular-file/reparse checks and PNG structural/CRC checks. Unsupported text/EXIF
metadata and animation are omitted. Invalid or absent optional evidence does not
change assertion status. Retention and storage quotas are future Sprint 8 scope.
