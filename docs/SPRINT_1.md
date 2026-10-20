# Sprint 1 — First End-to-End Test Execution

Status: In progress. Local sample implementation is ready for remote verification and acceptance review.

Tracking issue: [#2](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/2)
Milestone: [Sprint 1](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/2)

## Current Phase Status

- [x] 1.1: Implement and locally verify destination and redirect controls for the supported sample workflow.
- [x] 1.2: Install Playwright/Chromium and create the controlled sample.
- [x] 1.3: Implement lifecycle management, failure classification, and local cleanup checks.
- [x] 1.4: Persist results and linked screenshots.
- [x] 1.5: Implement local persistent queueing, cancellation, deadlines, retry, and explicit recovery.
- [x] 1.6: Implement and execute 10 smoke scenarios.
- [ ] 1.7: Verify the latest GitHub jobs, downloadable evidence, and sprint acceptance criteria.

Completed marks describe the local sample implementation, not production readiness.
Production Redis/Celery, PostgreSQL, customer isolation, and OS network sandboxing remain planned deployment/scale work.

## Delivered Behavior

- Validated test definitions and structured execution outcomes.
- Host authorization, scheme/port policies, public IP validation.
- Deadline-bound DNS, checked numeric-IP connections, and peer verification.
- Fixed browser proxy with loopback bypass disabled and no direct fallback.
- Redirect prevalidation and per-connection authorization.
- Request/redirect budgets and explicit read-only sample policy.
- Fresh context and isolated process per test, with total timeout.
- Persistent FIFO jobs, status filters, pending/active cancellation, and finalization.
- Retry lineage and interrupted-record recovery protected by an OS lock.
- JSON snapshots, complete PNG evidence, and smoke/security summary reports.

## Smoke Cases

LOGIN-001 through LOGIN-004, SEARCH-001 through SEARCH-004, NAV-001 and NAV-002.

The demo login case uses fake values and only verifies the sample status message.
It does not test real authentication. Each case uses explicit Python assertions.

## Verification — October 20, 2026

- 172 unit tests pass.
- 9 real Chromium egress checks pass using local canaries.
- All 10 queued smoke scenarios pass through the isolated worker/proxy path.
- The managed runner verifies JSON/queue consistency and valid PNG evidence.
- Python compilation and dependency checks pass.
- Earlier Windows checks verified active cancellation, process-tree timeout handling, and lock release after abrupt worker termination.

## Security Regression Coverage

Authorized redirects succeed. Unauthorized redirects, script navigation,
subresources, HTTPS CONNECT, WebSockets, and POST requests are denied before
forbidden connections. Redirect loops hit the budget. A stopped proxy does not
cause Chromium to connect directly.

Offline public-guard tests cover private/mixed DNS answers, DNS changes,
numeric-IP pinning, connected peer validation, ambiguous URLs, and resolver deadlines.

## Remaining Acceptance Work

- [ ] Push this checkpoint and verify scaffold and browser jobs.
- [ ] Inspect security/smoke reports and JSON/PNG artifacts in GitHub Actions.
- [ ] Verify Linux process-tree termination and OS lock behavior separately.
- [ ] Review issue #2 acceptance criteria and explicitly record any deferred scope.
- [ ] Close README status, issue, and milestone only after acceptance.

## Boundaries

The CLI remains restricted to the controlled sample. Public guard helpers are
not a production browsing service. OS/container network isolation and customer
private-network policy remain deployment work. TLS tunnels are not decrypted.
Recovery repairs queue records; it does not stop orphan processes or reverse
side effects. There are no automatic retries.

## Change Record

Sprint 1 progressed through browser execution, evidence, persistent queueing,
active cancellation/recovery, and catalog expansion. This checkpoint combines
the seven remaining scenarios and destination/redirect hardening into one commit
as requested. Earlier checkpoint details remain available in Git history.
