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
- [ ] Connect explicit local panel admission through existing ownership, policy,
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

Current state: supervised worker foundation; queue/panel integration is unfinished.
No public login submissions have been performed by this increment. The 100-case
catalog and Pages demo remain unchanged. This is a known-demo integration, not
automatic login support for arbitrary customer websites.
