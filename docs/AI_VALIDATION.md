# AI Validation and Enablement

## Current Mode

Update: the owner subsequently selected local Ollama. AiSession now also accepts
the registered local qwen3:4b adapter. It uses no key and no paid cloud model.
Real model evaluation is separate from the previously accepted scripted evidence;
see [Ollama setup](OLLAMA.md) and docs/SPRINT_6.md for measured status.

The owner chose free scripted validation first on 2026-10-21. That accepted stage
used only the offline scripted adapter. There was no default model, active remote provider,
paid request, model credential requirement, or measured real-model accuracy.
The unregistered OpenAI primitive is preparation, not an enabled model backend.

Local reports explicitly retain `mode=offline_scripted`, `remote_calls=0`, and
`real_model_accuracy=null`. Eighteen real-child/browser controls test the host
pipeline; replaying supplied answers is not a model evaluation. Existing unit
tests separately cover strict schema rejection and mocked provider boundaries.
Aggregate scoring has explicit denominators, classification confusion, feature
precision/recall, element correctness, abstentions, and high-confidence mistakes.
The offline scoring self-check includes a deliberate wrong high-confidence
answer and reports 3/4 kind predictions correct and one error. This verifies
the scorer, not the quality of any real model.

## Enforced Local Rules

- AI advice never authorizes a test or changes a success assertion.
- Original test-plan decisions and project policy remain authoritative.
- Confidence below the configured threshold cannot prioritize a case or supply
  an element fallback. Confidence is not a calibrated probability of correctness.
- Feature priority requires independently present structural evidence.
- A missing deterministic element may use a collected reference tied to one
  host-owned mapping. Live matching rechecks visibility and uniqueness.
- Existing ambiguity, errors, and explicit project mappings cannot be overridden.
- Input reduction drops arbitrary page text, URLs, IDs, links, and field values.
  Fixed-vocabulary labels are allowed; novel labels lose semantic detail. This
  is not a universal secret detector or arbitrary-site AI element recognition.
- Private transport fixtures are temporary; reports contain control outcomes.
- Failed attempts consume request slots. Shared session time and request limits
  apply to concurrent calls. Scripted transport is free; monetary admission tests
  do not certify production billing caps for a remote model.

## Remaining Live Acceptance

Before enabling a model, explicitly select an available model and verify its
structured-output compatibility, request envelope, tokenizer/usage accounting,
and dated input/output pricing. Define an owner-approved run spend limit and
worst-case charge admission. Do not trust a charge declared by a model reply.
Wire remote execution into an isolated process with total deadline/cancellation,
shared cost/request reservation, output limits, and safe provider fallback.

Use an environment secret reference for the API key; never paste or commit the
key, persist request bodies, or print provider responses. Do not send customer
data for validation. Run controlled labeled fixtures with independent ground
truth, including withheld/contrasting cases and injection/ambiguity negatives.
Record feature precision/recall, classification confusion, element accuracy,
abstention and incorrect high-confidence decisions, latency and actual cost.
Keep thresholds and evaluation denominators explicit and report failures.

Remote validation remains deferred by the owner's choice. Sprint 6 remains open
until the owner makes that decision and the remaining acceptance is verified,
or explicitly accepts a reduced offline scope. Do not start Sprint 7 automatically.
