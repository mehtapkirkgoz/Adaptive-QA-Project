# Controlled Local Agent Pilot

Status: Signed outbound transport and real controlled local execution implemented;
exact-commit CI/artifact acceptance verified in SPRINT_10_ACCEPTANCE.md.
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
response reflection and replay fail closed. A strict loopback HTTP coordinator
factory now implements these exchanges; no public endpoint is activated.

The outbound client accepts only an explicit numeric loopback origin, ignores
environment proxies, rejects redirects and validates signed responses. Exchanges
have a five-second total deadline and no automatic retry. A supervised separate
agent process has a 150-second process-tree deadline and a 110-second execution
budget. Browser descendants do not inherit the token environment variable.

Run `python scripts/check_outbound_agent.py` for disposable enrollment,
coordinator startup and real local fixture execution. The drill verified two
passed UI cases, two validated PNGs, foreign-agent refusal, replay refusal,
zero proxy-canary contacts and released active capacity. Its safe report is
`artifacts/organizations/agent-pilot.json`. CI repeats this demonstration.

Trusted operators can invoke `python -m adaptive_qa.agent_worker --coordinator
http://127.0.0.1:8871 --agent-id <enrolled-agent-id>` after internal enrollment
and coordinator startup. Supply the token only through the
`ADAPTIVE_QA_AGENT_TOKEN` environment variable. There is no public enrollment
endpoint or finished operator setup UI. After an uncertain exchange, revoke and
re-enroll instead of guessing the consumed sequence or retrying work.

This verifies controlled local execution, not customer private-network access,
cross-machine connectivity, hosted TLS or remote attestation. Sweeping remains
explicit/on poll; no unattended cleanup service is claimed. Pilot findings must
be labeled synthetic rather than actual customer feedback.

Do not mark Sprint 10 complete until these behaviors and exact-commit CI/artifacts
are verified. Registry, broker, transport, client and worker tests cover the
internal boundaries; the separate-process drill verifies their integration.
