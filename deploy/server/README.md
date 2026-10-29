# Separate authenticated server edition

This is a portable, invitation-only, single-instance server package. It is not a public deployment. The owner currently has no hosting account or server. Existing local preview data must remain on the owner's computer; do not mount or copy its workspace into this edition.

The dashboard and bounded test workers run on the server. Targets, results and evidence therefore reside on that server, scoped to the signed-in account. This is a separate data boundary from the local edition and from the licensing service. Login test passwords remain memory-only; use authorized disposable accounts. Standard same-origin HTML login is supported; ambiguous forms, JavaScript-only login, CAPTCHA, MFA and SSO are unsupported. HTTP 200 alone does not prove authentication.

Each operator-provisioned account has one active project. The managed queue remains deliberately small and bounded. There is no public registration, billing, high availability, arbitrary-site authentication agent or production load-capacity claim. Local API/database tools and fixed public-demo execution are unavailable in this edition. Existing free/licensed local behavior and public Pages are unchanged.

## Host prerequisites

Use a maintained Linux host with Docker Engine and Docker Compose v2, sufficient memory for Chromium (at least 4 GB host memory is a starting allocation, not a capacity guarantee), outbound public HTTPS/DNS, and inbound TCP 80/443. The host must support non-root Chromium user-namespace sandboxing with the supplied seccomp profile. Startup fails if that sandbox is unavailable; do not work around it by using root, privileged mode or disabling the sandbox.

Only the reverse proxy publishes ports. The application listens inside its private container network. Keep the Docker socket and SSH private. Configure host security updates, restricted administrator access and encrypted offline backups before real customer use.

## Operator installation after obtaining hosting and a domain

Run from this directory in a private SSH terminal:

```sh
export PUBLIC_ORIGIN=https://qa.your-domain.example
docker compose config --quiet
docker compose build
docker compose run --rm --no-deps app hosted create-user --email owner@your-domain.example
docker compose up -d
docker compose ps
```

The account command prompts twice without echoing the password. Do not put passwords in command arguments, environment variables, chat or tracked files. Save PUBLIC_ORIGIN in the operator's deployment environment for subsequent commands. Create additional invited accounts with the same interactive command. Accounts do not inherit local preview sessions or data.

Point the domain's DNS to the host and allow ports 80/443 before starting the proxy. Caddy obtains the HTTPS certificate when the real hostname is reachable. Do not expose port 8080 or add another untrusted proxy: the application checks its canonical Host and Origin, rejects forwarded headers, and expects the supplied Caddy configuration to strip them. A server/provider, host provisioning and final public HTTPS validation still remain; buying a domain alone cannot provide hosting.

## Backups and upgrades

Persistent account/project data lives in the qa_data Docker volume; Caddy certificate state lives in caddy_data. During a maintenance window, stop app, snapshot qa_data using the host's encrypted backup facility, then start app again. Store backups outside the server and verify restoration into an isolated volume before relying on them. Never use `docker compose down -v` on a live deployment. Do not migrate the owner's existing local workspace implicitly.

Before an upgrade, retain the previous image ID, source revision and verified backup. Build the reviewed revision, then recreate the application during a maintenance window. Schema rollback may require restoring the corresponding backup; do not assume an older image understands newer data. Verify sign-in, account isolation, report access, cancellation and an explicitly authorized disposable workflow after deployment. This repository's isolated proofs do not replace that host-specific acceptance.

## Verification and provenance

`tests/test_hosted.py` checks account/route boundaries and local-workspace rejection. `scripts/check_hosted_ui.py` exercises the real backend with an owned HTTPS-origin browser adapter; it explicitly does not claim TLS termination. `scripts/check_hosted_container.py` runs only on disposable CI, using a private Docker network, an owned certificate authority and synthetic accounts. It checks the actual non-root sandbox, HTTPS cookies, persistence, backup readability and logout without contacting a target site. See the Hosted server package workflow for exact-commit container evidence. No public service is activated by these checks.

The seccomp profile is derived from [Microsoft Playwright](https://github.com/microsoft/playwright/blob/main/utils/docker/seccomp_profile.json), under the accompanying PLAYWRIGHT_LICENSE. Upstream SHA256: `cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849`. Packaged SHA256: `300d32eda3f35b6ab5a119c1a71efa6743a59999a352d2233d09a1abdaed5288`. The single policy change allows chroot without Docker's capability-dependent filter: Chromium needs that syscall after creating its own user namespace. All container capabilities remain dropped; this does not grant host chroot capability. The first CI proof failed on that syscall and is retained as failed evidence. Browser sandbox requirements follow [Playwright Docker guidance](https://playwright.dev/python/docs/docker) and [Chromium Linux sandbox design](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/sandbox/linux/README.md). Proxy header behavior follows [Caddy reverse_proxy documentation](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy). Base-image tags require reviewed rebuilds and updates; byte-for-byte reproducibility and production penetration testing are not claimed.
