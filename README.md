# Adaptive-QA-Project

An AI-assisted QA platform under development for website discovery and applicable UI, API, and database tests.

**Current sprint:** [Sprint 8](docs/SPRINT_8.md) started on 2026-10-22 after owner acceptance and closure of Sprint 7. Owned reports provide status filters, JSON downloads, explicit subset reruns, qualified historical comparisons and separate catalog/requested/recorded counts. Owned screenshots expire after seven days with bounded cleanup; assertion history remains. Flaky signals and further catalog expansion are pending. The Sprint 7 delivery evidence below remains the accepted baseline.

**Accepted baseline:** Sprint 7 is accepted; its issue and milestone are closed. The local React dashboard supports authenticated projects, scoped configuration/references, guarded discovery, explicit read-only UI runs, progress/results and owner-authorized PNG evidence. The catalog remains 40 UI, 20 API and 15 database definitions. Customer-site execution and deployment are not enabled.

Sprint 7 implementation `2608fc40919e8e530c07b434538f70ac4070f118` passed 500 unit tests and all seven CI jobs. Six downloaded archive digests/head SHAs, 184 retained PNGs and 178 filesystem references were verified. The real panel completed LOGIN-001/SEARCH-001 and decoded authorized evidence while denying anonymous/other-owner access. See [acceptance and limits](docs/SPRINT_7_ACCEPTANCE.md), [verification manifest](docs/evidence/sprint7-acceptance.json), and [CI](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39742021256). The owner has authorized Sprint 8; future sprint starts and closures remain with the owner.

Earlier [Sprint 6 acceptance](docs/SPRINT_6_ACCEPTANCE.md) verified free local Ollama/qwen3:4b without an API key. Its nine model fixtures scored 8/9 website kinds overall and 4/5 on the separate holdout; errors and abstentions remain recorded. These small-fixture measurements do not establish arbitrary-site accuracy. See [Ollama setup](docs/OLLAMA.md), [Sprint 5 acceptance](docs/SPRINT_5_ACCEPTANCE.md), [Sprint 7 progress](docs/SPRINT_7.md) and [dashboard API contracts](docs/DASHBOARD_API.md). Destination, data-change, deadline and non-executing plan policies remain authoritative.

## Project Plans

Sprints follow goals and acceptance criteria without a fixed two-week commitment.

| Sprint | Goal | Status |
|---|---|---|
| 0 | Architecture, models, configuration, GitHub workflow | Completed |
| 1 | First controlled end-to-end execution | Completed |
| 2 | Website discovery | Completed |
| 3 | UI catalog and element matching | Completed |
| 4 | API tests | Completed |
| 5 | Database validation | Accepted; issue closed |
| 6 | AI integration | Accepted; issue closed |
| 7 | Web dashboard | Accepted; issue and milestone closed |
| 8 | Reporting and catalog expansion | In progress |
| 9 | Domain and deployment | Planned |
| 10 | Customer management and pilot | Planned |

See [architecture](docs/ARCHITECTURE.md), [sprint plan](docs/SPRINT_PLAN.md), [Sprint 1](docs/SPRINT_1.md), [GitHub workflow](docs/GITHUB_WORKFLOW.md), and [security contract](docs/SECURITY_CONTRACT.md).

## Setup

Use Python 3.13 or newer. From the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m playwright install chromium
```

Subsequent commands assume an active environment. See [setup](docs/SETUP.md). SQLite is included with Python. No service or AI key is needed locally. Redis/Celery and PostgreSQL remain the production direction.

## Automated Verification

```powershell
python -m unittest discover -s tests -v
python scripts/check_process_lifecycle.py
python scripts/check_network_security.py
python scripts/check_local_browser.py
```

Keep port 8000 available and run these scripts sequentially. They manage local servers and do not test external sites.

Current local results:

- **500 unit tests passed locally:** platform rules, adapters, authentication and project/settings ownership, not website scenarios.
- Real Chromium login/logout, project management and masked configuration checks passed (`scripts/check_web_auth.py`, owned port 8765).
- **3 real OS lifecycle checks passed on Windows:** deadline, active cancellation, and crash lock release.
- **9 real Chromium security checks passed:** forbidden canaries received no connections.
- **40 queued UI scenarios passed:** matching JSON results and PNG screenshots.
- Dependency compatibility and compilation checks passed.

Remote verification passed for the implementation commit on Linux and Windows. CI installs Chromium/system dependencies, runs security and smoke checks, and uploads `local-browser-evidence` with seven-day retention.

## Smoke Catalog

Sprint 8 adds DOC-001–005, five read-only HTML document rules that do not depend
on login or commerce. Six further semantic rules cover computed accessible names,
label associations, viewport zoom and automatic refresh, with feature prerequisites.
The current full catalog has **86 scenarios: 51 UI,
20 API and 15 database**. Thirty-three checks on three offline site types and eleven
deliberate defects verify the new rules; fixture variants do not increase counts.
See [cross-site scope and limits](docs/UI_CATALOG.md#cross-site-expansion).

The table below retains the original ten cases. Thirty additional scenarios are
listed in the [full catalog guide](docs/UI_CATALOG.md).

| Case | Behavior |
|---|---|
| LOGIN-001 | Login fields, masked password input, and submit button are visible |
| LOGIN-002 | Empty username blocks submission |
| LOGIN-003 | Empty password blocks submission |
| LOGIN-004 | Fake credentials display the demo-only status |
| SEARCH-001 | Search field is visible and its submit button enabled |
| SEARCH-002 | Query displays the expected no-results message |
| SEARCH-003 | Empty query blocks submission |
| SEARCH-004 | Whitespace input displays the search prompt |
| NAV-001 | Sign in link reaches the login section |
| NAV-002 | Search link reaches the search section |

Each scenario uses explicit assertions and a fresh context. These are controlled sample checks, not universal site tests or AI interpretation of text steps.

For manual execution, start the sample server in one terminal:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory samples/web
```

