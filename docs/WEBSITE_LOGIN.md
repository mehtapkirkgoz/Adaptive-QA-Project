# Inspected website test-account login

Owner request, 2026-10-28: inspect the supplied site for login before requesting
an existing test account; choose email or username from the inspected form, ask
for its password locally, and run supported login cases in the main workspace.
The usage-renewal automation was paused during implementation. The owner explicitly
requested its reactivation on 2026-10-28 after delivery.

The URL check remains read-only. It now records a value-free login candidate from
up to five inspected pages. No observed login is a limited-coverage observation,
not proof of site-wide absence. Multiple candidates require the exact login URL.
Registration and password-reset forms do not authorize a login submission.

The inline Login tests section first reviews the owned saved check. Only then
does it request the detected email/username and a disposable test-account password.
The owner confirms permission for one sign-in and supported sign-out. Admission
and execution retain shared ownership, licensing, capacity, claim, cancellation,
configuration revision and worker locking. No saved read-only policy is replaced.

Credentials travel over the loopback authenticated/CSRF-protected request, then an
anonymous pipe to one supervised child. They are not written to SQLite, project
configuration, environment variables, command arguments, reports, screenshots or
temporary credential files. Browser fields are cleared on submit/discard/unmount;
no local/session storage is used. Python memory is not a cryptographic zeroization
guarantee. Cookies and hidden CSRF values exist only in the child session's memory.

Supported execution is deliberately narrow: one native HTML form, one unambiguous
identifier and password, same-origin HTTPS urlencoded POST, bounded hidden fields,
verified TLS and public numeric peer pinning. Scripts never execute. No assets,
SSO, CAPTCHA bypass, MFA, registration, guessed passwords or automatic retry.
The native required attributes are reported as declarations, not server-side
empty-password tests. Generic success requires a new page without a password
form, cookies and an unambiguous exact-origin logout link. HTTP 200 alone is never
a pass. Sign-out requires a supported GET logout path, then both its response and
the previously authenticated page presenting the login form. This is bounded
observable evidence, not proof of every protected resource or application role.

POST redirects become GET on 302/303; GET navigation accepts 302/303, at most
three followed transitions per read and sixteen requests per child. Only exact
origin HTTPS paths without queries/fragments are supported. Other contracts
report Not evaluated rather than silently
expanding scope. Changed/ambiguous forms stop before credentials are submitted.
Each run has a hard maximum of 45 seconds, one POST attempt and no replay on reload.

Validation uses owned TLS fixtures only. The existing public demo cohorts, owner
reviews and one-time root checks must not be replayed for this change. The catalog
and public Pages demo remain unchanged. New results are separately identified as
website_login in existing owned interactive history and shown in the main page.

## Delivery checklist

- [x] Value-free detection, field-kind inference and fresh saved-check review.
- [x] One-shot memory-only credentials and guarded supervised standard HTML flow.
- [x] Inline English account entry, result details, cancellation and reload history.
- [x] Source/installed TLS and browser acceptance, regression and exact-commit CI.
- [x] Preserve owner database/settings and upgrade the versioned local preview.

## Accepted delivery

Implementation 873329b3e5dba3dce5ca79e60ad067f08a1de9f9 / Core 40694401848
passed twelve logical jobs. Twelve archives matched their byte counts, SHA-256,
ZIP CRCs and exact source commit; 229 PNGs and the four inactive release files
were verified. The source regression passed 945 tests with one existing Windows
permission skip. Both source and installed workers passed sixteen owned TLS
scenarios, including explicit authentication rejection, POST-302 and POST-303
success, ambiguous/changing forms, false HTTP-200 success, missing cookies,
ineffective logout, foreign redirects, untrusted TLS, private DNS, deadlines,
pre-admission/active-POST cancellation and duplicate submission prevention.
Source and installed desktop/mobile panel proofs passed with no external requests,
credential persistence, replay or changed saved settings.

The first Windows CI runtime job 122837211714 failed the existing owned
login-rejected fixture with a generic technical error. Its same-installed-package
eight-scenario HTTP proof passed locally; targeted CI retry 122844666993 passed.
The first local full installed verification reached the new passing worker/panel
proofs, then failed old public-browser fixture cleanup with Windows file-lock error
32. The targeted seventeen-scenario installed public-browser proof and the full
installed retry both passed. Neither initial failure is relabelled a pass; the
underlying cause of the CI fixture's generic error is not asserted.

The CI-built installed runtime now serves port 8766 from its new versioned
directory. An offline copy passed before the actual upgrade. A fresh backup and
before/after digests proved all thirteen prior tables, seven browser reviews and
ten old bookmark assets unchanged. No owner account was entered and no new public
target check/login ran. Older results lack the new value-free login observation:
the owner starts a new URL check explicitly to inspect login; reload never replays
an old check. No customer authenticated workflow is claimed verified.

The acceptance follow-up also keeps the HTTP unit-test worker mock alive until
its admitted background job finishes, preventing scheduler timing from allowing
the fixture test to fall through to a real network worker. Seven focused tests
passed after this test-only hardening; application/runtime code remains 873329b.
See evidence/website-login-ci-873329b.json and website-login-preview-873329b.json.
