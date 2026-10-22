# Controlled API Catalog

The full catalog has 100 distinct definitions: 51 UI, 34 API and 15 database cases.
API definitions live in `api_catalog.py`; UI queue behavior remains independent.

| IDs | Behavior |
| --- | --- |
| API-001–004 | Readiness, typed item list, known item, unknown-item 404 |
| API-005–008 | Matching/unmatched search, missing query, excessive query length |
| API-009–011 | Anonymous 401, authenticated access, insufficient scope 403 |
| API-012–013 | Body-free HEAD and unsupported-method 405 |
| API-014–016 | Valid stateless echo, missing/oversized required payload field |
| API-017–019 | Quantity minimum, business total, quantity maximum |
| API-020 | Observe a 307 without following or forwarding authentication |
| API-021–022 | Requested pagination window/terminal cursor and invalid pagination rejection |
| API-023–025 | Numeric price order, stable taxonomy identifiers and category isolation |
| API-026–027 | Available stock quantity and zero-stock unavailability |
| API-028–030 | Empty-cart checkout restriction, quantity/price subtotal and discount arithmetic |
| API-031–032 | Region/currency delivery quote and unsupported-region rejection |
| API-033–034 | Field-specific validation errors and authenticated nullable/false-valued profile data |

POST cases declare data changes even though this fixture is stateless. The
integration harness explicitly enables those operations for the local fixture;
default project policy blocks them. Generated bearer values exist only in the
test environment. Reports contain result IDs/status/duration and generic reasons,
not requests, tokens, headers, response bodies, or assertion operands.

The fixture binds only `127.0.0.1:8000`. There is no customer endpoint inference,
real login service, database, or persistent customer mutation. API assertion
support is an explicit bounded subset, not a full OpenAPI/JSON Schema validator.

```powershell
python scripts/check_local_api.py
```

The script manages its own local server; port 8000 must be available. It saves
safe summaries and result records under `artifacts/api/`. The UI worker remains
a UI adapter; API execution uses its own configured adapter rather than silently
treating arbitrary queued IDs as network requests.

Catalog execution uses a private isolated API process with a hard total deadline
and cancellation cleanup. Run `python scripts/check_api_boundaries.py` for twenty
transport/policy/redaction boundary checks; these do not add catalog cases.
Private temporary configuration inputs are not report artifacts and are removed
after the run. Slow header/body streams are terminated by the parent deadline.

The fourteen Sprint 8 additions are distinct read-only contracts. They cover
generic listing APIs, account APIs and commerce calculations; they are not
fourteen cosmetic variants of one response. Concrete expected values belong to
the controlled fixture, not arbitrary customer business rules. Reuse requires
an explicitly supplied endpoint and expected contract. The API adapter never
guesses customer routes or runs these requests merely because a URL exists.
Without configuration the cases are blocked. UI discovery alone does not bind
API execution; all 34 API definitions remain blocked in that non-executing plan.
The dashboard still admits only explicitly selected read-only UI tests.

The extended fixture is stateless, without real orders, accounts or inventory
updates. All 34 isolated API cases passed against it. Additional unit checks
verify the fourteen additions reject an incorrect payload even when its HTTP
status matches, and never call transport without configuration. These checks
are not additional catalog cases.