In another terminal:

```powershell
python -m adaptive_qa.local_worker submit SEARCH-002
python -m adaptive_qa.local_worker run-next
```

The worker processes the oldest queued job and exits. Direct debugging: `python -m adaptive_qa.local_browser --case SEARCH-002`. Direct execution uses operation timeouts; the worker adds a total process deadline.

## Persistent Queue

Default queue: `artifacts/jobs.sqlite3`. Use `--database <path>` before the subcommand to select another database.

```powershell
python -m adaptive_qa.local_worker list
python -m adaptive_qa.local_worker list --status running --limit 20 --offset 0
python -m adaptive_qa.local_worker status <job-id>
python -m adaptive_qa.local_worker cancel <job-id>
python -m adaptive_qa.local_worker retry <job-id>
python -m adaptive_qa.local_worker recover-interrupted
```

Job states: queued, running, cancel_requested, finalizing, completed, cancelled. Result states: passed, failed, skipped, blocked, cancelled, error. Completed does not imply passed. Lists default to 50 records and are capped at 500.

- Pending cancellation is immediate; active cancellation terminates the child tree.
- Default total timeout is 30 seconds; normal cancellation polling is 0.2 seconds.
- Finalization freezes the result before JSON storage; late cancellation is rejected.
- Retry creates a new attempt linked to a completed failed/error attempt.
- Recovery requires a free executor lock and marks unfinished records as errors.
- Recovery does not replay operations or prove orphan processes have stopped.

One supported local executor or recovery operation may own a database at a time. Review process cleanup and previous side effects before retrying. Do not share live SQLite files across machines or synchronization services. A remaining lock file does not mean the OS lock is held; do not delete it to bypass a worker.

## Target and Redirect Controls

Every browser run uses a fixed egress proxy, including loopback traffic. The sample policy permits only HTTP to literal `127.0.0.1:8000`. Navigation, redirects, and resources cannot fall back to direct connections. POST and upgrades are rejected; service workers and WebSockets are disabled.

The separate public guard checks exact host allowlists, schemes, ports, and every DNS address. DNS has a five-second subprocess deadline. Connections use validated numeric IPs without resolving the hostname again; actual peers are checked. Public mode rejects private, loopback, link-local, reserved, multicast, and IPv6 transition destinations.

HTTP redirects are checked before forwarding. Subsequent HTTP(S) connections are independently authorized. Request and redirect budgets are bounded.

The CLI remains sample-only. Public connection helpers are unit-tested offline. Live arbitrary-site browsing and production firewall/container isolation are not enabled. A proxy is not an OS sandbox. TLS tunnels are not decrypted; production method enforcement also needs browser and infrastructure controls.

## Results and Evidence

Generated files are ignored by Git:

- `artifacts/results/`: JSON snapshots, with job IDs for worker runs.
- `artifacts/screenshots/`: complete PNG evidence.
- `artifacts/smoke/report.json`: per-case run summary.
- `artifacts/security/report.json`: egress regression summary.

Missing images are not linked; screenshot errors do not replace test outcomes. Persistence failures are never reported as saved. Recovery updates queue records without rewriting historical JSON snapshots; zero duration indicates unknown timing if no duration was recorded.

Secrets are environment references with masked standard output. Never log direct values or send them to AI providers. Production secret storage, evidence access control, and retention remain planned.

## Platform Acceptance

CI now runs real process lifecycle checks on Ubuntu 24.04 and Windows 2025.
Reports are uploaded as process-lifecycle-ubuntu-24.04 and process-lifecycle-windows-2025.
Linux termination also discovers detached descendants through /proc and checks
process start identities before signaling them. The Linux path has offline unit
coverage; its real execution passed in the Linux CI job.

