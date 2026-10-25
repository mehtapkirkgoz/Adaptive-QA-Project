# Local Product Review

Current runtime implementation: `4b77ba5f4dac3d190b9234851fbdd7f81ebe27dd`.
The single-device edition and its bounded operator flows are technically verified.
Overall owner product acceptance remains pending.

## Verified Checkpoints

| Scope | Implementation | Core checks | Verification |
|---|---|---|---|
| Latest session/history recovery, including delayed old responses | 4b77ba5 | 40133176124 | 12 successful jobs, 12 verified archives, 210 validated PNGs, four inner release file digests |
| Bounded Windows inactive publication | ab08898 | 40132928164 | 12 successful jobs, 12 verified archives, 210 validated PNGs, four inner release file digests |

The complete local regression at 4b77ba5 ran 838 tests: 837 passed and one Windows
permission check was skipped. Both checkpoints include free, source-licensed and
installed-licensed browser evidence with no external browser requests/page errors.
See [latest recovery evidence](evidence/latest-recovery-ci-4b77ba5.json),
[publication evidence](evidence/publication-ci-ab08898.json) and
[local installed package proof](evidence/installed-recovery-ab08898.json).

## Open the Actual Free Panel

A separate local review workspace was started at `http://127.0.0.1:8766/`.
It uses `artifacts/local-review-2026-10-25/projects.sqlite`, outside source control.
It starts empty, requires no account and serves the current built dashboard.
No project, target request or test was created by opening it. An existing owner
workspace was not replaced or restarted. This is a loopback development preview,
not a public backend or an automatically installed service.

If that preview is still running, use it directly rather than launching a second
server on the same port. Its process metadata/logs are in the ignored review
directory. For startup on another device or after stopping it, follow the
[quick start](LOCAL_QUICKSTART.md).

## Owner Usage Review

1. Open the panel, create one project and select its configuration. Free mode
   should refuse a second active project without requiring registration.
2. Enter your intended target URL and exact allowed host names, then save.
   Inspect **Execution support**. Saving does not inspect the target or start work.
3. For a supported target, explicitly queue discovery. A separate one-shot worker
   processes this review workspace:

   ```powershell
   .\.venv\Scripts\python.exe -m adaptive_qa dashboard free-worker-cycle --database artifacts/local-review-2026-10-25/projects.sqlite
   ```

4. Review the discovered plan, select applicable checks and explicitly start them.
   Run the worker again, then inspect the recorded results. Catalog definitions
   are not a promise that every scenario applies to your site.

The worker uses the same workspace database as the panel and exits after its
bounded queue attempts. API/database jobs require their own explicit contracts
and separate worker commands. See the quick start before using those panels.
The GitHub Pages demo remains a separate illustrative interface with execution
disabled.

## Supported Boundaries

- General public HTTPS discovery and document/form inspection are read-only;
  they do not sign in, fill fields or submit searches.
- Interactive submissions and reusable API/database execution are demonstrated
  on explicitly configured owned controlled local fixtures. The API profile
  does not provide general customer authentication, and the database profile
  provides a confined SQLite count rather than arbitrary SQL or remote connectors.
- Signed paid licensing and password-authenticated local administration are
  implemented and verified with disposable keys/accounts. Actual publisher trust,
  customer license issuance, sales/payment operations and customer deployment
  have not been activated.
- Targets, results, evidence and secret values remain customer-owned/local.
  Application backups do not copy target database fixtures or environment values.

The remaining local milestone is the owner's usage review and any concrete issue
it reveals. Broader authenticated site/API/database support and commercial rollout
are separate product scope; this record does not declare them complete or reopen
closed sprint tracking. Keep existing review sessions intact during follow-up.
