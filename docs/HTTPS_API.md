# Explicit Public HTTPS API Support

Owner authorization: 2026-10-25, following the completed bounded local edition.
Implement general HTTPS API support while preserving local-first storage and the
existing guards. This is product follow-up, not a reopened sprint.

## Delivery

- [x] Add an explicit HTTPS execution profile with strict origin/443 validation,
  public-IP pinning, certificate/hostname validation and no implicit reconnect.
- [x] Prove offline review and private child transport preserve the selected
  profile; deny private/mixed DNS answers and unsupported request authority.
- [x] Connect owner-scoped saved settings, confirmation, queue and worker profiles.
- [x] Expose the profile in the local UI with accurate endpoint/scope guidance.
- [x] Prove saved UI/worker execution and failure boundaries on controlled TLS
  fixtures; retain existing free/licensed queue/cancellation/recovery checks.
- [x] Complete exact-commit CI/artifact acceptance and current usage documentation.

The first public profile is unauthenticated GET/HEAD only, with an explicitly
configured origin and response assertions. No query/body, bearer authentication,
write operations or redirect following is enabled. Existing local fixtures retain
their default profile. DNS is validated at execution, not during offline review.
TLS verification cannot be disabled by a project setting. The supervised child
retains its 15-second total deadline and bounded response processing.

## Implementation History

The following notes record the intermediate implementation stages; final acceptance
is recorded below.

Six focused checks passed, including real TLS against an owned loopback harness
with a test-only connector and temporary CA. The harness preserves the public
profile's syntax/authorization path but routes its already validated destination
to an owned socket in the test only. This is not an Internet/customer deployment
proof or a production private-network bypass. Production exposes no such connector
override. Saved public execution and the operator UI remain pending.


Saved HTTPS metadata now requires explicit `profile: public_https`; legacy local
bindings keep their original shape and default. Offline save/review, scoped HTTP
admission/cancellation, stale confirmation/claim rejection and offline restoration
passed four new checks. The API-focused suite completed 62 tests, and six settings
checks passed. The prior full free browser/CLI API/DB flow also passed unchanged.
The editor shows the selected profile and full saved endpoint before confirmation.
Backend capability metadata prevents newer UI assets from offering HTTPS bindings
against an older running server. Existing review sessions are not restarted.
Queue history uses the neutral explicit_saved_api scope rather than falsely
labelling public jobs loopback-only. Real public-profile UI/worker TLS proof is next;
no customer or public test target has been contacted.


## Configure and Execute

In the updated free/licensed local dashboard, save an HTTPS origin as the project
Target URL, without a path/query, and list its exact allowed host. Enable the
explicit API response binding and select Public HTTPS. Enter the endpoint path
separately. The default response contract checks HTTP status only; optionally
select HTTP status and JSON boolean for one top-level boolean assertion.
Expected statuses are 2xx or 4xx. A status-only pass does not validate the body or
claim the whole site works. The dashboard exposes GET; the typed transport also
retains HEAD support for explicit internal status-only contracts.

Save, review the full saved endpoint, then explicitly confirm one request. Run a
separate one-shot worker against the same workspace:

```powershell
python -m adaptive_qa dashboard free-api-once --database C:/QA/workspace/projects.sqlite
python -m adaptive_qa local api-once --workspace C:/QA/workspace --trusted-keys C:/QA/publisher-public-keys.json
```

Choose the command for your edition; the three-queue worker cycle does not process
API jobs. New server processes advertise API binding profiles. An older running
server does not gain this Python feature from refreshing its UI assets; the new UI
fails closed when that capability is absent. Preserve active sessions/work and
start the updated runtime after completing them. No existing preview is restarted
by this change. The public Pages demo stays non-executing.

## End-to-End TLS Evidence

The new script exercises the actual free/licensed CLI and supervised API child,
using a separate test entry point to route a validated public-looking destination
to an owned TLS socket. Temporary CA trust is supplied only inside that test child;
production has no fixture address/CA override in its project configuration.
The routing tool is excluded from the wheel and checked during release verification.

Both source UI editions passed six explicitly confirmed jobs: JSON-positive and
404-negative contracts, redirect failure without follow, untrusted certificate
failure before HTTP, cancellation without execution, and non-JSON status-only
success. Each made exactly four owned HTTP requests, with no Authorization,
Cookie or Proxy-Authorization headers. Unsaved edits clear confirmation, old
backend capability metadata fails closed, and 390px layout was inspected. No
external UI requests or page errors occurred. Sixty-four API-focused tests pass.

Public jobs retain only status and fixed outcome-reason codes. TLS verification,
destination policy, HTTP status and JSON contract failures have safe UI labels;
raw worker exceptions/response bodies/headers are not persisted. Legacy local
job result shapes stay unchanged. Installed package proof and exact-commit remote
CI/artifact acceptance remain pending after this implementation increment.


## Installed Proof and CI Follow-up

The b965faf inactive release installed outside the checkout and passed the new
licensed HTTPS UI -> actual CLI -> supervised TLS child proof, including all six
jobs, status-only non-JSON success, certificate rejection and no secret headers.
All four release file digests matched and the fixture routing tool was absent
from the wheel. Full regression at that commit: 850 tests, 849 passed and one
Windows permission skip. Safe local evidence: docs/evidence/https-local-b965faf.json.
These are local installed results; remote exact-commit acceptance remains pending.

Intermediate a490c53 / Core 40153850838 failed the legacy dashboard queued-state
assertion after an asynchronous target save. It is not accepted. The follow-up
now disables new discovery admission while settings are unsaved/saving, while
retaining cancellation access, and the UI check waits for the actual saved HTTP
response. A held-save free browser regression and the full legacy dashboard
proof on owned port 8891 passed. Mobile HTTPS outcome reasons now wrap below the
job header and were visually inspected at 390px; the licensed TLS proof passed
again. No owner session was restarted.

## Final Controlled Acceptance

Implementation b965faf / Core 40154365536 and follow-up 8dd1af5 / Core
40154721472 both passed all twelve jobs. Each exact source commit's twelve
artifact ZIPs matched GitHub size and SHA-256 metadata, passed CRC checks, and
contained 212 structurally validated PNGs. Each inactive release manifest matched
its source commit and all four inner file sizes/digests; activation remained off.
Safe archive evidence is in docs/evidence/https-ci-b965faf.json and
https-ci-8dd1af5.json. The earlier a490c53 failed run remains historical.

Both runs include free, licensed and installed-wheel licensed HTTPS reports.
Each report confirms six admitted jobs, three passing contracts, four actual
owned TLS HTTP requests, redirect refusal, untrusted certificate rejection before
HTTP, cancellation without execution, no secret headers, no external UI requests
and no page errors. The final free browser report also proves discovery admission
is blocked during unsaved and pending configuration saves.

This completes the explicitly scoped unauthenticated HTTPS API follow-up on
controlled fixtures. It does not prove customer-network deployment. Authentication,
query/body requests and writes remain unsupported for public HTTPS. The catalog
and public non-executing demo behavior remain unchanged.

Preserve the existing 8766 preview: its older Python process intentionally does not
advertise the new HTTPS capability. Start an updated runtime after finishing that
session, using the commands above; refreshing assets alone cannot upgrade Python.
No owner session was restarted and no public backend was activated. Overall
product acceptance remains with the owner.
