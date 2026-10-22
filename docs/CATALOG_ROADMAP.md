# Catalog Expansion After the First 100 Scenarios

Status: Planning only. These ideas are not registered executors, accepted cases
or authorization to start another sprint, contact customer systems or mutate data.

The current 100 definitions are 51 UI, 34 API and 15 database cases. The number
of applicable cases depends on inspected features, explicit adapter bindings,
configured contracts and project policy. Translations and locator alternatives
exercise existing IDs and must never increase the count.

## Candidate Coverage Toward 200

| Area | Provisional additional capacity | Behaviors to validate with pilot findings |
|---|---:|---|
| Accounts and registration | 20 | Registration validation, confirmation/reset lifecycle, session expiry, role-specific access and recovery |
| Commerce workflows | 20 | Variant/stock constraints, cart updates, coupon eligibility, totals, delivery choices and order confirmation |
| Search and navigation | 15 | Pagination, multi-filter interaction, sort stability, deep-link state and empty/error states |
| Forms and accessibility | 15 | Multi-step forms, uploads with explicit limits, focus/error association and dynamic controls |
| API contracts | 15 | Versioned schemas, concurrency/idempotency, pagination consistency and authorization boundaries |
| Database verification | 15 | Transaction consistency, relationship integrity, lifecycle changes and read-only reconciliation |

These are provisional capacity ranges expressed as planning targets, not promises
to add precisely 100 cases or cosmetic variations. Pilot evidence can replace,
combine or remove an area. Full load/security scanning and billing remain separate
product decisions under SPRINT_PLAN.md.

## Evidence Required Before Adding a Case

1. Record the concrete user behavior, required features, risk and expected result.
2. Confirm it is not covered by an existing ID or a parameter/locator variant.
3. Supply explicit site bindings and expected API/query contracts where required.
4. Provide independent positive and meaningful negative controlled fixtures.
5. Enforce target, timeout, mutation and secret-reference policies.
6. Prepare and clean isolated test data; never depend on execution order.
7. Register an executor only when it exists and is verified. Unsupported or
   ambiguous binding remains blocked, with a reason.
8. Add same-commit CI evidence and update catalog/applicable counts separately.

Account creation, cart updates, uploads and orders require explicit mutation
policy and disposable test accounts/data. Real payment execution, customer-site
access, service purchases and deployment require owner authorization. AI may
assist matching/classification but cannot invent contracts or success criteria.

## Pilot Prioritization Record

For each pilot finding record its site type, feature evidence, business impact,
frequency, proposed existing/new case ID, required bindings, reproducible fixture,
data cleanup and owner acceptance. Prioritize repeated high-impact gaps first.
No customer pilot has been run or is authorized by this planning document.
