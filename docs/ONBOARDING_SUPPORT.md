# Local Pilot Onboarding and Support

This guide covers synthetic local pilots. Public Pages is an interface demo;
it does not accept credentials or execute automation. Customer deployment,
commercial support commitments and production hosting are not enabled.

## Onboarding

1. Follow SETUP.md for locked dependencies, Chromium, interactive account
   provisioning and the built local dashboard. Protect auth/projects storage
   with OS account permissions. Never share databases or credentials publicly.
2. Sign in locally and create an organization. Its creator is the owner.
   Provision additional accounts interactively before adding their existing
   email through the organization access panel; this does not send invitations.
3. Assign the least required role. Owners administer the organization; admins
   configure projects and manage lower-privilege memberships. Members execute;
   viewers read. Admins cannot manage peer admins or the owner. Ownership
   transfer and public registration are not provided.
4. Create a shared project and save its explicit target/host policy. Shared
   execution currently supports the controlled loopback fixture root. Keep
   data-changing operations disabled. Secret settings contain environment
   references, never pasted plaintext credentials.
5. Start the controlled fixture as described in SETUP.md. Request discovery in
   the shared project, then run the separate discovery worker. Review detected
   features and the non-executing plan before selecting cases. Queueing a plan
   does not execute it; run the separate UI worker to process admitted work.
   LOCAL_RUNTIME.md describes managed discovery-once/run-once supervision.
6. Review actual statuses and scoped screenshots. Distinguish a failed assertion
   from blocked, skipped, cancelled or execution-error outcomes. The catalog has
   100 definitions; this does not mean all 100 apply to every target or are
   available through shared UI execution.
7. Verify access with a viewer and a second organization. Remove pilot members
   when access is no longer needed. Membership changes are checked again when
   work is claimed and results/evidence are accessed.

Agent enrollment/startup uses trusted internal operator APIs. Reproduce the
disposable end-to-end agent exercise with check_outbound_agent.py and follow
AGENT_PILOT.md for its credential, sequence and local-only limitations. There is
no customer agent installer or finished enrollment interface.

## Quotas and Operations

Default organization limits are 20 projects, five pending runs, one active run
and 100 daily admissions. UTC daily usage includes cancelled admissions; cancel
does not refund the daily counter. Global/per-user queue limits also apply.
Shared usage is a snapshot refreshed in the panel. It is not billing or a
subscription entitlement system. Personal work is processed before shared work
by the current one-job worker, so continuous personal traffic can delay it.

Stop workers before offline backup/restore and follow OPERATIONS.md and
LOCAL_RUNTIME.md. Restored sessions and agent credentials are revoked; re-enroll
agents rather than reusing credentials from a copied database. Live agent leases
block interrupted-run recovery. Expired/revoked leases require a trusted sweep
or another poll; no automatic retry should replay abandoned work.

## Support Triage

| Symptom | Check and next action |
|---|---|
| Sign-in fails | Confirm the local origin and provisioned account; do not disable Host/Origin/CSRF guards. |
| Project or evidence is unavailable | Check current organization membership, selected project and evidence expiry. Cross-scope requests intentionally reveal no resource details. |
| Admission refused | Review pending/active/UTC daily usage and global queue capacity; do not repeatedly resubmit. |
| Run remains queued | Confirm a separate worker is running and the current project/discovery settings still match. |
| Agent exchange fails | Stop it, check local coordinator availability and lease/credential expiry; revoke/re-enroll after uncertain sequence state. |
| Screenshot missing | Check retention and PNG limits; an omitted screenshot does not change assertion status. |
| Interrupted execution | Preserve partial outcomes, stop live processes and follow documented recovery; never fabricate a passed result. |

For a repository support issue, include the source commit, OS/Python versions,
synthetic reproduction steps, expected/actual statuses and a redacted error
category. Review screenshots before sharing. Exclude database copies, passwords,
tokens, signing keys, customer records, connection strings and secret values.
Report a suspected isolation failure privately to the owner first; stop the
affected local workers and revoke affected credentials. No support SLA is claimed.
