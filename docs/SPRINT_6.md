# Sprint 6 — AI Integration

Started: 2026-10-21, explicitly authorized by the owner in this chat.
Status: In progress
Free local implementation and exact-commit CI review are complete. Waiting for
the owner's later live-model/spend decision; no additional paid work is authorized.
Issue: [#7](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/7)
Milestone: [#7](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/7)

## Delivery Phases

- [x] 6.1: Provider-independent bounded advisory and budget contracts.
- [x] 6.2: Reduce collected inputs, validate strict response schemas and reference membership.
- [ ] 6.3: Add an optional provider adapter with time/request/cost limits and safe fallback.
- [x] 6.4: Integrate feature, test-selection, and element suggestions without policy escalation.
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

## Responses API Contract Preparation

An offline request builder now prepares an explicitly configured model request
with `store=false`, streaming disabled, no tools, and a strict JSON schema under
`text.format`. Model selection has no default and API authentication accepts only
an environment secret reference. The builder never resolves credentials or opens
HTTP connections. Schema references are limited to collected IDs and host logical
names; incomplete coverage excludes absent-feature suggestions. Empty evidence
or candidate sets require empty corresponding suggestion arrays.

The bounded response-envelope extractor accepts one completed assistant text
message and rejects refusals, incomplete/error responses, tools, multiple outputs,
oversized bodies, and oversized text. Host advice validation still runs after
extraction. This conservative subset may reject legitimate model response shapes;
reasoning-message support must be reviewed before enabling such models.

Seven offline contract tests pass; all 368 local unit tests pass. These tests do
not establish live provider compatibility, pricing correctness, or model accuracy.
Remote transport, trusted charge bounds, explicit provider enablement, and live
evaluation remain pending. No paid call or credential access was performed.

Official contract references reviewed on 2026-10-21:

- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Responses migration and storage controls](https://developers.openai.com/api/docs/guides/migrate-to-responses)

## Fixed-Origin Transport Preparation

An internal HTTPS primitive targets only `api.openai.com:443/v1/responses`, uses
certificate verification, ignores environment proxy routing, and never follows
redirects or retries automatically. It resolves an environment key only after
explicit remote enablement and a positive claimed cost reservation within the
configured cap. Invalid/header-injected keys prevent connection. Response media,
encoding, body bytes, envelope and advice references are validated; errors omit
keys, headers, provider bodies, and OS details. Connections close on all outcomes.

This primitive is intentionally not registered with AiSession or any CLI. Its
reservation argument is a caller contract, not verified billing or a price quote.
DNS/slow-stream hard deadlines still require an isolated parent before live use.
The shared session currently admits only the guaranteed-free offline adapter.
Trusted model/pricing configuration, paid-usage authorization, isolated remote
runtime wiring, and live compatibility/evaluation remain unfinished. No production
spend-control claim is made for this unregistered primitive.

Eight mocked transport tests pass; all 376 local unit tests pass. Tests use fake
keys and mocked HTTPS only. No real environment credentials were read, no model
was contacted, and no paid request was made.

## Owner-Selected Offline Validation Scope

On 2026-10-21 the owner explicitly chose to finish free local validation first
and select a live model/spend limit later. Do not enable paid calls or claim live
model accuracy. The unfinished live portion of 6.3 and real-model evaluation in
6.5 remain pending that later decision; they do not block the offline controls.

## Phase 6.4 and Local Evaluation

The advisory plan overlay retains the exact original plan, authorization flag,
and decisions. Only already-selected cases whose structurally present features
also receive confident advice are prioritized. AI cannot unblock policy-denied
tests or replace unknown/absent prerequisites. Website kind is advisory only.

Element fallback runs only after a deterministic missing match, uses one collected
reference mapped to a host-owned locator, and rechecks current visibility and
uniqueness using the existing matcher. It never narrows ambiguous results,
overrides explicit project mappings, accepts model-generated locators, or performs
an action. Runtime policy and deadlines remain caller responsibilities.

Six integration unit tests and 18 real-child/browser controls verify these rules,
plain/commerce scripted fixtures, hidden/duplicate elements, outages, timeouts,
injected instructions, and rejected references/authorization fields. Reports state
`mode=offline_scripted`, `remote_calls=0`, `real_model_accuracy=null`. Scripted
fixture consistency is not evidence of model intelligence or accuracy.
All 388 local unit tests pass. CI repeats local AI acceptance and retains
metadata-only evidence. All seven jobs for implementation
`54ece45bee3a628d260e321f3ff7587d43691837` succeeded. Six downloaded artifact
digests/head SHAs, all 18 offline AI controls, scoring and existing regression
evidence were verified. See [local acceptance](SPRINT_6_LOCAL_ACCEPTANCE.md).

The offline evaluator records explicit denominators, website-kind confusion,
present-feature precision/recall, element correctness, abstentions, and
high-confidence errors. Undefined precision remains null when nothing positive
was predicted. An intentional incorrect commerce classification is retained as
an error in the four-item scoring self-check (3/4 correct); it does not make the
18 boundary controls fail or become a model-accuracy claim. Four scoring unit
tests cover false positives, abstentions, alignment, and duplicate label rejection.
The two added runtime contract tests also prevent malformed advice envelopes
and negative/boolean cost reservation. Oversized numeric model output is rejected
without conversion overflow. See [validation and enablement](AI_VALIDATION.md).
