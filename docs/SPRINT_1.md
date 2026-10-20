# Sprint 1 — First End-to-End Test Execution

Status: In progress

Tracking issue: [#2](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/2)
Milestone: [Sprint 1](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/2)

## Goal

Execute browser tests against a controlled sample application
and persist results and evidence.

## Implementation Phases

- [ ] 1.1: Define and test destination policies.
- [ ] 1.2: Install Playwright and create a controlled sample application.
- [ ] 1.3: Implement browser lifecycle management and the first test.
- [ ] 1.4: Persist results and generate evidence.
- [ ] 1.5: Introduce queued execution and cancellation.
- [ ] 1.6: Expand coverage to 10 smoke test cases.
- [ ] 1.7: Verify CI and sprint acceptance criteria.

## Execution Boundaries

- General network execution remains disabled until destination controls are verified.
- The controlled local sample uses the explicit 127.0.0.1:8000 development policy.
- Local development requires an explicit policy for the sample application.
- Production workers must enforce destination restrictions independently
  of application-level URL checks.
- Data-changing tests must respect project policy.

## Completion Evidence

To be recorded as implementation progresses.


## Phase 1.1 Progress

Implemented:

- Scheme and effective port validation.
- Public destination IP validation.
- Exact project hostname authorization before DNS resolution.
- Validation of every resolved destination address.
- DNS failure handling and duplicate address removal.

Verification: 61 unit tests pass locally across the project.

Remaining before browser execution:

- Explicit local sample policy is implemented; complete redirect enforcement remains pending.
- Apply destination policies to browser requests and redirects.
- Enforce connection-level destination restrictions.
- Bound DNS resolution time as part of the execution timeout.

Phase 1.1 remains in progress.


## Phase 1.2 Progress

- [x] Create the controlled sample page.
- [x] Install Playwright 1.64.0 and Chromium locally.
- [x] Verify Chromium startup and shutdown.
- [x] Record pinned runtime dependencies.
- [x] Configure CI to install pinned dependencies.
- [ ] Verify pinned dependency installation in GitHub Actions.
- [x] Connect the sample application to browser execution.


## Phase 1.3 Progress

- [x] Open the controlled sample application with Playwright.
- [x] Verify the sample page and login form.
- [x] Close browser resources through finally blocks.
- [x] Return a structured result with elapsed duration.
- [x] Distinguish assertion failures from execution errors.
- [x] Verify result classification with five isolated unit tests.
- [x] Verify resource cleanup on success, setup errors, and simulated navigation timeout.
- [ ] Verify process-level timeout and queued worker cancellation separately.
- [x] Configure automated browser execution in CI (remote verification pending).

Local verification: 71 unit tests pass.
The local browser check has also been verified manually.
## Current Checkpoint — Phase 1.4 (October 20, 2026)

- [x] Persist structured test results as JSON.
- [x] Capture screenshots after successful local checks.
- [x] Link existing screenshots through the optional evidence_paths result field.
- [x] Verify evidence serialization and omit missing screenshot references.
- [x] Execute the real local browser scenario and verify its JSON references a PNG.
- [x] Capture failure evidence without replacing the original test outcome.
- [x] Configure automated browser execution in CI (remote verification pending).

Current local verification: 78 unit tests pass; one local browser scenario passes.
Phases 1.1 and 1.3 still have pending controls and automated lifecycle checks.
Phase 1.4 remains in progress. Queueing, cancellation, and the 10-case catalog
have not been implemented. Current changes await GitHub CI verification after push.

## Failure Evidence Checkpoint — October 20, 2026

- Capture screenshots before closing the page after assertion or execution errors.
- Preserve the original test outcome if screenshot capture or storage fails.
- Publish screenshot files only after a complete write.
- Verify assertion preservation and screenshot/storage error handling in unit tests.

Verification: 82 unit tests pass. Real Chromium runs verified both passed and
intentionally failed assertions with valid PNG evidence. The sample source was
not modified; the failure was served by a temporary local test server.
Phase 1.4 remains in progress pending browser CI coverage. Current changes await
GitHub Actions verification after push.

## Browser CI Checkpoint — October 20, 2026

- Add a local runner that owns the sample server lifecycle.
- Run the browser command with a 60-second process timeout and propagate failures.
- Add a separate Linux browser CI job and install Chromium system dependencies.
- Upload sample JSON/PNG evidence on success or failure with seven-day retention.

Local verification: the managed runner passes and all 82 unit tests pass.
Remote verification pending: both `scaffold` and `Local browser check` jobs must
pass after push; verify the downloadable `local-browser-evidence` artifact.
Phase 1.4 remains in progress until that remote verification is complete.

## Browser Lifecycle Checkpoint — October 20, 2026

Four additional unit tests verify context/browser cleanup after successful
execution, context creation failure, page creation failure, and a simulated
Playwright navigation timeout. The timeout test also checks that available
page evidence is retained and the original exception is preserved.

Local verification: 86 unit tests pass. No runtime dependency changes.
This checkpoint does not complete process-level timeout/cancellation testing
or confirm the pending GitHub browser CI run.

## Phase 1.5 — Local Queue Foundation (October 20, 2026)

- [x] Implement FIFO submission and atomic claims in a local in-memory queue.
- [x] Cancel queued jobs and skip them during claiming.
- [x] Attach matching results only to running jobs.
- [x] Distinguish job completion from test success.
- [x] Verify competing claims do not execute a job twice within one process.
- [x] Connect local queue jobs to browser execution.
- [ ] Add durable queue dispatch and job persistence.
- [ ] Implement active cancellation and worker recovery.

Verification: 94 unit tests pass locally, including eight queue tests.
No additional dependencies or services are required for this foundation.
The local queue is an intermediate development component; it does not replace
the planned Redis/Celery architecture. Pending CI verification remains open.

## Phase 1.5 — Browser Worker Connection (October 20, 2026)

- Execute one claimed local job and attach its result.
- Persist the job identifier with the JSON result.
- Skip cancelled pending jobs; block unsupported test identifiers.
- Convert unexpected executor/storage failures into explicit error outcomes.
- Run the queued path through the managed sample script and browser CI job.

Verification: 102 unit tests pass. The managed script executed a real queued
Chromium run successfully and saved its result and screenshot.
Durable dispatch, restart recovery, and active cancellation remain pending.
GitHub Actions verification of the updated worker path requires a push.

## Phase 1.5 — Durable Local Queue Adapter (October 20, 2026)

- Add SQLite persistence using Python's standard library; no dependency install.
- Preserve queued/cancelled/running/completed snapshots and test results on reopen.
- Claim jobs transactionally across competing database connections.
- Verify invalid transitions roll back without changing job state.
- Keep interrupted running jobs visible instead of automatically replaying them.

Verification: 109 unit tests pass, including seven SQLite adapter tests.
The browser CLI is still backed by the in-memory queue. SQLite integration and
restart commands are pending. Active cancellation, recovery, and production
broker integration remain incomplete; Phase 1.5 stays in progress.

Architecture note: SQLite is a local incremental adapter. Redis/Celery and
PostgreSQL remain the production direction described in the architecture plan.

## Phase 1.5 — Persistent CLI Integration (October 20, 2026)

- Use SQLite by default in the local worker CLI.
- Add submit, status, run-next, and pending cancel commands.
- Reopen the same queue across commands and persist completed result snapshots.
- Exercise submission and execution in separate processes in the managed CI script.
- Isolate automated checks with a temporary queue database.

Verification: 114 unit tests pass. The managed Chromium check passed with a
persistent queue shared between submission and execution processes.
No additional installation is required. Active cancellation, crash recovery,
and production queue dispatch remain pending; Phase 1.5 is not complete.
GitHub verification requires the next push.

## Phase 1.5 — Persisted Job Inspection (October 20, 2026)

- Add bounded job listing with status filters and offset pagination.
- Preserve submission order and avoid claiming jobs during inspection.
- Expose persisted running jobs after reopening the queue.
- Verify list validation and CLI filters across invocations.

Verification: 121 unit tests pass. No additional dependencies are required.
Running status alone is not evidence that a process is dead; automatic recovery
and active cancellation remain unimplemented. Phase 1.5 is still in progress.

## Phase 1.5 — Explicit Retry Attempts (October 20, 2026)

- Add explicit retry for completed failed/error results.
- Preserve original attempts and persist retry_of lineage for new queued jobs.
- Reject retries of active, cancelled, successful, skipped, or blocked jobs.
- Migrate older queue databases without deleting jobs.

Verification: 126 unit tests pass, including retry and old-schema migration checks.
The managed real Chromium run also passes after the schema change.
Retries are manual, do not execute immediately, and do not implement interrupted
worker recovery. Active cancellation and production dispatch remain pending.

## Phase 1.5 — Isolated Browser Deadline (October 20, 2026)

- Execute local browser jobs in a dedicated child process with a 30-second default limit.
- Terminate the process tree on timeout, then report an execution error.
- Validate child result transport and report abnormal exits or missing/invalid output.
- Keep per-operation Playwright timeouts and the managed script's outer deadline.

Verification: 132 unit tests pass. A real queued Chromium run passes through the
new subprocess boundary. A controlled Windows parent/descendant timeout check
confirmed both processes stopped. POSIX tree termination needs Linux verification.
User-requested active cancellation and interrupted-worker recovery remain pending.
Phase 1.5 is still in progress.
