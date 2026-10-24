# Local-First Edition: Local Acceptance Record

Implementation under review: 1c3704ce312679821133310b0536bdd1af74d7cf.
This is post-sprint conversion work; Sprint 10 remains closed. Local conversion technical CI acceptance is verified below; overall owner
product acceptance remains pending. Evidence is limited to controlled local fixtures, temporary
accounts/keys and the committed inactive package, not customer deployment.

## Verified Behavior

- Free dashboard starts without an account database, uses ephemeral session/CSRF
  tokens and transactionally permits one active local project.
- The explicitly provisioned licensed administrator uses password authentication
  and maps to the same local project IDs. Other accounts do not inherit them.
- Signed Ed25519 entitlements require separately supplied publisher public keys.
  Unknown issuers, invalid claims, tampering and exclusive expiry fail closed.
- Project creation and discovery/run admission check current validity; worker
  claims share a transactional signed concurrency bound. Expiry polling records
  cancellation. Existing records remain readable and are never deleted by expiry.
- The authenticated license panel loads status, imports a valid document, rejects
  invalid replacement, preserves the prior license and survives reload.
- Both built free and licensed browser flows discover and execute LOGIN-001 on an
  owned local fixture. Licensed execution uses separate actual customer CLI worker
  processes. Browser reports contain zero external requests/page errors.
- Offline snapshots include projects plus auth/license databases when present.
  Recovery into a fresh directory invalidates sessions, cancels pending work and
  preserves raw signed validity. Free recovery does not create an account store.
- A committed wheel was installed and exercised outside the source checkout.
  Signed entitlement/expiry, ownership and free snapshot/recovery checks passed.
  Four bundle digests and the installed 51 UI / 34 API / 15 database catalog were
  verified. The package stayed inactive and excludes the publisher issuance tool.
- Publisher tooling uses ephemeral test keys only, issues verifiable bounded
  entitlements, refuses repo paths/overwrites and prints no private signing key.

Final unit regression: 735 tests completed (734 passed, one Windows permission
skip). Both current built-interface flows and the installed package check passed.

## Evidence and Remaining Limits

Machine-readable local evidence is in evidence/local-first-1c3704c.json. It records
implementation SHA, bundle digests, value-free browser reports and the completed
regression result. It is local evidence, not downloaded GitHub artifact evidence.
Exact-commit GitHub jobs/artifact verification is still required before declaring
remote acceptance. The last checked frontend commit 25d64e4 passed Core and Pages.

The supported customer path is the local command group plus the committed wheel
and built UI. Legacy development/auth compatibility commands remain in the repo;
this open local runtime is not tamper-proof licensing. The managed legacy binary
switcher refuses licensed databases rather than starting an unenforced worker.
Managed licensed binary switching/rollback remains unavailable. The subsequent
packaged paid recovery browser drill passed against release 67f6f85; see
evidence/installed-licensed-recovery-67f6f85.json. Snapshot storage is customer-controlled and unencrypted;
issuer trust files/environment secrets are restored separately.

No actual publisher key, customer license, central account service, payment,
public backend or customer/private-network test was created. The Pages demo remains
non-executing. Interactive credential submission and broader reusable API/database
product work remain outside this conversion acceptance. Overall owner acceptance
is pending; this record does not close a new sprint or restart closed tracking.

## Installed Licensed Recovery Drill

The committed 67f6f85 wheel and extracted built UI were exercised outside the
checkout. Both server imports and actual local CLI workers used the installed
package. The browser signed in, imported a signed ephemeral license, discovered
the controlled fixture and passed LOGIN-001. After stopping the owned server, the
complete workspace was snapshotted and restored to a fresh directory. Restarted
recovery refused the old session, accepted a fresh password login and displayed
the preserved valid license and passed result. There were zero external browser
requests or page errors. No owner server/session was restarted. CI now repeats the
installed drill and uploads its value-free report; exact-commit remote results
remain pending. No managed legacy binary cutover is implied.

## Exact-Commit Remote Technical Acceptance

Commit 799e390f1bcaaf419b62f4c40c22886f5c9f29b8 passed all twelve jobs in
[Core checks 40018710391](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/40018710391).
The scaffold log reports 739 passing unit tests. All twelve artifact ZIPs were
downloaded and their GitHub SHA-256 digests/exact head SHAs verified. ZIP integrity,
206 PNG files and all four inner inactive-release file digests were validated.
The downloaded installed browser report confirms a real licensed CLI fixture run,
offline recovery, fresh password login, preserved license/results, zero external
browser requests and no page errors. Full machine-readable evidence is in
evidence/local-first-ci-799e390.json.

Earlier e27f476/67f6f85 runs were superseded/cancelled; they are not claimed successful.
The local conversion command path is technically verified within the documented
single-device scope. Legacy managed licensed binary switching remains unsupported;
no owner acceptance, new sprint closure, live customer deployment or external form
submission is implied. Remaining product work continues with controlled interactive
form execution under INTERACTIVE_FORMS.md. Historical pending notes above describe
their earlier checkpoint and are superseded by this exact-commit record.

## Installed Bounded Worker Cycle Follow-Up

Release 55fdae9 was built from its committed tree, installed outside the checkout
and checked against all four release file sizes/digests. Its installed catalog
remains 51 UI + 34 API + 15 database definitions. The licensed browser drill used
the installed `local worker-cycle` command for actual controlled discovery and
LOGIN-001 execution, then verified offline backup/recovery, invalidated sessions,
fresh password login and preserved signed license/results. No external browser
requests or page errors occurred. The release stayed inactive; the existing owner
server was not restarted. Machine-readable local evidence is in
evidence/installed-worker-cycle-55fdae9.json. This supplements the frozen conversion
acceptance; exact-commit remote CI/artifact acceptance for this follow-up is pending.
