# Local-First Edition: Local Acceptance Record

Implementation under review: 1c3704ce312679821133310b0536bdd1af74d7cf.
This is post-sprint conversion work; Sprint 10 remains closed. Product/remote CI
acceptance is pending. Evidence is limited to controlled local fixtures, temporary
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
