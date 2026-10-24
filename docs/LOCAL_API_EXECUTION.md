# Explicit Local API Review

The existing API catalog contains controlled example contracts. Website discovery
does not establish API endpoints or make those contracts applicable to another API.
The catalog remains 34 API definitions, within the unchanged 100-case total.

`local_api_review.py` adds an internal reusable read-only contract path. An operator
supplies a typed ApiCase with an explicit request path, HTTP status and bounded JSON
assertions. No endpoint or expected response is inferred from the website URL.
Only the owned `http://127.0.0.1:8000` origin and its exact hostname allowlist are
supported. GET/HEAD requests have no body, query, authentication or data-change
authority. This does not enable public/customer API execution.

Reviewing is offline and does not resolve environment references. Its fingerprint
binds all project fields and the complete case contract. The internal execution
entry point requires the exact confirmed fingerprint and current typed project;
changed settings/assertions invalidate the review before dispatch. Execution uses
the existing isolated API child, numeric destination guards, 15-second total
deadline and cancellation callback. Raw response bodies are not persisted.

The entry point is not a dashboard route or customer worker. Before exposing it to
customers, add owner-scoped saved API settings/review, current license/capacity
admission, queue leases/cancellation, explicit UI confirmation and corresponding
end-to-end evidence. A direct internal function does not supply those permissions.
Existing saved plans remain non-executing and API-token references alone do not
establish an executable binding.

Three unit checks cover offline review, confirmation/configuration drift, restricted
origins and request authority, and bounded child dispatch. The owned HTTP proof uses
two contrasting endpoints and configurable boolean assertions: two expected passes
and one expected failure, exactly three GET requests. Review, stale configuration
and pre-dispatch cancellation produce no requests. CI repeats the proof and uploads
its value-free report with the API evidence.

## Saved Settings and Scoped Review

Project configuration now accepts optional `local_api_binding` metadata with four
exact fields: `path`, `expected_status`, `json_field`, `expected_boolean`. The first
saved profile is an unauthenticated GET with one explicit top-level boolean
assertion, a 2xx/4xx status and a bounded normalized path. It requires the exact
owned API origin above. Unknown fields, values masquerading as booleans/statuses,
query strings and authority/path escapes are rejected. Null removes the binding;
invalid replacements preserve the prior saved configuration.

Local free/licensed apps expose POST
`/api/projects/{project_id}/local-api/review` with an empty JSON object. It requires
the existing local session, Origin and CSRF checks and reads one owner-scoped saved
snapshot. The review fingerprint includes the complete saved settings plus the
typed API contract, so changing policy, references or assertions changes it.
The response explicitly says `execution_authorized: false`. It does not resolve
references, contact the endpoint, create a run or reserve licensed capacity.

The current dashboard preserves this metadata on unrelated saves; an API editor
and queue admission are not implemented yet. This endpoint therefore provides
review only. Three persistence/HTTP checks verify restart, foreign ownership,
configuration drift, invalid replacement/removal and session/Origin/CSRF guards.

The HTTP configuration endpoint explicitly accepts the optional binding as well
as the persistence layer. A browser regression caught a missing field in that HTTP
allowlist; it was corrected and the HTTP tests now save valid/invalid replacements
through the real PUT endpoint. The free browser drill also verifies that reloading
and saving unrelated dashboard settings preserves a previously saved API binding,
alongside real discovery/LOGIN-001 execution and zero external browser requests.
The shared-settings regression completed 805 tests (804 passed, one Windows
permission skip); focused HTTP and browser checks passed after the allowlist fix.

## Internal Confirmed Queue and Worker

`LocalApiQueue` now admits a confirmed current saved-review fingerprint in a
SQLite write transaction. It rechecks ownership/settings and current licensed
admission, shares pending capacity with UI/form runs and reserves running capacity
through the existing licensed store. Claim-time drift blocks dispatch; active
settings/license changes request cancellation. Random claim tokens prevent stale
finalization, outcomes contain status only, and failures are never retried.
Explicit interrupted-work recovery marks claims terminal. Offline workspace
recovery cancels API work and clears claims alongside the other queues.

