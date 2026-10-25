# Local Product Review

Current simple-flow implementation: `e69a87d0b108a81bbf1e42f99e202fe017501dc3`.
The owner explicitly requested URL-only, one-button usage. Source free/licensed
browser proofs passed; exact-commit CI/package acceptance is tracked in
[SIMPLE_SITE_CHECK.md](SIMPLE_SITE_CHECK.md). The earlier verified checkpoints
below remain historical. Overall owner product acceptance remains pending.

## Verified Checkpoints

| Scope | Implementation | Core checks | Verification |
|---|---|---|---|
| Explicit public HTTPS API and save admission guard | 8dd1af5 | 40154721472 | 12 successful jobs, 12 verified archives, 212 validated PNGs, four inner release file digests |
| Latest session/history recovery, including delayed old responses | 4b77ba5 | 40133176124 | 12 successful jobs, 12 verified archives, 210 validated PNGs, four inner release file digests |
| Bounded Windows inactive publication | ab08898 | 40132928164 | 12 successful jobs, 12 verified archives, 210 validated PNGs, four inner release file digests |

The HTTPS implementation regression at b965faf ran 850 tests: 849 passed and one
Windows permission skip. Its installed TLS proof and the final follow-up are in
[HTTPS usage and acceptance](HTTPS_API.md) and
[exact-commit HTTPS evidence](evidence/https-ci-8dd1af5.json).

The earlier complete local regression at 4b77ba5 ran 838 tests: 837 passed and one Windows
permission check was skipped. Both checkpoints include free, source-licensed and
installed-licensed browser evidence with no external browser requests/page errors.
See [latest recovery evidence](evidence/latest-recovery-ci-4b77ba5.json),
[publication evidence](evidence/publication-ci-ab08898.json) and
[local installed package proof](evidence/installed-recovery-ab08898.json).

## Open the Actual Free Panel

The actual local review workspace is `http://127.0.0.1:8766/`, using
`artifacts/local-review-2026-10-25/projects.sqlite`, outside source control.
Following the owner's explicit update request, its server was restarted with the
new managed-check runtime. The database was backed up first, no workers were
active, and existing project/settings/queued-job counts were preserved. No target
request or test was started during the UI verification. Existing queued advanced
work was not processed. This is a loopback preview, not a public backend/service.

The default screen is URL-first. Refresh the page to load it. Do not launch a
second server on the same port or replace the workspace. Startup on another
device is documented in [LOCAL_QUICKSTART.md](LOCAL_QUICKSTART.md).

## Owner Usage Review

1. Enter the authorized site URL and press **Test et**.
2. Watch site inspection and automatic execution. No worker command is required.
3. Inspect the separate pass/fail/incomplete groups and optional test details or
   screenshots. **Durdur** cancels a running check. Refresh never repeats execution.
4. Open **Gelişmiş ayarlar** only for explicit API/database contracts or manual
   case selection. Those advanced queues retain their independent commands.

The simple flow derives exact host scope and selects only applicable independent
read-only inspectors from real discovery. It does not submit forms or authenticate.
Catalog definitions are not a promise of universal execution. The public Pages
demo remains illustrative and non-executing.

## Supported Boundaries

- General public HTTPS discovery and document/form inspection are read-only;
  they do not sign in, fill fields or submit searches.
- Explicit public HTTPS API execution supports unauthenticated GET/HEAD status
  contracts and optional top-level JSON boolean assertions. The dashboard offers
  GET with an explicit origin, path and per-request confirmation. No query/body,
  authentication, writes or redirect following is enabled. It was verified on
  owned TLS fixtures, not customer networks. See [HTTPS_API.md](HTTPS_API.md).
- Interactive submissions and database execution remain demonstrated on owned
  controlled local fixtures. The database profile provides a confined SQLite
  count rather than arbitrary SQL or remote connectors.
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
