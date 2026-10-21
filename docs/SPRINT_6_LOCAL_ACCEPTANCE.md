# Sprint 6 — Free Local Validation

Status: Free local scope verified; live model decision deferred by the owner.
Scope decision: The owner chose free local validation first on 2026-10-21;
live model selection and spend authorization are deferred.

Implementation: `54ece45bee3a628d260e321f3ff7587d43691837`
[CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39599629270)

## Exact-Commit CI Review

All seven jobs succeeded for the implementation above: scaffold, API, browser,
database on Ubuntu/Windows, and process lifecycle on Ubuntu/Windows. Scaffold
logs confirm 388 unit tests. All six downloaded archive SHA-256 digests and
recorded head SHAs matched the implementation.

The browser artifact confirms all 18 offline AI controls, explicit no-live-call
and no-real-model-accuracy fields, four scoring labels with the intentional error,
and safe control result fields. Existing evidence was also rechecked: 40 queued
UI cases, 96 shared variants, 40 reverse UI runs, 18 matching controls, 20 API cases
and 20 API boundaries, 15 database cases plus 19 boundaries and 15 reverse runs
on both OSes, both cross-layer bridges, discovery fixture hashes/plans, nine egress
checks, and three lifecycle checks on each OS. All 178 referenced PNG headers
and dimensions are valid; the retained bridge UI screenshot was visually reviewed.
Metadata and archives are retained only under the ignored acceptance directory.

## Verified Locally

All 388 unit tests pass. Eighteen free real-child/browser integration controls
pass. They cover accepted scripted advice, unsupported references and SQL,
authorization injection, nonfinite confidence, provider outage/disablement,
stalled-child termination, private/injected-text reduction, plain/commerce
fixtures, policy-preserving plan priority, single/duplicate/hidden candidates,
explicit project override, preserved deterministic ambiguity, and honest scoring.

The four-item scoring self-check intentionally includes one wrong confident
classification. It reports 3/4 correct website-kind predictions and one
high-confidence error. Feature and element checks have explicit denominators;
undefined precision remains null. These are scorer tests using supplied answers,
not evidence of real-model classification or element-identification accuracy.
Reports preserve `mode=offline_scripted`, `remote_calls=0`, and
`real_model_accuracy=null`.

AI review retains the exact original plan and cannot grant execution, unblock
policy-denied tests, or change success assertions. Element fallback is allowed
only after a missing deterministic result, through one host-owned collected
mapping that must match a unique visible current element. Existing ambiguity,
errors, and explicit project mappings remain authoritative.

## Deferred Live Work

No paid provider was enabled, real key read, or model inference requested.
The optional OpenAI request/response and HTTP primitives are preparation only;
normal AiSession execution remains scripted and free. Trusted dated pricing,
worst-case charge accounting, isolated remote runtime wiring, owner-authorized
model/spend selection, and independently labeled live evaluation remain pending.
See [enablement requirements](AI_VALIDATION.md).

Sprint 6 is not fully accepted or closed by this local validation. Issue #7 and
milestone #7 stay open; Sprint 7 is not started. After local evidence review,
scheduled continuation waits quietly for the owner's live-model decision instead
of enabling remote calls or repeating unchanged tests.
