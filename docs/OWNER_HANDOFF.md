# Owner handoff — local edition

The owner accepted their local test on 2026-10-29 and requested the next unified
real-use release, aiming to leave domain acquisition/connection for last. The
execution/data location must be selected before public deployment is implemented.
The required local-review decision below has therefore been satisfied; public
service acceptance and activation have not been granted by that local test.

The main workspace is http://127.0.0.1:8766/. Use its Reports link to select the
seven existing browser reviews, filter statuses and read evidence on the same
page. Automatic URL checks appear above them. Browser observations are labelled
separately from engine verdicts. Refreshing or opening reports never repeats tests.

Current installed runtime: 873329b3e5dba3dce5ca79e60ad067f08a1de9f9.
Release bundle: artifacts/releases/873329b3e5dba3dce5ca79e60ad067f08a1de9f9.
Existing local data: artifacts/local-review-2026-10-25/projects.sqlite.
The active process/UI locations are recorded in that workspace's preview-process.json.
Do not replace that database with a fresh demo workspace. Backup/recovery and
installation instructions are in LOCAL_QUICKSTART.md and the linked operations docs.

## Required decision

1. Review the delivered main page and decide whether this bounded local edition
   is accepted. If something is wrong, identify the visible behavior; the scheduled
   follow-up remains available to diagnose concrete findings. No further technical
   setup or domain/server purchase is required for the current local preview.

## Only if extending use or selling licenses

2. For supported standard website login, explicitly run a new URL check. If a login
   is found, use Login tests / Add a test account to enter the detected identifier
   and disposable password for that run only. See WEBSITE_LOGIN.md for limits.
   Other authenticated contracts still require local secret references and scoped
   implementation. Do not paste
   passwords into reports/issues/source control. Unsupported authentication still
   needs scoped engineering; providing credentials alone does not enable arbitrary
   login automation.
3. For paid distribution, choose customer entitlement terms and control the
   production signing key/trusted public key. Existing offline publisher tooling
   supports signed licenses, but test keys are not production issuer identities.
   Keep private keys and customer secrets outside the repository.
4. If public hosting or a broader commercial deployment is wanted, explicitly
   choose that scope and infrastructure. The current application runs locally;
   it does not require a central test-results server. No external hosting,
   subscription or purchase has been activated.

This delivery does not claim every function on every website is automatically
tested by AI. The automatic URL flow performs bounded read-only HTML/native-field
checks; optional standard HTML login uses a separately confirmed one-shot account.
Other login, API and database execution require supported explicit contracts.
The 100-case catalog is preserved and is not a universal execution guarantee.
