# Unified English Workspace and Public Check Diagnostics

Owner request, 2026-10-25: one understandable English workspace, not separate
simple/advanced pages. Keep URL-first execution, place optional controls in the
same coherent area, explain zero outcomes honestly, and fix the underlying errors.

- [x] Replace the simple/advanced mode switch and dual layouts with one English
  workspace. Preserve paid/free limits, existing owner settings and API/DB tools.
- [x] Read existing owner records without rerunning targets: both demoqa.com and
  the-internet.herokuapp.com discovered 4–5 pages and ran five DOC checks; all ten
  outcomes were technical errors, not assertion failures. Raw adapter reasons
  were intentionally redacted in persistence. Screenshots show HTML did load.
- [x] Reproduce on a controlled fixture containing off-host resources. Inspect
  document_process._execute: it treats any denied request (including external
  assets) as incomplete coverage and overrides all document assertions with ERROR.
  This is a likely cause, not yet proved for the owner runs. Do not remove IP,
  method, redirect, TLS or host guards to make results pass. Define and verify an
  honest HTML-only contract if static checks can safely exclude optional assets;
  form/rendered checks must retain their own fail-closed coverage contract.
- [x] Add fixed safe diagnostic codes, never raw exceptions/URLs/headers/bodies.
  Show execution errors distinctly from failed assertions. Zero results must not
  appear as a successful completed check. Preserve historical results unchanged.
- [x] Verify English UI, one-area navigation, zero/error/partial/pass/fail states,
  cancellation/reload, controlled public-like transport and existing advanced flows.
- [x] Run appropriate regression and exact-commit CI/artifact checks, then upgrade
  the owner's preview only when no owner check is active; back up and preserve data.

## Initial Increment (Historical)

Initial fix: reads now classify a historically completed run whose recorded
outcomes are all error/blocked/cancelled as execution_error, without rewriting
persisted results. Per-status outcome counts are returned. The UI now recognizes
that state. At that initial increment, the unified layout and root-cause repair were unfinished; the implemented checkpoint below supersedes that status.
Do not declare this request complete from the earlier simple-flow acceptance.

Current preview remains the prior runtime. Do not restart while owner jobs run.
Public demo sites are authorized for bounded read-only validation, but prefer
controlled fixtures until the diagnostic hypothesis has been verified.

## Implemented and Locally Verified

The local product now has one English workspace. URL, automatic execution and
results stay together. Optional controls are small inline groups for saved sites,
website scope, API, database, form matching, secret references and manual history;
there is no simple/advanced page switch. The #advanced fragment only expands the
same inline controls for compatibility. Unsaved edits block automatic admission,
status/notice feedback survives option opening and session reopening, and paid
sign-out/project pagination remain available.

A controlled HTML fixture with external assets reproduced the blanket ERROR.
The five independent DOC contracts now explicitly inspect initial HTML structure:
page scripts are disabled, scripts/styles/images/embedded documents are excluded
without contacting them, and the main document still requires approved pinned
egress, valid TLS, exact URL and successful HTML loading. Rendered form inspection
retains strict resource coverage. Updated contract steps prevent comparing older
rendered-document results as identical contracts. Controlled proof: five passes,
two true assertion failures, denied redirect, no mutation, and a rendered form
still failing closed. No destination, TLS, method or deadline guard was relaxed.

One bounded DOC-001 request on each owner-authorized public demo (demoqa.com and
the-internet.herokuapp.com) passed after the fix. This is not a full five-case
rerun and does not rewrite the owner's previous ten technical errors. Historical
errors remain audit records. Fixed diagnostic codes distinguish HTML loading,
policy/coverage, deadlines and process errors; unknown raw messages remain redacted.
Partial and all-error checks receive distinct display states, with no-result
counters shown as unavailable rather than successful zeroes.

Latest full regression: 858 tests, 857 passed and one Windows permission skip.
The free legacy API/database/session/late-response browser proof passed in the
unified inline controls. Real free/licensed one-button proofs also passed during
implementation. Final compact-layout/state proof, installed wheel verification,
exact-commit CI/artifacts and safe owner-preview transition remain pending.

## CI Contract Follow-up

The first f5510f2 run (Core 40193262094) failed the older configured-document
fixture expectation: it required an ERROR solely because an off-host script was
excluded. This checkpoint is not accepted. The expectation now explicitly tests
the source-HTML contract: valid HTML with an excluded script passes, invalid HTML
with that same script fails, and the off-host canary receives zero requests.
Bound navigation redirects still error. Direct owned-sample DOC execution now
uses the same source-HTML inspector as managed/configured runs, keeping contract
fingerprints and all entry points consistent. No broader egress was enabled.

## Installed and Owner Preview Checkpoint

The b0d84b1 inactive package passed installed UI, supervised child resolution,
API/database/license recovery and dedicated installed HTML-boundary proofs.
It produced five HTML passes and two genuine HTML assertion failures with no
mutation, blocked redirected navigation and retained rendered-form coverage.
All four release file sizes/digests matched. Unified English source/installed UI
proofs cover blank/error/partial outcomes, explicit cancellation, reload without
replay, inline settings and mobile fit. Safe local proof:
[evidence/unified-local-b0d84b1.json](evidence/unified-local-b0d84b1.json).
The owner preview was backed up and updated only with no active checks; all prior
row digests matched afterward. Its previous two error runs were not rewritten.
Core 40193691217 exact-commit artifact acceptance remains pending.

## Final Controlled Acceptance

b0d84b1 / Core 40193691217 passed all twelve jobs. Each of twelve downloaded
archives matched exact source commit, API size/SHA-256 metadata and ZIP CRC.
There were 220 structurally validated PNGs; the inactive release's source identity
and four inner file digests matched. All free/licensed/installed unified UI reports
verify English one-area operation, empty/error/partial states, real pass/fail
separation, cancellation, reload/no replay, inline options and mobile fit. Source
and installed HTML proofs verify five passes, two assertion failures, blocked
redirects, zero mutations and retained rendered-form failure boundaries. The
configured-document proof adds eighteen cases and zero canary/write contacts.
Existing API, database, licensing/recovery, organization and process checks passed.
Exact evidence: [evidence/unified-ci-b0d84b1.json](evidence/unified-ci-b0d84b1.json).

The owner preview already serves this English unified flow and the source-HTML
fix. Its earlier records remain unchanged; a new explicit Test website request is
required to create new outcomes. This scoped request is technically ready for
owner review. No complete-site quality guarantee, universal case coverage, AI
model execution, customer deployment or public backend activation is claimed.
