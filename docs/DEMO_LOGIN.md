# Authorized Public Login Demonstration

Owner authorization, 2026-10-26: demonstrate successful login, wrong-password
rejection and logout on https://the-internet.herokuapp.com/login, with results
visible in the existing local panel. This supersedes the prior read-only limit
only for this explicitly selected demonstration and its public test account.

The site publishes its test credentials. Its official source uses POST /authenticate,
a session cookie and a 303 redirect to /secure or /login; GET /logout clears the
session and redirects to /login. Sources:
- https://the-internet.herokuapp.com/login
- https://github.com/saucelabs/the-internet/blob/main/server.rb

Existing reviewed public form execution expects boolean JSON with no redirects or
cookies. It cannot prove this site's login. Do not relax that contract or silently
claim an HTML login passed from HTTP 200 alone.

## Delivery sequence

- [x] Add a non-executing, exact-origin three-scenario contract. Require the known
  method-specific redirects and reject foreign origins, query/fragment, unexpected routes,
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
At the source-integration checkpoint no public login submissions had been performed. The 100-case
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


## Public demonstration and protocol compatibility finding

Runtime badd2e4 / Core 40367443724 completed all twelve jobs and twelve verified
archives with 224 PNGs. Its installed preview replaced 2f6d50c with all twelve
prior table digests preserved. Three deliberately bounded public-demo scenarios
then ran through normal authenticated local admission. All three produced technical
errors with uncertain submission counts; none is a website pass/fail assertion.
All earlier rows were preserved and exactly three new demo jobs were added. See
[evidence](evidence/public-demo-login-badd2e4.json) and
[accepted baseline CI](evidence/demo-login-ci-badd2e4.json).

The first implementation and mirror incorrectly expected HTTP 302 after a POST.
The site's current Gemfile.lock pins Sinatra 4.2.1. Its official redirect helper
uses 303 for non-GET HTTP/1.1 requests and 302 for GET. The historical three errors
have no captured response status, so do not retroactively label their cause proven.
This verified source-level protocol mismatch is corrected: exact login POST 303,
exact logout/protected-page GET 302, with the same fixed origin/routes. No generic
redirect authority is added. Sources:
- https://github.com/saucelabs/the-internet/blob/main/Gemfile.lock
- https://github.com/sinatra/sinatra/blob/v4.2.1/lib/sinatra/base.rb

The corrected review fingerprint binds the protocol revision and statuses. New
technical outcomes carry only a bounded diagnostic code (including a three-digit
HTTP status), never raw responses, credentials or cookies. Previous result rows
remain unchanged. A sixteen-scenario owned TLS proof additionally rejects the
obsolete POST 302 response, and verifies its diagnostic. The UI proof also checks
that explanation after reload. Finish this fix's installed/CI acceptance, then
perform one new controlled three-scenario verification cohort under the owner's
existing demo authorization. Preserve the first cohort and never automatically
replay an uncertain request or guess additional passwords.

## Accepted corrected demonstration

Implementation 3d9db06 completed Core run 40372756119 with all twelve jobs
successful. Twelve archives matched their source commit, byte counts and SHA-256;
ZIP CRCs, 224 PNGs and the four inactive release files were verified. Full local
installed release verification passed, including sixteen direct demo mirror
scenarios and five managed UI scenarios. The 932-test regression passed with one
existing Windows permission skip. See [CI evidence](evidence/demo-login-ci-3d9db06.json).

The verified versioned runtime was installed on port 8766 with all twelve prior
table digests preserved. One new bounded public-demo cohort then passed all three
scenarios: successful login, wrong-password rejection, and logout followed by
denied access to the protected page. Each scenario made exactly one login POST;
there was no automatic retry. Normal local review, confirmation and managed queue
admission produced the results visible in the existing panel. All previous rows,
including the first cohort's three technical errors, remain unchanged. Exactly
three new demo jobs were added. See [public demonstration evidence](evidence/public-demo-login-3d9db06.json).

This requested demonstration is complete. Refresh the existing local panel to
load the installed interface. Do not repeat the public submissions on scheduled
runs; inspect new CI failures or concrete owner findings only. This proves the
fixed public demo flow, not arbitrary-site login or customer deployment. Overall
product acceptance remains with the owner.
