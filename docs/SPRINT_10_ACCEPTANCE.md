# Sprint 10 Acceptance — Organizations and Controlled Local Agent Pilot

Status: Technical acceptance complete for the documented local pilot scope;
ready for owner review. Issue #11 and milestone #11 remain open.
Date: 2026-10-23.

Implementation: `c6c5678ed8606987dfe80993cc406a9c2d1469cb`.
CI: [run 39905039071](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39905039071).
This documentation commit freezes evidence from that implementation separately.

## Verified Delivery

| Criterion | Evidence and practical scope |
|---|---|
| Organization management | Persisted owner/admin/member/viewer roles, existing-account membership administration, scoped projects/configuration and current-role checks in the authenticated local API/UI |
| Quotas and usage | Atomic pending/active/UTC daily reservations, transactional project limits and scoped usage snapshots; cancellation does not refund daily admission |
| Isolation/concurrency | Two disposable organizations, sixteen concurrent submissions, four admitted runs, one active claim per organization, two interrupted error records, two real completed runs/four passed cases/four validated PNGs |
| Access revocation | Cross-organization results/evidence, viewer execution, anonymous evidence and removed-member access denied; no browser external requests or page errors |
| Outbound agent | Separate supervised process, signed request/response protocol, project-bound expiring/revocable credentials and leases, two real passed cases/two PNGs, foreign-agent/replay refusal and released capacity |
| Protocol/process limits | Five-second exchanges, no redirects/environment proxies/automatic retries, independent fixed-target/case checks, 120-second leases and 150-second process-tree supervision |
| Onboarding/support | ONBOARDING_SUPPORT.md, AGENT_PILOT.md and prioritized synthetic observations in PILOT_FINDINGS.md |

The agent initiates connections and provides no service listener. A client test
forbids socket binding and DNS lookup during an exchange; this is not an OS-wide
audit of browser-native ports. Stored verification digests are secret keys and
require private storage. Raw tokens are not transmitted or inherited by browser
descendants. Agent outcomes are not remote attestation; the controlled drill
separately verifies real fixture execution.

## Exact-Commit Evidence

All twelve jobs succeeded. The Linux scaffold log confirms 656 unit tests passed.
Local Windows regression completed 656 tests: 655 passed, one symlink-permission
skip. Both-platform process jobs repeat registry/broker/transport/client/worker
checks. Twelve downloaded artifact SHA-256 digests and workflow head SHAs were
verified; 206 retained PNG files passed the existing PNG validator.
See [the permanent verification manifest](evidence/sprint10-acceptance.json).
Signed download URLs, databases and credentials are excluded from that record.

Regression reports retain 51 UI cases, reverse-order/context cleanup checks,
34 API cases, 15 database cases and their policy boundaries. The static demo
retains 100 definitions with zero API/external requests. Both-platform packaged
runtime reports verify old/live → new/restored → old/restored with the exact
implementation, two actual passed cases/two PNGs, revoked restored sessions,
preserved data and process cleanup. No public backend was activated.

## Limits and Owner Review

The owner kept automation local and the Pages demo unchanged. No customer website
or private network was contacted. Customer private-network access, hosted TLS,
an agent installer and finished enrollment UI remain deferred. Enrollment and
coordinator startup use trusted internal APIs demonstrated by the harness.
Cleanup is explicit/on poll, not an unattended service. Lost-response sequence
uncertainty requires operator recovery/re-enrollment; automatic replay is absent.

Shared execution supports a selected read-only UI subset on controlled fixtures.
The catalog does not imply arbitrary-site execution or full shared API/DB runs.
Some personal reporting/rerun features are not exposed for shared projects.
Comprehensive load/fairness, billing and customer rollout remain deferred.
Findings are synthetic engineering observations, not customer feedback.

The owner reviews these limits before closure. Keep issue/milestone open and the
scheduled follow-up quiet pending owner decisions. Do not claim the entire
product accepted or activate another deployment automatically.
