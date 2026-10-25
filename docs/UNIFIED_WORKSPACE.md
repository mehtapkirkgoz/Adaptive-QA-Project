# Unified English Workspace and Public Check Diagnostics

Owner request, 2026-10-25: one understandable English workspace, not separate
simple/advanced pages. Keep URL-first execution, place optional controls in the
same coherent area, explain zero outcomes honestly, and fix the underlying errors.

- [ ] Replace the simple/advanced mode switch and dual layouts with one English
  workspace. Preserve paid/free limits, existing owner settings and API/DB tools.
- [x] Read existing owner records without rerunning targets: both demoqa.com and
  the-internet.herokuapp.com discovered 4–5 pages and ran five DOC checks; all ten
  outcomes were technical errors, not assertion failures. Raw adapter reasons
  were intentionally redacted in persistence. Screenshots show HTML did load.
- [ ] Reproduce on a controlled fixture containing off-host resources. Inspect
  document_process._execute: it treats any denied request (including external
  assets) as incomplete coverage and overrides all document assertions with ERROR.
  This is a likely cause, not yet proved for the owner runs. Do not remove IP,
  method, redirect, TLS or host guards to make results pass. Define and verify an
  honest HTML-only contract if static checks can safely exclude optional assets;
  form/rendered checks must retain their own fail-closed coverage contract.
- [ ] Add fixed safe diagnostic codes, never raw exceptions/URLs/headers/bodies.
  Show execution errors distinctly from failed assertions. Zero results must not
  appear as a successful completed check. Preserve historical results unchanged.
- [ ] Verify English UI, one-area navigation, zero/error/partial/pass/fail states,
  cancellation/reload, controlled public-like transport and existing advanced flows.
- [ ] Run appropriate regression and exact-commit CI/artifact checks, then upgrade
  the owner's preview only when no owner check is active; back up and preserve data.

Initial fix: reads now classify a historically completed run whose recorded
outcomes are all error/blocked/cancelled as execution_error, without rewriting
persisted results. Per-status outcome counts are returned. The UI now recognizes
that state. Full English/unified layout and root-cause repair remain unfinished.
Do not declare this request complete from the earlier simple-flow acceptance.

Current preview remains the prior runtime. Do not restart while owner jobs run.
Public demo sites are authorized for bounded read-only validation, but prefer
controlled fixtures until the diagnostic hypothesis has been verified.
