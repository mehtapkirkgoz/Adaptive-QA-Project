# Sprint 4 Acceptance Review

Review date: October 21, 2026 (Europe/Istanbul)
Status: Accepted. Final same-commit CI and downloaded artifact evidence verified.
Tracking: [issue #5](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/5).

## Acceptance Evidence

| Requirement | Evidence | Local result |
| --- | --- | --- |
| Positive/negative API cases execute | Twenty distinct API definitions against a stateless local HTTP fixture | Passed |
| Configuration failures are explicit | Missing configuration, environment secret, and wrong project checks | Blocked as expected |
| Secrets/payloads are not reported | Reflected bearer/body/header fixture plus outcome-only results | Passed |
| Target/mutation limits apply | Fixed-origin pinned transport, write denials, redirect canary | Passed; zero canary contacts |
| Hard total limits stop hostile streams | Isolated child, slow headers/body, idle timeout, cancellation | Passed |
| UI/API outcomes remain independent | Four binding checks with real UI/API and controlled failures | Passed |
| Catalog count is meaningful | Forty UI and twenty API definitions; variants/boundaries do not add cases | 60 total |

## Reproduce

With port 8000 available, run sequentially from the repository root:

```powershell
python -m unittest discover -s tests -v
python scripts/check_local_api.py
python scripts/check_api_boundaries.py
python scripts/check_ui_api_bridge.py
```

The existing browser, matching, discovery, UI isolation, queue, and OS lifecycle
checks also run in CI. There are 307 unit tests. API reports contain only safe
outcome metadata; private temporary configuration files must never be uploaded.

## Required Remote Gate

- Five jobs pass for the final implementation SHA: scaffold, API, browser, and
  lifecycle on Linux and Windows.
- Unit logs confirm 307 tests.
- Four downloaded artifacts match their SHA-256 digests and implementation SHA.
- API artifact: twenty passed cases, twenty safe result JSON records, twenty
  expected boundary outcomes, zero canary contacts, and no private inputs/payloads.
- Browser artifact: four UI/API binding outcomes preserve each layer's status,
  with a valid UI screenshot and the retained Sprint 3/regression evidence.
- Both OS lifecycle reports contain three successful checks.

## Verified Remote Evidence

Implementation: `5db716ced9576e878611e5579a3ebe0f64ddb873`.
[CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39559291036)
passed all five jobs. Unit logs confirm 307 tests. The API artifact has 20 passed
cases and 20 safe result JSON records, plus 20 expected boundary outcomes and
zero canary contacts. No authorization/header/body/private-input fields were
published. The browser artifact preserves four bridge outcomes, 40 queued UI
results, 18 matching checks, 96 variants, 40 reversed runs, and 177 valid PNG
references. Fixture hashes/matrices, five discovery-budget scenarios, nine egress
checks, and both three-check OS lifecycle reports also passed.

All four archive SHA-256 digests matched GitHub metadata and the implementation
SHA. A bridge screenshot was visually inspected: the sample book input and
literal no-results status match the fixed UI assertion. Downloads, metadata,
and inspection tooling are retained under ignored `artifacts/acceptance/`.
GitHub artifacts have seven-day retention; committed scripts/fixtures reproduce
these checks. Issue #5 is closed. The tool exposes no milestone write operations,
so Sprint 4 milestone creation/association/closure remains an owner action.

## Explicit Scope

Customer/public API execution remains disabled. API inputs are explicit and are
never inferred from the supplied website URL. The initial assertion subset is not
full JSON Schema/OpenAPI support. API execution has its own adapter; arbitrary
queued UI IDs do not become network requests. UI planning remains non-executing.
POST sample operations require explicit data-change policy even though echo and
quantity fixtures are stateless. No customer mutation or backend cleanup occurs.
Private temporary inputs may contain configured test data; authentication uses
environment references and values are resolved only during execution.

## Closure

- [x] Verify local API, safety, bridge, and unit checks.
- [x] Record scope and reproduction commands.
- [x] Verify final CI jobs and downloaded artifacts.
- [x] Update sprint completion documents and close issue #5 after acceptance.
- [ ] Create/associate/close the Sprint 4 milestone through the repository owner.
