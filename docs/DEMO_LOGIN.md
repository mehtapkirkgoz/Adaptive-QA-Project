# Authorized Public Login Demonstration

Owner authorization, 2026-10-26: demonstrate successful login, wrong-password
rejection and logout on https://the-internet.herokuapp.com/login, with results
visible in the existing local panel. This supersedes the prior read-only limit
only for this explicitly selected demonstration and its public test account.

The site publishes its test credentials. Its official source uses POST /authenticate,
a session cookie and a 302 redirect to /secure or /login; GET /logout clears the
session and redirects to /login. Sources:
- https://the-internet.herokuapp.com/login
- https://github.com/saucelabs/the-internet/blob/main/server.rb

Existing reviewed public form execution expects boolean JSON with no redirects or
cookies. It cannot prove this site's login. Do not relax that contract or silently
claim an HTML login passed from HTTP 200 alone.

## Delivery sequence

- [x] Add a non-executing, exact-origin three-scenario contract. Require the known
  302 transitions and reject foreign origins, query/fragment, unexpected routes,
  status codes and raw untyped scenario values. No credentials or session values
  are persisted in the contract.
- [x] Implement a supervised private-browser worker with a hard deadline, public
  numeric peer pinning and verified TLS. Limit each scenario to one exact login
  POST; allow only its exact main-frame redirects and, in the logout scenario,
  one logout GET. Retain fresh isolated profiles and bounded reads. Block foreign
  destinations, other writes, frames/popups and retry/replay. Do not broaden the
  general read-only proxy or the existing JSON form routes.
- [ ] Prove positive, negative and logout behavior on controlled local TLS mirrors,
  plus wrong status/route, false/missing DOM markers, rejected cookies, cancellation,
  deadlines and duplicate submission. Check both final URL and visible DOM outcome;
  logout must actually remove authenticated access in that ephemeral session.
- [x] Connect explicit local panel admission through existing ownership, policy,
  quota, confirmation, cancellation and sanitized results. Preserve the owner project
  and old results; do not silently replace the saved target or reuse owner cookies.
- [ ] After controlled proofs and exact-commit CI pass, run the three bounded public
  demo scenarios once. Report actual errors honestly; no bypass or repeated guessing.
- [ ] Verify installed package/UI and upgrade the preview with preserved row digests.

The worker has twelve owned TLS/browser outcomes: three passes for accepted login,
rejected login and logout; six transport errors for foreign redirects, unexpected
status, absent session cookie, ineffective logout, untrusted TLS and deadline; one
failed DOM assertion; one blocked missing form; one cancelled admission. Seven
contract/transport unit tests passed. Profiles were removed, each scenario made at
most one POST, and the hard-deadline scenario reached the owned POST handler.
The browser's direct proxy is deliberately dead. All documents are fulfilled by
the pinned verified-TLS transport; validated 302 transitions are followed through
explicit scoped browser navigation because Chromium can bypass route interception
when following redirects. The cookie jar exists only in the private child memory.
No customer input, cookies, raw response text, screenshot or trace is returned.

The local panel now has one inline demo section, with three scenarios, explicit
demo-account consent, a non-executing review and a separate run confirmation. It
uses the existing owned queue, shared quotas, licensed admission, claim tokens,
cancellation and sanitized history. One managed thread claims only the newly
confirmed job; it never drains existing owner work or replays work on reload.
The consent is specific to the fixed public demo and does not grant any write
permission to the saved target. Its configuration and result rows remain intact;
the demo history is attached to the owned project without replacing its target.
Configuration changes invalidate a prior confirmation.

Source UI-to-worker proof passed three real owned TLS login scenarios and cancellation
after a fourth POST had reached the fixture. Reload did not repeat a submission,
changing scenarios invalidated confirmation, and the saved read-only target remained
unchanged. Desktop/mobile screenshots were inspected; no overflow or external UI
request occurred. Six queue/HTTP tests include invalid CSRF/Origin, foreign ownership,
stale settings, shared capacity and paid-license expiry behavior.

Current state: source queue/panel integration implemented; full CI and installed
acceptance precede the three external demo scenarios and owner preview upgrade.
The expanded direct mirror proof passed fifteen scenarios, additionally rejecting
a duplicate POST attempt before contact, private DNS and an oversized initial
document. The 929-test regression passed with one existing Windows permission skip;
the additional paid-license test passed in the focused six-test queue suite.
No public login submissions have been performed by this increment. The 100-case
catalog and Pages demo remain unchanged. This is a known-demo integration, not
automatic login support for arbitrary customer websites.

CI follow-up: Core 40323061099 at 94d2266 passed eleven jobs, but the UI catalog
job was cancelled at its fifteen-minute overall allowance twice (jobs
121572642907 and 121579718974), without an assertion failure. The full installed
release verification passed locally, including the fifteen demo browser scenarios
and four managed UI scenarios. Increase only the CI UI-catalog job allowance to
twenty-five minutes so installation delays and the added source/installed proofs
can finish. Target, socket, child-process and cancellation deadlines stay unchanged.
The superseding exact commit still requires green CI and archive verification;
neither cancelled attempt is accepted as a successful run.
