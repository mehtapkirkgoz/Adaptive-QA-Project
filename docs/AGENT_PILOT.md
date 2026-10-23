# Controlled Local Agent Pilot

Status: Credentials, signed-message authentication and scoped work leases implemented;
network transport and actual outbound execution drill pending.
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

The broker binds a 120-second lease to one enrolled agent and its project. Only
LOGIN-001/SEARCH-001 are eligible in this initial pilot. Run/reservation activation
and lease creation share a write transaction. The private worker claim token and
submitter identity are never returned in the work envelope. Each result/PNG,
cancellation check and finish rechecks lease/agent/scope inside the underlying
queue transaction. PNG transfer is additionally bounded to 256 KiB per result.
Expired/revoked/cancelled leases preserve earlier results, release matching quota
and never replay/requeue abandoned work. Trusted sweep is bounded to 100 leases.
Live leases block local operator recovery; offline restore cancels their copies.

The transport authentication primitive signs exact request direction, endpoint,
sequence and bytes with HMAC-SHA256 using a derived credential key; the raw token
need not cross the connection. Responses use a separate direction prefix. Stored
digests therefore also act as verification keys and must be protected as secret
credentials, not treated as safe-to-share password hashes. Invalid body/path,
response reflection and replay fail closed. No HTTP endpoint is exposed yet.

- Implement bounded, redirect/proxy-resistant outbound transport and explicit coordinator authentication.
- Exercise the implemented project-bound claims and result publication over the outbound transport.
- Reject revoked/expired/replayed/cross-project messages and terminal duplicate acknowledgements.
- Demonstrate real UI execution against local fixtures with no agent listener or arbitrary target access.
- Record only synthetic pilot findings; never present them as actual customer feedback.

Do not mark Sprint 10 complete until these behaviors and exact-commit CI/artifacts
are verified. Current implementation and tests are agent_registry.py and
test_agent_registry.py, agent_broker.py and test_agent_broker.py. These internal
components alone do not satisfy the outbound pilot.
