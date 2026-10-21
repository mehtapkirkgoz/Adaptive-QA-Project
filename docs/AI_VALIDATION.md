# AI Validation and Enablement

## Current Mode

The owner chose free local validation first on 2026-10-21. AiSession accepts only
the offline scripted adapter. There is no default model, active remote provider,
paid request, model credential requirement, or measured real-model accuracy.
The unregistered OpenAI primitive is preparation, not an enabled model backend.

Local reports explicitly retain `mode=offline_scripted`, `remote_calls=0`, and
`real_model_accuracy=null`. Seventeen real-child/browser controls test the host
pipeline; replaying supplied answers is not a model evaluation. Existing unit
tests separately cover strict schema rejection and mocked provider boundaries.

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
