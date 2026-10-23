# Prioritized Synthetic Pilot Findings

These are engineering observations from disposable local fixtures and code
review, not customer feedback, production load results or private-network trials.
Revisit priorities with the owner before expanding deployment scope.

| Priority | Finding and evidence | Follow-up / acceptance needed |
|---|---|---|
| P1 | Agent execution is deliberately limited to two fixed UI cases and a numeric loopback fixture. The outbound drill proves local process integration only. | Before customer use, separately authorize cross-machine TLS, endpoint identity, network policy and a real private-network acceptance environment. |
| P1 | Enrollment/coordinator startup are internal operator APIs, not an installer or finished enrollment UI. | Design auditable one-time handoff, credential rotation/revocation and installation; prove no token leakage and current owner authorization. |
| P1 | A lost signed response leaves the client uncertain whether the server consumed its sequence. Automatic retry is disabled. | Preserve at-most-once work behavior; add an explicit recovery/rotation UX before unattended operation. |
| P1 | Lease cleanup is explicit/on poll; there is no always-running maintenance service. Expiry tests verify capacity release when swept. | Add supervised bounded maintenance and interrupted-agent acceptance before unattended deployment. |
| P2 | Two-organization concurrency tests cover admission races and isolation, not comprehensive load or sustained fairness. Personal jobs are processed first. | Measure starvation and queue latency; introduce reviewed scheduling policy with bounded capacity. |
| P2 | Shared execution uses a selected read-only UI subset. Existing personal report comparison/rerun features are not all exposed for organizations. | Extend only with current-role/configuration checks and scoped regression tests; keep unsupported actions explicit. |
| P2 | Evidence retention and size limits can intentionally remove/omit screenshots while preserving assertion outcomes. | Explain this in result UX; verify maintenance scheduling before operational rollout. |
| P3 | The accepted 100-case catalog spans 51 UI, 34 API and 15 database definitions; applicability differs by site and configuration. | Expand toward 200 using distinct missing behaviors from authorized pilots, not cosmetic variants. |

Resolved local findings include a React key collision between shared discovery/run
panels, transactional organization quota races and replay/scope checks in the
agent protocol. Their regressions remain covered by the organization UI,
isolation and agent checks. Final exact-commit CI/artifact acceptance is recorded
separately; this backlog does not itself establish sprint acceptance.
