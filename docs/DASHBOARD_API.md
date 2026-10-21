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
submission. General target execution remains disabled. Plan review and run
execution endpoints are not implemented yet.
