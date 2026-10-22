# Sprint 9 Acceptance — HTTPS Demo and Managed Local Runtime

Status: Technical acceptance complete; ready for owner review and closure.
Date: 2026-10-22
Tracking issue: [#10](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/10)
Milestone: [#10](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/10)

Implementation: `3982f404fb350671a9bd49b86878eb32550a5808`.
CI: [run 39830200667](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39830200667).
Implementation evidence is frozen separately from this documentation commit.

## Owner-Approved Delivery

The owner selected a public GitHub Pages interface demo while real automation
runs locally, and explicitly authorized public repository visibility. No domain,
server, subscription or paid service was purchased. This acceptance applies to
that adjusted delivery recorded in SPRINT_PLAN.md and SPRINT_CONTROL.md.

| Criterion | Delivered behavior |
|---|---|
| HTTPS interface | Published static demo with 100 definitions, filters, illustrative report and responsive layouts |
| Separate data | Validated environment directories and numeric loopback local origin; hosted activation rejected |
| Reviewed packages | Committed-source wheel, compiled dashboard, dependency locks, digest and schema support checks |
| Local activation | Explicit trusted preparation, bounded extraction/inventory, atomic release/data selection and stale-selection refusal |
| Process boundaries | One lease per role, maintenance exclusion, selected-wheel imports, bounded supervisor and existing worker deadlines |
| Recovery | Verified backup, private restored copies, additive migration, revoked sessions and cancelled pending work |
| Actual rollback | Historical wheel serves again against the preserved restored data generation, retaining post-upgrade projects/results |
| Operations | Bounded storage health, component status, value-free logs, operator commands and incident/backup procedures |

Existing test/deployment plans remain non-executing. Preparing/selecting a package
does not start services. Only explicit local-run starts a bounded component.
Result lifecycle never substitutes for assertion success; a completed queue job
may contain failed cases. Invalidated work produces a nonzero component outcome.

## Runtime Drill

The actual sequence uses historical package
`a71bc2c69140b3d4bd993be7495ab2d360f8decc` and the implementation package above:
old/live → new/restored → old/restored. It exercises real HTTP serving/login,
CSRF-protected project creation, packaged discovery and UI workers, LOGIN-001 and
SEARCH-001 assertions, and two persisted PNGs. Switching while serving is refused.
Old sessions are rejected after restoration. Binary rollback keeps the new
project and completed run. Original live database bytes and a valid backup remain
unchanged. Component leases release after stopping and after supervisor timeout.
All fixtures/accounts are disposable local test data.

The local Windows drill passed against the exact implementation package.
CI repeats the same sequence on Linux and Windows. Earlier unsuccessful Windows
attempts are excluded: a test fixture and then worker-owned evidence used short
TEMP aliases. Trusted temporary roots are now canonicalized at creation;
noncanonical/untrusted evidence guards were preserved. Failed drill cleanup stops
the child before deleting its temporary directory.

## Verified Evidence

All twelve CI jobs succeeded on the exact implementation SHA. The scaffold log
confirms 588 passing unit tests. Twelve downloaded artifact SHA-256 digests and
head SHAs were verified. Both packaged runtime reports confirm every drill check
above, including two passed cases and two persisted PNGs per platform. The safe
permanent record is [the verification manifest](evidence/sprint9-acceptance.json).

Regression artifacts confirm 51 queued UI cases, 51 reversed-order cases with
cleanup/context isolation, 34 API cases and 20 API boundaries with no forbidden
canary contacts, and 15 database cases plus 19 boundaries on both platforms.
The demo check preserves all 100 definitions, subpath navigation, synthetic
report labels and 390/768/1440-pixel layouts with zero API/external requests.
Actual HTTPS publication has separate evidence in sprint9-pages.json.

## Limits and Owner Review

The public [demo](https://mehtapkirkgoz.github.io/Adaptive-QA-Project/) has no API,
credentials, persistent user data or test execution. General customer website
execution is not enabled: accepted adapters use controlled fixtures and explicit
contracts. The catalog remains 51 UI, 34 API and 15 database scenarios; fixture
variants do not increase scenario counts.

Managed local processes do not provide production OS CPU/memory quotas,
unattended service management, central alerts, hosted backend TLS, customer agents
or a production cloud deployment. Those infrastructure prerequisites are deferred.
Operators must stop unmanaged legacy processes before offline maintenance and
protect private data directories using filesystem permissions. Digests detect
corruption, not publisher authenticity; trusted release review remains explicit.

Issue and milestone remain open for owner review. Sprint 10 requires an explicit
owner start. See LOCAL_RUNTIME.md, OPERATIONS.md and DEPLOYMENT.md for commands and
operational boundaries.
