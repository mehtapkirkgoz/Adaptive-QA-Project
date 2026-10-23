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
- [ ] Verify same-commit CI for this follow-up.
- [ ] Make saved target execution eligibility explicit before queue submission.
- [ ] Extend reusable execution beyond fixed sample bindings using contrasting
  controlled fixtures before enabling any owner-authorized external targets.
- [ ] Address operator enrollment/agent startup and bounded unattended maintenance
  from PILOT_FINDINGS.md with separately verified increments.

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
