# Sprint 1 Acceptance Review

Review date: October 20, 2026
Status: Accepted. Implementation verified remotely on Linux and Windows.

Tracking: [issue #2](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/2).

## Acceptance Evidence

| Requirement | Evidence | Current result |
|---|---|---|
| Start a run and retrieve its result | Worker submit/run-next/status commands, persistent queue tests, smoke JSON snapshots | Verified locally |
| Reject unauthorized destinations | Guard unit tests and real canary checks | Verified for the controlled sample; public helpers tested offline |
| Enforce policy on redirects and outgoing traffic | Proxy redirect/resource/CONNECT/WebSocket/POST/fallback regressions | 9 browser checks passed locally |
| Release resources after timeout and cancellation | Real process-tree and persistent cancellation script | 3 real process checks passed on each OS |
| Distinguish failed assertions and execution errors | Result classification, evidence, and transport unit tests | Verified locally |
| Verify 10 smoke cases against the sample | Managed queue runner and artifacts/smoke/report.json | 10 cases passed locally with matching JSON/PNG evidence |

## Reproducible Checks

Run sequentially from the repository root, with the virtual environment active:

```powershell
python -m unittest discover -s tests -v
python scripts/check_process_lifecycle.py
python scripts/check_network_security.py
python scripts/check_local_browser.py
```

The lifecycle script uses real sleeping parent/descendant processes and a separate
CLI requester. It exercises the same supervisor and process termination code used
by browser jobs, without needing a browser installation. On Linux the descendant
starts a separate session, testing the detached-child case. A different fixture
owns a real worker lock and is abruptly terminated before recovery is attempted.
These lifecycle fixtures are not Chromium processes; real browser scenario coverage
is provided by the smoke and egress scripts.

## Required Remote Jobs

- scaffold
- Process lifecycle (ubuntu-24.04)
- Process lifecycle (windows-2025)
- Local browser check

Required downloadable artifacts:

- process-lifecycle-ubuntu-24.04: process report with 3 checks and passed=true.
- process-lifecycle-windows-2025: process report with 3 checks and passed=true.
- local-browser-evidence: security report, smoke report, JSON snapshots, and PNGs.

The verified [run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39465390109)
passed for implementation commit 811cc2adb1110f26f57aba4472013f92d83bdb9e.
All four jobs succeeded. All three downloaded artifact SHA-256 digests matched
GitHub metadata. The 10 result JSON records matched the smoke summary, and all
10 linked PNGs were present and valid. A sample screenshot was visually inspected.

## Explicit Scope Decisions

- Sprint 1 delivers a local sample prototype; arbitrary customer URL execution remains disabled.
- SQLite is the local durable queue adapter. Production Redis/Celery and PostgreSQL are not implemented.
- Public destination pinning/DNS helpers are tested offline, not against arbitrary external sites.
- Production OS/container isolation, tenant authorization, secret vaults, and private-network agents remain future scope.
- Interrupted-record recovery does not terminate orphan processes or undo prior side effects.
- There is no automatic replay or retry.

## Closure Checklist

- [x] Push implementation and verify all four jobs above.
- [x] Download and inspect reports for the same implementation commit.
- [x] Confirm 3 lifecycle checks per OS, 9 security checks, and 10 passed smoke cases.
- [x] Check all result JSON and linked PNGs; visually inspect a sample screenshot.
- [x] Record accepted prototype scope and verified evidence in issue #2.
- [x] Update README/Sprint 1 completion status and close issue #2 as completed.
- [ ] Close milestone #2 in GitHub after issue closure.

Issue #2 was closed as completed. Milestone closure remains pending: the connected tool does not support closing milestones and the available browser is not signed in.
