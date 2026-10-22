# Sprint 7 Acceptance — Local Authenticated Dashboard

Status: Technical acceptance complete; ready for owner review and closure.
Verified: 2026-10-22.
Implementation: `2608fc40919e8e530c07b434538f70ac4070f118`
[CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39742021256)
Owner tracking: [issue #8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/8),
[milestone #8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/8).

## Acceptance Scope

This accepts a local authenticated MVP against the controlled root fixture at
`http://127.0.0.1:8000/`. It does not enable arbitrary customer sites or deployment.

| Criterion | Verified behavior and evidence |
|---|---|
| Complete a run through the dashboard | Real built React login, project create/rename, saved target and reference configuration, discovery submission, separate discovery worker, current plan review, explicit LOGIN-001/SEARCH-001 selection, separate run worker, two actual passed outcomes and decoded screenshot |
| Owner isolation | SQL owner/project predicates, session-derived identities, forged-owner rejection, cross-owner/project/run denials, namespaced non-resolving secret references, anonymous 401 and other-owner 404 for actual screenshot requests |
| Progress and results | Persisted queued/running/cancel-requested/terminal states, bounded history, polling, ordered actual per-case statuses/durations, no invented results for unattempted cases, failed outcomes preserved independently from job completion |
| Integrated MVP | Built desktop/mobile React UI, same-origin loopback API, separately invoked guarded workers, SQLite project/job/result/evidence persistence, successful reload/logout checks and retained CI reports/screenshots |

## Controls Retained

Local accounts use salted scrypt hashes and bounded login admission. Opaque
session/CSRF token digests, expiry/revocation, Strict host-only HttpOnly session
cookies, exact Host/Origin checks, CSRF mutations, bounded bodies/deadlines and
no-store responses apply. Loopback HTTP cookies intentionally lack Secure.
Provisioning is interactive with hidden password input; there are no default
credentials or public registration endpoints.

Web settings store only owner/project/slot-bound environment references, not
secret values. The settings API never resolves them or reports their presence.
Discovery plans remain non-executing, with unknown evidence distinguished from
absence. An explicit run request additionally requires current owned completed
discovery, selected read-only UI definitions and an exact local-root binding.
API/database and mutating scenarios are not admitted by dashboard run endpoints.

The existing destination/redirect/proxy guards remain authoritative. Workers hold
the same OS execution/recovery lock, use guarded isolated browser processes and
poll cancellation/configuration changes. Per-case execution is bounded to 30
seconds; the run has a 120-second orchestration budget, bounded database waits and
process cleanup. Recovery never replays interrupted work. Valid earlier progress
survives interruption; late or obsolete-policy results are not committed.

Optional screenshot import bounds UUID paths, canonical containment, regular-file
identity, reparse/symlink handling, PNG structure/checksums, dimensions and 5 MiB
size. PNG BLOBs commit atomically with results and are retrieved only by owned
project/run/evidence IDs. Public JSON has no filesystem paths. Missing/invalid
optional evidence does not change actual assertion status.

## Evidence Review

All seven CI jobs passed for the exact implementation SHA above. Scaffold logs
confirm 500 unit tests. All six downloaded final-run archive SHA-256 digests and
recorded head SHAs matched. All 184 retained PNGs and 178 distinct filesystem PNG
references validated. The final retained mobile dashboard screenshot was visually
reviewed; desktop layout was also reviewed during implementation acceptance.

[Frozen verification manifest](evidence/sprint7-acceptance.json) records run/job
identity, archive IDs/digests and verification counts. Reports confirm 23 integrated
dashboard checks, both real passed dashboard assertions with evidence IDs,
separate discovery/run workers, actual screenshot decoding and anonymous/other-owner
denial. Databases/account files are not published in artifacts; screenshot BLOB
retrieval is exercised before temporary storage is removed.

Retained regressions confirm 40 queued UI scenarios, 96 shared fixture variants,
40 reverse/cleanup runs, 18 matcher controls, nine egress controls, four UI/API
bridge controls, five discovery budget cases, four contrasting discovery fixtures,
and 18 scripted AI controls with zero remote calls. Separate API evidence confirms
20 cases and 20 boundaries with zero forbidden canary contacts. Both OS database
reports confirm 15 cases, 19 boundaries, 15 reverse runs and unchanged files. Both
OS lifecycle reports confirm three checks; their CI steps also passed the four
cancellable discovery-supervisor tests. Artifact retention is seven days; the safe
verification manifest remains in the repository.

The acceptance-record commit changes documentation only. Verification applies to
the pinned implementation, not an unverified future implementation or deployment.

## Practical Limits and Deferred Scope

- Workers are explicit local one-job operator commands; HTTP only submits work.
- Dashboard execution supports registered read-only root UI fixtures, at most ten
  explicitly selected cases per run. There is no inferred API/database binding.
- The catalog remains 40 UI + 20 API + 15 database definitions; 500 unit tests are
  platform verification, not 500 website scenarios.
- SQLite storage, local admission and PNG BLOBs are a prototype. Retention,
  storage quotas, broader reports, exports and catalog growth belong to Sprint 8.
- Organizations/roles, password reset/MFA, production identity, HTTPS/reverse proxy,
  deployment, always-on worker operations and customer-hosted agents are deferred.
- Browser proxy controls are not an OS/container sandbox. No independent security
  audit or unrestricted-site readiness is claimed.
- Existing free local AI acceptance remains Sprint 6 evidence. This sprint's CI
  uses scripted AI regression controls and makes no paid model/customer calls.

The owner manages sprint closure and the next sprint start. Keep issue #8 and
milestone #8 open until owner review. Sprint 8 has not been authorized.
