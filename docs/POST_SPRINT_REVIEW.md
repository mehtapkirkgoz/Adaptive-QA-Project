# Post-Sprint Local Product Review

Started: 2026-10-23, explicitly authorized by the owner after closing milestone 11.
Sprint 10 issue/milestone are closed. Its frozen acceptance remains historical.
This follow-up does not enable purchases, public backend hosting or customer tests.

## Current Work

- [x] Verify Sprint 10 milestone closure and preserve the existing local session.
- [x] Review personal/shared project selection through real local Chromium flows.
- [x] Show discovered case names, searchable identifiers/names, visible/selected
  counters and a bounded list in both execution panels.
- [x] Preserve hidden selections when filtering, enforce the ten-case limit and
  clear selections explicitly. Reset stale shared selections when candidates change.
- [x] Verify actual discovery, two-case execution, report/evidence, roles and
  revocation after the UI changes; zero external requests/page errors.
- [x] Verify same-commit CI for the selection/target/document increments through
  2e2b8bd: all twelve jobs passed; four downloaded artifact digests and reports verified.
- [x] Make saved target execution eligibility explicit before queue submission;
  verify unsupported saved targets never dispatch in personal/shared browser flows.
- [ ] Extend reusable execution beyond fixed sample bindings using contrasting
  controlled fixtures before enabling any owner-authorized external targets.
  - [x] Add an explicit canonical document-path binding for the existing five
    independent document cases; remove sample title/heading assumptions only
    for those bound cases, retaining pinned egress and process deadlines.
  - [x] Verify three contrasting HTTP documents and five real negative defects
    through separate child processes, including denied write/canary requests.
  - [ ] Integrate reviewed discovered document bindings into admission/planning
    before widening dashboard execution scope.
    - [x] Route already-admitted root document cases through the independent
      executor in the common personal/shared worker; retain current admission.
    - [ ] Review non-root discovered paths and target-specific context binding
      before exposing additional target scopes through the dashboard.
- [ ] Address operator enrollment/agent startup and bounded unattended maintenance
  from PILOT_FINDINGS.md with separately verified increments.
  - [x] Add an explicit bounded maintenance-once operator command for expired
    agent leases and personal/shared evidence pruning; automatic supervision is pending.

The last three items are future engineering work, not accepted capabilities.
Do not remove destination guards, infer ownership from a public URL or count
fixture variations as additional catalog cases. API/database business assertions
still need explicit contracts and secret references. Public Pages remains unchanged.

## Selection Verification

The personal and organization browser drills now check ID/name search, empty
search results, preservation of checked hidden tests, clearing and the ten-case
limit before running the existing real end-to-end scenarios. The shared list no
longer stretches the page with dozens of unlabelled identifiers. Normal app
build passed; personal/shared browser checks passed locally.

check_dashboard_ui.py accepts an optional --port for isolated verification when
the owner's normal server is already listening on 8765. It uses disposable
accounts/storage and never stops the owner's server.

## Saved Target Support

The local app now explains whether the saved URL/host settings match the current
controlled root worker. Unsupported targets remain configurable and reviewable;
their discovery action is disabled with a concrete explanation. This UI mirrors
the current restriction but grants no authorization: server/worker checks remain
authoritative. API/database bindings are not inferred from a URL. The message
uses saved settings so unsaved edits cannot imply an executable configuration.

Both browser flows saved https://example.test/ without visiting it, verified the
unavailable explanation and disabled dispatch, then restored the controlled
fixture and completed actual discovery/UI tests. The shared host textarea has
an explicit accessible name so repeated saved-setting edits remain addressable.
The demo regression passed at 390/768/1440 pixels with zero API/external requests
and no enabled execution. No public demo behavior was changed.

## Independent Document Worker Foundation

run_isolated_sample_test now accepts an explicit document_path for DOC-001 through
DOC-005 only. This binding visits a canonical path on the existing controlled
127.0.0.1:8000 fixture origin and evaluates the registered rule without requiring
the Adaptive QA Sample title or heading. It cannot redirect another case into an
arbitrary executor, add hosts, change methods or enable customer execution.
Paths with authority/scheme escapes, query/fragment, percent encoding, traversal,
controls or non-ASCII text are rejected before process creation. The existing
proxy/route guards, fresh context, bounded process tree, cancellation and evidence
validation remain in force. No dashboard target restriction was widened.

check_document_execution.py executes five existing cases on information, commerce
and account documents with unrelated titles (15 passed executions), then verifies
five specific broken documents produce failed assertions rather than success or
generic loading errors. Twenty PNGs are validated; a forbidden destination canary
and POST receiver remain untouched. These fixture variations do not increase the
100-case catalog. CI repeats the drill in the UI catalog job. Discovery-backed
general document admission/UI integration remains the next unfinished step.

Foundation local regression completed 659 tests: 658 passed and one Windows
symlink-permission skip. The earlier selection increment 9588cce passed Core
checks run 39914643399; saved-target increment 42db9b4 CI remains in progress.
The document foundation requires its own same-commit CI after push.

## Discovery-Backed Root Document Runs

The normal personal/shared worker now routes the five already-eligible root
document cases through the independent binding. Existing membership, discovery,
configuration, quota, result/evidence and cancellation checks remain authoritative.
The HTTP drill discovers an information page with an unrelated title, explicitly
admits five cases through each queue and verifies ten passed persisted outcomes,
ten scoped PNGs and released shared active capacity. Admission alone remains
non-executing. No root-path or external-target restriction is widened.

Document runs deliberately omit a comparable execution context until actual page
content can be bound to it; differing documents must not be pooled into flaky
signals based only on a sample source fingerprint. Worker/consistency regressions
cover this conservative behavior. The context source inventory also includes the
new document-path validator. Non-root admission/UI support remains unfinished.

## Verified Follow-Up Evidence

Implementation 2e2b8bd9cae181c9fc9436972d74d2f0d5bce244 passed all twelve
jobs in run 39915903166 and 660 Linux unit tests. Earlier 9588cce, 42db9b4 and
892c190 Core checks also succeeded. Four downloaded archives (UI catalog,
organization/browser and both packaged runtimes) passed SHA-256/head verification.
Their actual reports confirm document execution, named/filtered selection,
unsupported-target non-dispatch and both-platform runtime/rollback. See
evidence/post-review-2e2b8bd.json. This supersedes the historical pending CI notes.

The maintenance increment has its own tests/CI requirement and does not inherit
acceptance from that earlier commit. No unattended service has been installed.
Its local full regression completed 666 tests: 665 passed and one Windows
symlink-permission skip. Six maintenance tests include an actual CLI subprocess,
live/expired lease handling, partial-outcome preservation, bounded evidence
cleanup and worker-lock refusal. Both-platform CI repeats these checks.