See the [Sprint 1 acceptance review](docs/SPRINT_1_ACCEPTANCE.md) for the evidence
map and exact closure checklist. Sprint 1 acceptance is complete for the documented local prototype.

## Sprint 1 Completion Evidence

[Verified CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39465390109):
all four jobs passed, including 175 unit tests, three process lifecycle checks on
each OS, nine browser security checks, and ten queued smoke cases.
All three downloaded artifact digests were verified; ten JSON records matched
the smoke summary and their ten linked PNGs. A sample screenshot was visually inspected.

Sprint 2 implementation passed [all four CI jobs](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39496255283)
for commit `8bca37ca4852208d8a6efcaf11558693c79450b0`. Evidence includes 243 unit
tests, five bounded discovery scenarios, four contrasting sites, and the retained
security/smoke/lifecycle regressions. Three downloaded archive digests, fixture
hashes and feature/decision matrices, and ten JSON/PNG pairs were verified.
See the [Sprint 2 acceptance review](docs/SPRINT_2_ACCEPTANCE.md). Production
deployment and arbitrary-site execution remain outside this completed prototype.

## Sprint 2 Discovery Foundation

[Progress](docs/SPRINT_2.md) and [tracking issue #3](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/3).
Immutable snapshots describe fields, forms, and links without capturing input values.
Initial rules detect login, search, registration, product, and cart evidence using
visible controls, semantic regions, and English/Turkish action names.
Findings include present/absent/unknown states, reasons, and page-scoped evidence.
A link or partial form is a hint, not proof. Missing evidence on an incomplete page
stays unknown. Even a complete page cannot establish site-wide absence.

The collector reads visible native controls from an already guarded browser page,
without reading input values or following links. URL queries and fragments are
removed. Collection limits and unsupported structures preserve uncertainty.
Real Chromium checks cover the guarded sample and contrasting offline documents.
The local crawler applies page, depth, request, and total process deadlines with
explicit coverage limitations. General customer URLs remain disabled. Commerce
rules are conservative and do not execute registration or cart mutations.
Aggregation preserves discovery uncertainty and inspected-page scope. Generated
plans select applicable UI definitions, skip cases lacking evidence within that
scope, and block uncertain prerequisites or unsupported configurations. Each
decision has a reason; selected cases reference their target page and evidence.
Plans do not execute tests or authorize execution. Contrasting-site acceptance
checks and remote verification are complete. Issue #3 is closed; milestone #3
was closed by the repository owner.

## Sprint 3

[Sprint 3](docs/SPRINT_3.md) and [issue #4](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/4)
track deterministic role/label/alternative-name matching, project mappings,
reusable executors, independent test data, and expansion toward 40 meaningful
runnable UI scenarios. Validated mappings and deterministic browser matching are
implemented. Existing login/search checks pass across three controlled fixture
variants in isolated processes, including explicit project overrides. The catalog
now has 40 distinct scenarios; 32 shared executors also pass 96 runs across three fixture variants. Variants do not inflate the case count. All 40 cases also pass in reversed order;
browser-local fake data is prepared and cleaned explicitly, including on failure.

[Accepted CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39519899466)
for `eb95e96696d148133747ee4f290cb727f9fc4bb1` passed all four jobs: 268 unit tests,
18 matching checks, 96 shared-variant runs, 40 reversed runs, 40 queued runs,
and discovery/security/lifecycle regressions. Three archive digests, all result
records, and 176 PNG references were verified. A pre-cleanup form screenshot was
visually inspected. See [acceptance evidence](docs/SPRINT_3_ACCEPTANCE.md).
Issue #4 is closed; milestone #4 was closed by the owner. The Sprint 3
hourly follow-up is paused after acceptance.



## Sprint 4

[Plan](docs/SPRINT_4.md) and [issue #5](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/5)
track configured API transport, authentication references, structured assertions,
explicit UI/API bindings, and controlled positive/negative coverage. Customer API
execution remains disabled. The controlled adapter has 20 API cases, environment
secret references, typed assertions, hard process deadlines/cancellation, and
20 hostile-response/policy boundary checks. Four UI/API validation controls keep
each layer's outcomes independent.

[Accepted CI run](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/actions/runs/39559291036)
for `5db716ced9576e878611e5579a3ebe0f64ddb873` passed five jobs with 307 unit tests
and retained UI/discovery/security/lifecycle coverage. Four artifact digests,
60 case results, boundary/bridge reports, and 177 PNG references were verified.
See [acceptance review](docs/SPRINT_4_ACCEPTANCE.md). Issue #5 is closed; the
[Sprint 4 milestone #5](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/milestone/5)
is associated with issue #5 and was closed by the owner. Sprint tracking is complete.
