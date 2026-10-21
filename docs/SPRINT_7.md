# Sprint 7 — Web Dashboard and Project Management

Started: 2026-10-21, explicitly authorized by the owner after closing Sprint 6 issue #7.
Status: In progress
Issue: [#8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/8)
Milestone: [#8](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/8)

## Delivery Phases

- [x] 7.1: Persist owner-scoped projects and verify cross-owner access boundaries.
- [ ] 7.2: Add credential/session authentication and local web security controls.
- [ ] 7.3: Expose authenticated project/configuration APIs with secret references.
- [ ] 7.4: Build the React/TypeScript dashboard for project and plan review.
- [ ] 7.5: Bridge authorized run start/cancel/progress to separate worker execution.
- [ ] 7.6: Display owner-scoped history/results/evidence and test cross-owner denial.
- [ ] 7.7: Demonstrate the integrated local MVP and review exact-commit CI/evidence.

## Phase 7.1 Delivered

A separate SQLite dashboard project store persists random project IDs, owner
IDs, and bounded display names. Read/list/update queries constrain ownership
inside SQL. Missing and other-owner records produce the same outcome. Stable,
bounded pagination and parameter binding are implemented. No target execution,
queue mutation, credentials, raw secrets or evidence paths are stored here.

The typed actor is a trusted internal identity, not authentication. Future HTTP
handlers must derive it from validated server sessions, never request bodies or
owner headers. There are no public dashboard endpoints in this phase. Existing
queue storage remains separate until run ownership is explicitly integrated.

Eight real-database tests verify persistence, owner isolation, denied updates,
non-enumerating errors, pagination, identity preservation, bound SQL-looking names,
and invalid inputs. All 405 local unit tests pass. HTTP authentication, the web
panel and integrated run flow remain unfinished. No domain/deployment or customer
site execution is authorized by this sprint start.
