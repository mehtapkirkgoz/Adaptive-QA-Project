# Controlled Local Agent Pilot

Status: Credential foundation implemented; transport/execution drill pending.
This prototype is not a deployed customer agent or a public agent endpoint.

## Intended Connection Model

The agent initiates outbound requests to a specifically configured coordinator.
It must not expose an inbound listener, accept arbitrary destinations/commands,
execute shell text or infer authorization from a public URL. The local pilot will
use numeric loopback coordinator/fixture addresses only; real hosted TLS/private
customer network activation requires separately authorized infrastructure.

## Current Credentials

The owner can enroll a credential through the trusted internal registry. It is
bound to exactly one organization and controlled project, expires within one day
and is explicitly revocable. Only hashes are persisted. SecretValue masks normal
string/repr output, but callers must still never serialize/log its value or place
it in source, command arguments, screenshots, reports or chat. There is no public
enrollment endpoint, CLI secret output or finished credential-handoff flow yet.

Authenticated requests will carry a monotonically increasing integer sequence.
Every accepted authentication consumes the sequence transactionally. Duplicates
and earlier sequences fail; no automatic retry may assume a lost response means
authentication was not consumed. Revocation, expiration, current owner privilege
and strict project policy are checked again. Restored backups revoke all recovered
credentials rather than guessing how to rewind sequence state safely.

## Remaining Acceptance

- Implement bounded, redirect/proxy-resistant outbound transport and explicit coordinator authentication.
- Link project-bound claims to the existing atomic run reservation without crossing tenant scope.
- Enforce leases, deadlines, cancellation and safe authenticated result/evidence publication.
- Reject revoked/expired/replayed/cross-project messages and terminal duplicate acknowledgements.
- Demonstrate real UI execution against local fixtures with no agent listener or arbitrary target access.
- Record only synthetic pilot findings; never present them as actual customer feedback.

Do not mark Sprint 10 complete until these behaviors and exact-commit CI/artifacts
are verified. Current implementation and tests are agent_registry.py and
test_agent_registry.py; the registry alone does not satisfy the outbound pilot.
