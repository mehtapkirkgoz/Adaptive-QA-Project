# Owner handoff — local edition

The main workspace is http://127.0.0.1:8766/. Use its Reports link to select the
seven existing browser reviews, filter statuses and read evidence on the same
page. Automatic URL checks appear above them. Browser observations are labelled
separately from engine verdicts. Refreshing or opening reports never repeats tests.

Current installed runtime: 5a464290a8a94f19e2760f1776e2b321b05cd1a3.
Release bundle: artifacts/releases/5a464290a8a94f19e2760f1776e2b321b05cd1a3.
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

2. For a real authenticated workflow, provide an authorized disposable test account
   through local secret references and define the expected actions. Do not paste
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
checks; login, API and database execution require supported explicit contracts.
The 100-case catalog is preserved and is not a universal execution guarantee.
