# Target Authorization and Secret Management Contract

Status: Local sample controls implemented and verified. Production rollout remains gated.

## Authorized Targets

Project hostnames are explicit; subdomains require separate permission. Only HTTP(S)
URLs are accepted. Credentials in URLs, backslashes, control characters, ambiguous
hostnames, and unsupported schemes/ports are rejected.

The supported sample execution policy is HTTP to literal 127.0.0.1:8000 only.
No alternate loopback address, private subnet, hostname, or port is implicitly allowed.

The separate public guard rejects non-public destinations, mixed public/private DNS
answers, IPv6 transition mechanisms, and standard NAT64 translation prefixes.
DNS resolution has a five-second subprocess deadline. An upstream connection uses a
validated numeric IP directly and verifies its peer; it never re-resolves the original
hostname at connection time. Each new proxy connection is independently authorized.

## Browser Egress and Redirects

The browser uses a fixed loopback proxy with implicit loopback bypass disabled.
QUIC and HTTP/2 are disabled in the supported configuration; non-proxied WebRTC UDP
is disabled. There is no direct proxy fallback. Browser-level URL checks remain as
a second layer; they are not the sole redirect boundary.

HTTP redirect destinations are validated before forwarding. Relative redirects are
resolved against the current URL. Subsequent requests and HTTPS CONNECT targets pass
the same destination policy. HTTPS payloads are not decrypted: an HTTPS redirect
inside a tunnel is enforced at the next destination connection, not by reading its body.

Limits per browser run: 200 authorizations, 10 forwarded HTTP redirects, five-second
socket inactivity limits, 10 MiB HTTP response bodies, 20 MiB and 30 seconds per CONNECT
tunnel. The isolated worker also applies a total 30-second default deadline.

Service workers and browser WebSockets are blocked. The sample proxy denies CONNECT,
upgrades, write methods, and GET/HEAD request bodies. Public TLS method restrictions
require browser enforcement because a tunnel cannot inspect encrypted HTTP methods.

## Data-Changing Tests

Definitions declare changes_data. The current sample executor rejects definitions
marked as data-changing before starting the browser, and outgoing sample requests
are restricted to GET/HEAD. Demo form submissions change only the local DOM and use
fake values; no real authentication or database writes occur.

Future customer execution requires explicit project policies, approved accounts,
test data cleanup, and side-effect review before retries. Metadata alone does not
prove a test has no side effects.

## Verification and Deployment Gate

Local verification includes canaries for allowed/denied HTTP redirects, script
navigation, forbidden resources, HTTPS CONNECT, WebSockets, write methods, redirect
loops, and stopped-proxy fallback. No forbidden canary connection is accepted.

Public guard and socket behavior are unit-tested offline. The CLI is not enabled
for arbitrary public sites. Full public rollout additionally requires Linux testing,
OS/container egress enforcement, private-network agent policies, deployment-specific
NAT64/network rules, and independent isolation review. Proxy settings are not an OS
sandbox and do not constrain arbitrary Python code running outside the browser path.

## Cancellation and Recovery

Cancellation is requested through persistent state. A cancelled outcome is recorded
only after the supervisor handles the request; termination failures remain errors.
Finalization rejects late requests before they can contradict saved outcomes.

Explicit recovery repairs unfinished queue records only when the supported executor
lock is free. It does not stop orphan processes, undo operations, or automatically
replay tests. Inspect process cleanup and prior effects before retrying.

## Secrets and Evidence

Secrets are referenced by environment variable name and resolved at runtime.
Missing/blank values are rejected; standard string/repr output is masked.

Direct value access and serialization are not automatically safe. Never log secrets,
put them in source control, or send them to AI providers. Screenshot masking, request
sanitization, customer-level secret authorization, rotation/auditing, evidence access
control, and a production secret provider remain required for customer use.

Proxy request logs are disabled to avoid exposing URLs and headers. Current screenshots
contain only the controlled sample and fake demo values.

## AI Boundaries

When introduced, treat page content as untrusted data, validate structured responses,
keep authorization and success criteria outside model control, and enforce time,
request, and cost budgets.

## References

- [Chromium proxy bypass behavior](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md)
- [Playwright browser routing](https://playwright.dev/python/docs/api/class-browsercontext)
- [IPv4/IPv6 translation addressing](https://www.rfc-editor.org/rfc/rfc6052)
- [Local-use translation prefix](https://www.rfc-editor.org/rfc/rfc8215)
