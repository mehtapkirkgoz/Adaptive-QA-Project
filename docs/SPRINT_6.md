# Sprint 6 — AI Integration

Started: 2026-10-21, explicitly authorized by the owner in this chat.
Status: In progress
Issue: [#7](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/7)
Milestone: [#7](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/7)

## Delivery Phases

- [x] 6.1: Provider-independent bounded advisory and budget contracts.
- [x] 6.2: Reduce collected inputs, validate strict response schemas and reference membership.
- [ ] 6.3: Add an optional provider adapter with time/request/cost limits and safe fallback.
- [ ] 6.4: Integrate feature, test-selection, and element suggestions without policy escalation.
- [ ] 6.5: Evaluate controlled fixtures, ambiguity, prompt injection, outages, and privacy boundaries.
- [ ] 6.6: Verify exact-commit CI/evidence and report readiness for owner closure.

## Phase 6.1

Immutable advisory contracts cover website kind, known feature states, collected
evidence references, element candidate references, confidence, and bounded
request/time/input/output/cost budgets. The default cost allowance is zero.
Advice always has execution_authorized=False. No free-form SQL, arbitrary URL,
test success override, or executable locator is included in the advice contract.
The provider protocol returns untrusted JSON for later host validation. Runtime
budget enforcement and reference membership validation are not implemented yet.

No model API is called in this phase; no paid service is enabled. Existing
deterministic execution remains available. Provider configuration and live
acceptance must distinguish offline scripted evaluation from measured model
accuracy. Website content is untrusted data, never authorization.

Five new contract tests pass; the complete local suite has 345 passing tests.
Sprint 5 issue #6 was closed at the owner's explicit request. Its milestone
closure has not been re-confirmed; this does not block the authorized Sprint 6.

## Phase 6.2

Input reduction keeps bounded visible form/field/button structure and commerce
flags. It replaces page identifiers with local references and omits URLs, links,
raw names, and arbitrary text. Labels/actions are included only when they match
a small fixed vocabulary; other text becomes empty. This conservative policy
reduces semantics for novel button names. It is not a general secret detector:
host configuration and review remain necessary before enabling a remote provider.
Input text is explicitly marked as untrusted page data. Truncation makes coverage
incomplete, and oversized encoded input is rejected rather than silently shortened.

Strict JSON decoding rejects duplicate keys, non-finite values, malformed/deep
JSON, Markdown wrappers, extra root/nested properties, unknown features, duplicate
advice, and uncollected evidence/element references. Logical names must be supplied
by the host. Incomplete collection cannot support an absent-feature suggestion.
Accepted output remains advisory; confidence is not proof of correctness and
matching a reference does not establish visibility/uniqueness at execution time.

Eight new tests pass; all 353 local unit tests pass. No provider call, execution
integration, runtime budget enforcement, or measured model evaluation is claimed.

## Phase 6.3 Progress

An optional offline scripted adapter now exercises a real isolated child, shared
session request admission, total-time deadlines, byte limits, and safe fallback.
Concurrent calls share one thread-safe budget; failed/time-limited attempts are
not refunded. Cost admission reserves a trusted upper bound before execution;
the only registered adapter is guaranteed-free scripted transport. Model output
cannot report its own charge or increase a budget. No paid/remote provider is
registered and no real-model accuracy is implied by these tests.

Private scripted response fixtures are temporary inputs, excluded from repr and
reports. Child output is validated against collected references before advice
is accepted; disabled providers, failures, malformed/oversized responses, and
timeouts yield explicit fallback outcomes. Existing deterministic execution is
untouched. Eight new runtime tests pass, including actual child termination,
concurrent admission, failed-attempt accounting, and output rejection; the full
local suite passes 361 tests. Phase 6.3 remains open for the actual optional
model adapter, trusted pricing limits, and its provider-specific validation.
