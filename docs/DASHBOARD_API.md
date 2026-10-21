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

These endpoints manage display names only. Target configuration, secret
references, plan review and run execution endpoints are not implemented yet.
Creating or renaming a project never starts a test or connects to a target.
