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

- Network execution remains disabled until destination controls are verified.
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

- Define an explicit policy for the local sample application.
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