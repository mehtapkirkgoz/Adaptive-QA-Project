# Automatic Native Functional Checks

Owner authorization: 2026-10-25, continue remaining work after reviewing the
limited HTML-only automatic results. This extends the one English workspace;
it does not reopen Sprint 10 or activate an external backend.

## First Increment

- Reuse existing FORM-001 / FORM-002 from the meaningful 100-case catalog.
- Automatically select them when discovery observes exactly one visible email
  field on the exact saved page. Recheck uniqueness/editability at execution.
- Exercise actual Chromium native validity with malformed `invalid` and valid
  `qa@example.test` on a detached copy retaining the site's native constraints.
- Disable scripts and exclude assets/frames; do not type in the live page, fire
  input events, submit forms, resolve secrets or contact an action endpoint.
- Preserve existing host/IP/TLS/redirect guards, child deadlines, cancellation,
  local evidence/results and the ten-check/five-page bounds.
- Report failed validity assertions separately from unavailable controls or
  technical errors. A restrictive domain pattern can legitimately reject the
  fixed valid test address; do not erase constraints to manufacture a pass.

These are functional checks of native browser validation, not proof of site
JavaScript validation, successful signup/login, server responses, payment or
complete workflow correctness. Discovery may observe a script-generated field
that is absent in initial HTML; runtime must report unavailable, never a pass.
Existing configured interactive contracts remain separate and explicit.

## Verification / Remaining

- [x] Source supervised proof: passes, restrictive-pattern failure, absent,
  ambiguous/disabled controls, redirect denial, zero input/submission side effects.
- [ ] Real one-button free/licensed UI admission and installed-wheel execution.
- [ ] Appropriate unit regression, exact-commit CI and artifact evidence.
- [ ] Safely update the owner preview without interrupting active work.

Future workflow expansion requires explicit typed expectations and operation
permission. Do not infer successful business behavior merely from a click or
HTTP 200, and do not enable arbitrary customer submissions.

Source controlled proof passed seven native outcomes: two passes, one restrictive
pattern failure, three unavailable-control outcomes and one blocked-navigation
technical error. The same proof retained five true HTML passes, two HTML failures,
rendered-form fail-closed behavior and zero mutation requests. The real free
one-button UI recorded nine passes including both native checks, with cancellation,
reload/no replay, empty/error/partial states, zero external UI requests and no page
errors. Full regression: 860 tests, 859 passed and one Windows permission skip.
The previous stale-history fixture correction 23e9a9a / Core 40196363155 has now
passed all twelve CI jobs; that does not substitute for this increment's CI.

The licensed one-button source UI also recorded all nine expected passing checks;
installed execution remains an explicit CI acceptance requirement.

## Eligibility / Legacy UI Proof Follow-up

The first implementation CI (7baa160 / Core 40198081102) found an outdated
legacy dashboard assertion expecting seven eligible cases after two native cases
were added. It is not accepted as green. Public personal/shared fixture snapshots
now explicitly include email evidence and expect nine supported candidates;
non-root owned variants also expect nine. Generic non-executing planning now
requires a unique observed email field before selecting either native case, not
merely a form of any kind. Runtime editability and uniqueness checks remain
independent and fail closed. The one-button automatic path already required this
evidence. These changes do not grant additional network or submission authority.

The corrected legacy personal dashboard proof and real organization UI proof
passed, including preserved custom mappings, role/revocation isolation, actual
shared execution/evidence and zero external UI requests/page errors. Thirty-nine
focused planning/admission/orchestration tests passed, including absent, hidden,
ambiguous and different-page email evidence. Replacement exact-commit CI is pending.
