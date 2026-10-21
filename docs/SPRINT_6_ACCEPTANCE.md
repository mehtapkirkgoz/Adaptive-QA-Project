# Sprint 6 Acceptance — Local Ollama

Status: Technical acceptance complete; awaiting owner closure.
Implementation: `5e51be96a0c8e63ab30217ee7d4860372fd85f9e`
[CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39645758286)

All seven jobs passed. Scaffold logs confirm 397 unit tests. Six downloaded
archive SHA-256 digests and recorded implementation SHAs matched. The retained
browser evidence confirms 18 scripted AI controls and scoring, 40 queued UI
cases, 96 shared variants, 40 reverse runs, 18 matching controls, both cross-layer
bridges, discovery fixture hashes/non-executing plans, and nine egress checks.
API evidence confirms 20 cases and 20 boundaries. Both OS database artifacts
confirm 15 cases, 19 boundaries, 15 reverse runs, and unchanged files. Both OS
lifecycle artifacts confirm three checks. All 178 referenced PNGs were checked;
a retained bridge screenshot was visually reviewed. Local actual-model report
identity, digest, denominators, mistakes and two safe browser outcomes were verified.

## Selected Scope

The owner selected local Ollama instead of a paid cloud API. Ollama 0.40.7 and
qwen3:4b Q4_K_M are installed; local inference uses no API key or API charge.
Cloud features are disabled in host configuration. Requests use a fixed numeric
loopback endpoint; arbitrary model names/cloud aliases are not registered.
The local model registry and service are trusted host components. Dormant OpenAI
preparation remains outside the selected execution path.

## Runtime and Host Controls

The shared session enforces concurrent request admission and a hard client
process deadline. Input reduction, strict JSON/schema/reference validation,
response byte limits, bounded generation and idle retention, and safe fallback
apply. The persistent shared Ollama server is not killed by client cancellation;
its cancellation/resource behavior remains a server responsibility. This is not
an OS/container memory quota or arbitrary-host execution sandbox.

AI retains advisory scope. Plan review preserves original decisions, assertions
and policy. Element fallback cannot override deterministic ambiguity/errors or
explicit project mappings; it requires complete reduced coverage, confident
present feature advice, evidence belonging to the candidate's form, one host-owned
mapping, and unique visible current DOM matching. No action is performed by the
advisory matcher and its output is not execution authorization.

## Measured Model Evidence

[Frozen nine-case report](evidence/sprint6-ollama-evaluation.json) identifies the
implementation and installed model digest
`359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
Four development fixtures were used before the separate five-case holdout.

- Eight validated replies out of nine; duplicate-button advice was rejected.
- Overall website-kind accuracy 8/9; development 4/4, holdout 4/5.
- Holdout feature-state correctness 3/5, present-feature precision 1.0 and recall 0.6.
- Holdout element decisions 4/4 including abstention; zero wrong confident holdout decisions.
- One wrong confident development element suggestion is retained in the report.
- Browser controls confirmed no unsafe handle: incomplete coverage remained
  missing and duplicate buttons remained ambiguous.
- Accepted replies took approximately 2–5 seconds; API charge/remote calls were zero.

The confidence threshold stayed at 0.85. Rejected/abstaining cases remain in all
relevant denominators. A negative control may reject advice only if the host
remains safe; positive fixtures must produce valid advice. Metrics describe these
small structural fixtures, not general website accuracy, calibrated confidence,
end-to-end customer execution, or a latency SLA. Initial cold/poor baseline is
documented in OLLAMA.md; error handling was not removed to increase acceptance.

Hosted CI does not download/run a real model. Local model evidence and hosted
regression evidence are separate and reference the same implementation SHA.
Issue #7 and milestone #7 remain open for owner closure; Sprint 7 requires an
explicit owner start.
