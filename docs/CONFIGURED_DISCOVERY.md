# Configuration-Driven Discovery Worker

Status: Personal and organization dashboard admission is connected to the
configuration-driven worker. A subsequent owner-authorized demo observation is recorded below.

`discover_configured_target(project, budget, profile='public_https')` accepts a
typed ProjectConfig and CrawlBudget from trusted orchestration. It produces a
non-executing, inspected-pages-only plan; selected cases are not execution approval.
The existing local sample wrapper uses the same child/supervisor with an explicit
controlled_local profile, preserving existing local discovery and execution.

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

Saved settings expose static discovery capability without DNS or network access.
Authenticated personal/shared queues admit eligible HTTPS targets under existing
roles, ownership, capacity and cancellation rules. The separate worker rechecks
the stored scope and runtime destination guard. Reports are rebuilt server-side;
foreign-host snapshots are rejected and public cases have no execution binding.
Actual browser checks queued and cancelled HTTPS jobs without dispatching them,
then completed existing local fixture flows in both scopes.

Owner-authorized demo observation: https://books.toscrape.com/ yielded five
inspected pages and 21 requests with page_limit, without executing the plan.
This is a bounded demo observation, not general customer acceptance.
External dashboard test execution remains a separate unfinished step.
Public discovery does not by itself enable login, general UI execution, API or
database contracts. Pages remains a static demo and no backend is hosted publicly.

## Internal Document Execution

run_isolated_document_test in document_process.py supports only the existing five
independent document rules, with an existing private evidence directory and a
finite deadline of at most 120 seconds (default 30). It validates the typed
profile before starting a child, uses a bounded private input file, rechecks the
configuration inside the child and validates result identity/evidence scope.
The controlled-local fixture profile is explicit; it cannot widen public egress.
Redirected/non-HTML documents and denied coverage yield errors, not passing
verdicts. This internal API is not a dashboard execution authorization contract.

Run owned-fixture acceptance with python scripts/check_configured_document.py.
Public sites are never contacted by this script or by CI. A separate authorized
DOC-001 observation on Books to Scrape passed with one screenshot; the remaining
external rules and dashboard bindings are not claimed accepted.

## Dashboard Document Binding

The subsequent dashboard integration exposes public_document only for the five
independent document definitions. Admission requires the exact saved document_url,
selected read-only UI status and current owned discovery fingerprint. Public
settings expose execution_scope=document_ui; clients filter options using the
saved URL rather than unsaved edits. The separate worker selects the configured
public executor and retains process/case deadlines, cancellation and scoped PNG
persistence. Different crawled pages require a matching saved URL and new discovery.

Both personal/shared browser tests queue and cancel the public selection using
controlled snapshot data, without external traffic. A separate owner-authorized
Books to Scrape drill completed all five real document checks with scoped evidence.
External login/form/API/database execution remains unsupported. Historical notes
above describe the worker foundation before this integration, not current limits.
