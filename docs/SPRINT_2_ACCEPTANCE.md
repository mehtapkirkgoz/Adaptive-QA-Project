# Sprint 2 Acceptance Review

Review date: October 20, 2026
Status: Local checks passed; implementation CI and artifact verification pending.

Tracking: [issue #3](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/3)
and [milestone #3](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/3).

## Acceptance Evidence

| Requirement | Evidence | Local result |
| --- | --- | --- |
| Contrasting sites produce appropriate plans | Four static fixture sites, five feature states and five prerequisite definitions per site | Passed |
| Separate absence and uncertainty | Complete information pages vs unresolved hints, incomplete collection, traversal failures | Passed |
| Explain skipped/blocked cases | Every plan entry has a reason; selected entries include a page and evidence | Passed |
| Honor discovery budgets | Five real guarded discovery scenarios for traversal, page/depth/request limits, and hard deadline | Passed |
| Preserve destination controls | Existing proxy/browser canary checks, repeated runtime authorization | Passed in prior regression; required again in CI |
| Preserve existing execution | Existing ten queued smoke cases, result JSON and PNG evidence | Passed in prior regression; required again in CI |

## Reproducible Checks

Run sequentially from the repository root with port 8000 available:

```powershell
python -m unittest discover -s tests -v
python scripts/check_page_collector.py
python scripts/check_local_discovery.py
python scripts/check_discovery_acceptance.py
python scripts/check_network_security.py
python scripts/check_local_browser.py
python scripts/check_process_lifecycle.py
```

There are 243 unit tests. Browser checks verify real collection, five bounded
discovery scenarios, four contrasting sites, nine egress scenarios, and ten
queued smoke cases. Process lifecycle checks cover three OS-level scenarios
on both Linux and Windows in CI.

## Required Remote Evidence

- All four CI jobs succeed for the implementation commit.
- `local-browser-evidence` includes `discovery/acceptance.json`,
  `discovery/report.json`, security/smoke reports, and ten JSON/PNG result pairs.
- The four fixture reports match the committed HTML SHA-256 values and expected
  feature/decision matrix, with no execution authorization or origin writes.
- Both OS lifecycle reports contain three successful checks.
- Downloaded archive SHA-256 digests match GitHub artifact metadata.

## Scope and Next Work

This sprint delivers discovery and non-executing plans for controlled local sites.
General customer URLs, universal commerce support, AI classification, API/SQL
execution, and the dashboard remain future work. Selected definitions still need
compatible executors and runtime checks. Multi-page workflows require explicit
bindings; the existing sample executor continues to target its fixed root page.
Page content and URL paths remain untrusted, potentially sensitive data.

## Closure Checklist

- [x] Four contrasting sites pass real guarded discovery and planning checks locally.
- [x] All 243 unit tests pass locally.
- [ ] Verify all implementation CI jobs and download artifacts.
- [ ] Check fixture hashes, matrices, reasons, page evidence, and regression reports.
- [ ] Record verified evidence and update sprint completion documents.
- [ ] Close issue #3 as completed after acceptance.
- [ ] Repository owner closes milestone #3.