The internal worker uses the existing isolated API process and cancellation checks.
Six real SQLite checks cover confirmation, scope, concurrent admission/claims,
settings drift, cancellation, no retry, sanitized failures, signed-license capacity/
expiry and offline restoration. The HTTP proof now additionally saves, confirms,
queues and executes both contrasting endpoint contracts: five GETs total including
the earlier direct contracts, two saved jobs passed, no requests at review/admission.
The 100-case catalog is unchanged. HTTP job admission, customer CLI commands and
operator UI confirmation remain the next integration step; this internal increment
does not expose an execution route or start a worker in the owner's session.

## Local HTTP Admission and One-Shot Commands

Free/licensed local apps now expose `/local-api/jobs` under each owned project:
POST requires exactly `confirmed_contract_fingerprint` from the current saved
review; GET returns the latest twenty jobs. GET `/{job_id}` reads one owned job;
POST `/{job_id}/cancel` takes an empty object. Mutations retain session/Origin/CSRF
guards. Extra path/credential/authority overrides are rejected. Admission rechecks
the digest transactionally and does not execute the job in the HTTP handler.

Start at most one queued API job in another terminal, using the dashboard's actual
workspace path (example paths below must be replaced):

```powershell
python -m adaptive_qa dashboard free-api-once --database C:/QA/workspace/projects.sqlite
python -m adaptive_qa local api-once --workspace C:/QA/workspace --trusted-keys C:/QA/publisher-public-keys.json
```

Free commands refuse licensing state. Paid commands always use the licensed store.
Explicit `free-recover-api` / `local recover-api` commands mark interrupted API
claims terminal under the worker lock; they never retry them. Do not run recovery
alongside an active worker. The existing three-queue worker-cycle command is
unchanged; API processing is a separate explicit one-shot command.

Sixteen focused HTTP/CLI checks passed. The controlled HTTP proof now saves and
reviews through the real configuration API, explicitly confirms job admission,
executes both jobs using a separate free-api-once process and reads the persisted
results through scoped HTTP. Five total GET requests were observed; review and
admission contacted no target. Customer-facing editor/confirmation UI remains next.

## Local API Editor

The free/licensed configuration form now includes an optional explicit API editor
for the exact supported loopback origin. Operators select the GET path, expected
HTTP status, top-level JSON field and expected boolean; values/credentials are not
accepted. Saving uses the existing configuration endpoint and never reviews,
enqueues or executes a job. Switching projects reloads saved metadata; disabling
the editor removes the binding. API draft changes participate in unsaved-change
tracking so existing interactive confirmations cannot ignore them.

The real free browser drill configured/saved through the editor, reloaded the
binding, preserved it on a subsequent save, then removed it. No API job was created,
no central browser request or page error occurred, and the existing discovery/UI
execution checks still passed. Production/demo builds passed. The public demo
does not render this editor. The dedicated API review/confirmation/history panel
remains the next increment. Core CI for f2ac02f passed; this editor's exact-commit
CI and later artifact inspection remain pending.

## Explicit Operator Confirmation and Results

The real free/licensed dashboard now shows a saved API execution panel with the
GET path, expected status and boolean assertion. Review remains a separate action
with no target contact; a fresh review plus explicit checkbox is required to queue
one request. Unsaved configuration edits disable review and discard confirmation.
Admission consumes the confirmation, never automatically retries an uncertain
response, and refreshes scoped history after uncertainty. History polls while jobs
are active and offers cancellation. One-shot free/paid worker guidance is shown
separately; it does not start a process from the browser.

The free browser proof configured/saved the binding, reviewed it, demonstrated
confirmation invalidation on edit, explicitly queued a job, invoked the actual
free-api-once CLI and observed the persisted passing result in the UI. A second
explicitly queued job was cancelled before execution. Exactly one API GET reached
the owned fixture. Save/reload/remove, one-project limits, real discovery/UI runs,
zero external browser requests and no page errors still passed. Mobile layout had
no horizontal overflow and its screenshot was visually inspected. Production/demo
builds passed; the demo does not expose these controls. CI uploads the mobile
evidence, but exact-commit remote acceptance remains pending.

