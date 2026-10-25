# Explicit Public HTTPS API Support

Owner authorization: 2026-10-25, following the completed bounded local edition.
Implement general HTTPS API support while preserving local-first storage and the
existing guards. This is product follow-up, not a reopened sprint.

## Delivery

- [x] Add an explicit HTTPS execution profile with strict origin/443 validation,
  public-IP pinning, certificate/hostname validation and no implicit reconnect.
- [x] Prove offline review and private child transport preserve the selected
  profile; deny private/mixed DNS answers and unsupported request authority.
- [ ] Connect owner-scoped saved settings, confirmation, queue and worker profiles.
- [ ] Expose the profile in the local UI with accurate endpoint/scope guidance.
- [ ] Prove saved UI/worker execution and failure boundaries on controlled TLS
  fixtures; retain existing free/licensed queue/cancellation/recovery checks.
- [ ] Complete exact-commit CI/artifact acceptance and current usage documentation.

The first public profile is unauthenticated GET/HEAD only, with an explicitly
configured origin and response assertions. No query/body, bearer authentication,
write operations or redirect following is enabled. Existing local fixtures retain
their default profile. DNS is validated at execution, not during offline review.
TLS verification cannot be disabled by a project setting. The supervised child
retains its 15-second total deadline and bounded response processing.

Six focused checks passed, including real TLS against an owned loopback harness
with a test-only connector and temporary CA. The harness preserves the public
profile's syntax/authorization path but routes its already validated destination
to an owned socket in the test only. This is not an Internet/customer deployment
proof or a production private-network bypass. Production exposes no such connector
override. Saved public execution and the operator UI remain pending.
