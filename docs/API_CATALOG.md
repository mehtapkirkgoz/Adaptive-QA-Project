# Controlled API Catalog

The combined catalog has 60 distinct definitions: 40 UI cases and 20 API cases.
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
