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
Authenticated screenshot delivery remains unfinished. API/database and mutating
test runs are unsupported by these endpoints.
