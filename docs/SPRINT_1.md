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