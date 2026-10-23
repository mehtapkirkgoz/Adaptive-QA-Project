# Configuration-Driven Discovery Worker

Status: Internal worker foundation implemented; external profile is not yet
connected to dashboard admission. No external site has been tested by this increment.

`discover_configured_target(project, budget, profile='public_https')` accepts a
typed ProjectConfig and CrawlBudget from trusted orchestration. It produces a
non-executing, inspected-pages-only plan; selected cases are not execution approval.
The existing local sample wrapper uses the same child/supervisor with an explicit
controlled_local profile, preserving current dashboard behavior.

## Profiles and Bounds

- public_https accepts HTTPS on port 443 and only configured exact hostnames.
  Obvious private/loopback literals, localhost, ambiguous numeric hosts, start
  queries/fragments and oversized configuration are rejected before process start.
- Shape validation performs no DNS or connections. Actual requests still use
  DestinationGuard, bounded DNS resolution, validation of every resolved address,
  numeric pinned connections and peer checks. Mixed public/private DNS answers
  fail closed. Redirects cannot add hosts, switch to HTTP or introduce private IPs.
- controlled_local permits only the existing 127.0.0.1:8000 fixture origin and
  canonical configured paths. It cannot authorize another private service.
- Both profiles allow GET/HEAD requests only, block WebSockets/service workers,
  disable downloads and use fresh browser contexts. They do not sign in, submit
  forms or run the test plan. Method restrictions do not establish business-level
  semantics for arbitrary website endpoints.

Existing crawl/page/depth/request limits and the parent process-tree deadline
remain authoritative. Cancellation or timeout discards partial child output.
Configuration travels through a private temporary input file (maximum 16 KiB),
not URL/credential arguments. Child output is bounded to 2 MB and errors remain
generic. Snapshot collection does not read input values and removes URL queries
and fragments; paths and visible labels remain untrusted, potentially sensitive
project data, not universally redacted content.

Denied routes are recorded as limited network coverage even when blocked before
the proxy sees them. Such coverage cannot establish feature absence. A blocked
script therefore preserves unknown findings instead of silently yielding absent.

## Verification and Remaining Integration

`python scripts/check_configured_discovery.py` creates three owned local fixtures
and separate child runs with configured account/search/limited-document starts.
It verifies contrasting findings, non-executing plans, unknown findings after a
denied resource and zero canary contacts. Public guard/profile selection and mixed
DNS refusal are verified without external traffic. Real replacement-child tests
verify cancellation and deadlines. Existing document/discovery flows regress
against the shared collector. These are not a real public HTTPS acceptance run.

Next: connect stored project configuration to authenticated admission and report
validation for this profile, preserve personal/organization scopes, and validate
an owner-authorized external HTTPS target before claiming dashboard readiness.
Public discovery does not by itself enable login, general UI execution, API or
database contracts. Pages remains a static demo and no backend is hosted publicly.
