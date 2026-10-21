# Local Ollama Provider

The owner selected local Ollama on 2026-10-21. No API key or cloud inference
subscription is required. The registered starting model is `qwen3:4b` (about
2.5 GB download). Local compute still consumes RAM/VRAM, electricity, and time.
The observed development machine has approximately 16 GB RAM and an NVIDIA RTX
5050 Laptop GPU with 8151 MiB VRAM. Actual performance must be measured.

## Setup

Install Ollama from its official distribution. Bind it to `127.0.0.1:11434` and
disable cloud features with `OLLAMA_NO_CLOUD=1` or by preserving existing settings
and adding `disable_ollama_cloud: true` to `~/.ollama/server.json`.
Restart the service after changing settings. Pull the registered model:

```powershell
ollama pull qwen3:4b
```

Model installation is a separate, explicit host operation; test execution does
not download models automatically. Do not replace the registered local model
with a cloud alias. The loopback service and its installed model registry are
trusted host components, not a sandbox against malicious local administrators.

## Execution

`AiSession(AiBudget(timeout_seconds=60)).suggest(page, logical_names, OllamaProvider())`
uses the same reduced inputs, collected references, schema validation, confidence
thresholds, and policy-preserving host integration as scripted mode. A private
child sends one non-streamed request to the fixed numeric loopback address.
Redirects, unsupported media/encoding, incomplete/length-limited output, wrong
model names, tool calls, and nonempty thinking output are rejected. No custom
endpoint, cloud model, proxy environment routing, or API authorization header is
accepted. Thinking is disabled, generation is bounded, and keep_alive requests
model unload after its bounded idle period (30 seconds by default, configurable
from 0 to 120 seconds). Request payloads and raw model output are not
retained as reports.

The parent enforces its total session deadline and terminates the owned client
process on timeout. The shared Ollama service is not killed; server resource
cancellation after socket disconnection is a server responsibility. Avoid
parallel model jobs on a resource-limited host. Missing/stopped services and
invalid replies preserve deterministic fallback rather than passing a test.

## Validation

```powershell
python -m unittest discover -s tests -v
python scripts/check_ollama_model.py
```

The model evaluation uses independently labeled plain/login/commerce/incomplete
fixtures plus a separate five-fixture holdout set. It reports real local-model outcomes, abstentions, incorrect confident
decisions, latencies, and aggregate metrics. Local model evaluation is distinct
from the scripted controls in `check_ai_acceptance.py`. A successful HTTP/schema
response is not proof of correct classification; review all measured results.
Hosted CI tests mock the local service and do not download multi-GB models.

## Measured Integration Findings

Ollama 0.40.7 and the local Q4_K_M qwen3:4b model are installed. The first four-case
run had two 60-second timeouts and only 1/4 correct thresholded classifications.
After avoiding repeated immediate model unloads and clarifying general domain
classification instructions, all four development replies were accepted and
4/4 kinds were correct at the unchanged 0.85 confidence threshold. Warm replies
took approximately 2–3 seconds. GPU inspection confirmed 100% GPU execution with
about 3.8 GiB allocated; this is one-machine evidence, not a performance SLA.

The model still proposed an element for an uncertain incomplete form. This raw
high-confidence error remains in the report. Host fallback now rejects incomplete
coverage, unknown feature advice, or evidence belonging to a different form;
ambiguous deterministic matches were already protected. The held-out fixtures
were scored separately from these development examples.

The frozen [nine-case local evaluation](evidence/sprint6-ollama-evaluation.json)
records implementation `5e51be96a0c8e63ab30217ee7d4860372fd85f9e` and the installed
model digest. Eight replies were accepted; the duplicate-button reply was
rejected without being removed from metric denominators. Overall kind accuracy
was 8/9; the five-case holdout scored 4/5 kinds, 3/5 feature states, present-feature
precision 1.0 and recall 0.6, and 4/4 element decisions including abstention.
The four development cases retained one wrong confident element suggestion.
Actual browser checks produced no unsafe handle: incomplete evidence remained
missing and duplicate matches remained ambiguous. API cost and remote calls were
zero. This small fixture set is not an estimate of arbitrary-site accuracy.

## References

- [Ollama Windows setup](https://docs.ollama.com/windows)
- [Local authentication](https://docs.ollama.com/api/authentication)
- [Chat contract](https://docs.ollama.com/api/chat)
- [Cloud disablement](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features)
- [Registered model](https://ollama.com/library/qwen3:4b)
