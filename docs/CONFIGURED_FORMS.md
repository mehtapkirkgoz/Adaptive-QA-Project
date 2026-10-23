# Configured Read-Only Form Checks

Status: supervised worker and dashboard form bindings are integrated. Saved
mapping configuration/UI and exact-commit integration CI remain unfinished.
This does not authenticate, submit a search, fill credentials or mutate form data.

## Supported Assertions

- LOGIN-001: one visible username/email input, masked password input and enabled
  submit control, connected to the same form.
- SEARCH-001: one visible enabled text/search input and enabled submit control,
  connected to the same form.

Default labels/button names include English and Turkish alternatives. All
alternatives form a union: multiple visible candidates are ambiguous, never
first-match wins. Hidden candidates are excluded. Custom JavaScript widgets or
unlabelled inputs may require explicit mappings or remain unsupported; a public
URL does not establish universal form compatibility.

Trusted orchestration calls run_isolated_form_test in document_process.py with
a typed ProjectConfig, existing private evidence directory and optional typed
ProjectElementMappings. Overrides replace default alternatives and must match
the project ID and known login/search logical keys. They may use exact roles,
labels or test IDs, optionally scoped by a test ID. They cannot change assertion
semantics, enable other case IDs or bypass destination policy.

## Isolation and Results

The worker shares the document supervisor: public HTTPS on port 443 with exact
allowed hosts, or the explicit fixed controlled-local fixture profile. Public
DNS answers and peer IPs are validated and pinned by the existing egress layer.
Only GET/HEAD requests are allowed. Fresh contexts block service workers,
WebSockets and downloads. Redirects cannot replace the exact configured document.
The default hard process deadline is 30 seconds, with an internal maximum of 120.
Cancellation, deadline or callback failure stops the owned process tree.

Configuration is transported in a private bounded input file rather than URL or
mapping command arguments. The child reconstructs typed mappings and repeats
validation. Result identity, output size and screenshot directory are checked.
Messages do not include raw labels, credentials or browser exceptions.

- PASSED: matched controls satisfy the fixed read-only assertion.
- BLOCKED: required controls are missing or ambiguous.
- FAILED: uniquely matched controls violate the assertion.
- ERROR: loading, network coverage, mapping execution or process supervision fails.
- CANCELLED: cancellation is observed; partial child results are discarded.

A PNG is optional evidence, not an assertion result. Screenshots may contain page
content and remain subject to existing project evidence scope and retention.
No environment secret is resolved by these checks.

## Verification

python scripts/check_general_forms.py exercises seventeen real Chromium DOM cases
without network or interaction events. python scripts/check_configured_forms.py
executes twelve separate owned HTTP child runs with decoded PNGs, contrasting
languages, explicit mapping, negative assertions, missing/ambiguous controls,
redirect refusal and denied network/write probes. Canary, write and interaction
contacts remain zero. CI never runs these scripts against public sites. Scenario
variants reuse existing catalog definitions and do not inflate its 100-case count.

## Dashboard Integration

Current discovery may expose local_form/public_form for LOGIN-001/SEARCH-001.
Personal/shared admission requires exact saved path/URL and current report policy;
explicit selection queues the separate read-only form worker. No other login case
is enabled. Login first anchors to a unique password field; remaining controls
must match within that form, so unrelated registration email fields are excluded.
Search anchors to its unique query field. Multiple password/query forms or multiple
alternatives within one form remain blocked unless a valid explicit mapping exists.
The dashboard uses defaults: it does not yet save or edit custom mapping overrides.
General-form runs have unknown comparison context rather than a sample fingerprint.
