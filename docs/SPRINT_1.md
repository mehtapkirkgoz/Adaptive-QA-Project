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
- [ ] Connect the sample application to browser execution.


## Phase 1.3 Progress

- [x] Open the controlled sample application with Playwright.
- [x] Verify the sample page and login form.
- [x] Close browser resources through finally blocks.
- [x] Return a structured result with elapsed duration.
- [x] Distinguish assertion failures from execution errors.
- [x] Verify result classification with five isolated unit tests.
- [ ] Verify browser cleanup and timeout behavior automatically.
- [ ] Add automated browser execution to CI.

Local verification: 71 unit tests pass.
The local browser check has also been verified manually.
## Current Checkpoint — Phase 1.4 (October 20, 2026)

- [x] Persist structured test results as JSON.
- [x] Capture screenshots after successful local checks.
- [x] Link existing screenshots through the optional evidence_paths result field.
- [x] Verify evidence serialization and omit missing screenshot references.
- [x] Execute the real local browser scenario and verify its JSON references a PNG.
- [ ] Capture failure evidence without replacing the original test outcome.
- [ ] Add automated browser execution to CI.

Current local verification: 78 unit tests pass; one local browser scenario passes.
Phases 1.1 and 1.3 still have pending controls and automated lifecycle checks.
Phase 1.4 remains in progress. Queueing, cancellation, and the 10-case catalog
have not been implemented. Current changes await GitHub CI verification after push.