The licensed browser drill now covers the same editor/review/confirmation flow
with a contrasting expected-false response and the actual `local api-once` command.
Exactly one owned GET is sent. After offline snapshot/recovery and fresh password
login, both the saved API binding and passing result remain available. The source
drill passed with zero external requests/page errors. Installed-release validation
now requires this API evidence as well as the existing licensed recovery checks;
its result and remote CI will be recorded separately.

## Installed Operator Checkpoint

Committed release 3091a81 was built and installed outside the checkout. Its four
bundle file sizes/digests and unchanged 51 UI + 34 API + 15 database catalog were
verified. The installed licensed UI -> confirmed HTTP job -> separate installed
CLI -> supervised API child -> visible result flow passed. One expected-false
endpoint GET occurred; no external browser request or page error occurred. Offline
recovery invalidated the old session, required fresh password login and preserved
the saved binding, signed license and passing API result. The release stayed
inactive and the owner's live server was not restarted.

Full local regression completed 814 tests (813 passed, one Windows permission
skip). Evidence is in evidence/installed-api-3091a81.json. An initial local Windows
rename error prevented publishing the first inactive bundle; the destination was
absent and a fresh bounded rebuild succeeded without replacing an existing bundle.
Exact-commit remote CI/artifact acceptance remains pending; installed local proof
does not authorize customer APIs or public backend deployment.

## Remote Artifact Verification in Progress

Core run 40105056865 for 3091a81 has ten successful completed jobs. At inspection,
Windows packaged runtime and UI catalog/isolation were still running. All ten
available artifact archives match the exact head SHA and GitHub size/SHA-256
digest, pass ZIP integrity and contain 63 valid PNGs. Four inner inactive-release
file digests were also verified. The remote reusable API report confirms five
controlled GETs, two passing saved/confirmed HTTP-to-CLI jobs, no target requests
at review/admission and no raw response persistence. Evidence is in
evidence/api-ci-3091a81.json. This is a partial checkpoint: inspect both remaining
jobs and artifacts before accepting the combined API operator implementation.

Final inspection of run 40105056865 supersedes the pending snapshot above: eleven
jobs passed, but Windows packaged runtime failed when its combined installed
catalog/schema/license/recovery verification exceeded 30 seconds. It did not fail
the API assertion or operator UI proof. All twelve artifact archives, 210 PNGs and
four inner release digests are verified, including passing free, licensed and
installed licensed API UI reports. The failed job's uploaded artifacts do not
establish successful installed validation. Remote acceptance remains failed.

The packaging check now prints fixed stage names/elapsed time and has a finite
120-second verification budget. Target API/browser deadlines, assertions and
cancellation controls are unchanged; no test retry is introduced. The logs do
not identify the stalled stage in the older run, so no more specific cause is
claimed. Existing pre-installation tamper/identity/file-set checks passed. A fresh
installed check and exact-commit CI are required before accepting this adjustment.

The fresh f62882c release passed locally outside the checkout: all four package
digests, combined installed checks (stage logs complete at 2.13 seconds), installed
licensed API confirmation/CLI execution and recovery preservation passed. Its
value-free report is in evidence/installed-api-f62882c.json. Remote Windows CI
success is still unconfirmed; do not treat the local pass as a replacement.

## Controlled API Operator Acceptance

The later exact-commit checkpoint 68af26a passed all twelve Core jobs in run
40105470724, including Windows packaged runtime and installed licensed API UI
recovery. Its scaffold log reports 814 tests. All twelve artifact head SHAs,
GitHub sizes/SHA-256 digests and ZIP integrity were verified, including 210 PNGs
and four inner inactive-release file digests. The remote free operator report
confirms one actual GET, one job cancelled before execution and confirmation
invalidation on unsaved edits. The installed paid report confirms one GET,
preserved API binding/result after recovery, no external requests and no page
errors. Full evidence: evidence/api-ci-68af26a.json.

This accepts the controlled loopback API editor/review/confirmation/queue/worker
checkpoint. It does not accept arbitrary public/customer APIs, bearer authentication
or the overall product. The older 3091a81 timeout/failure record remains accurate;
this later successful run supersedes it for feature acceptance. The separate
f62882c packaging diagnostics/budget adjustment still needs its own remote result;
the successful older-budget run does not establish the cause of the earlier stall.
