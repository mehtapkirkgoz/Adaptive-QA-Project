# Adaptive-QA-Project

An AI-assisted QA platform under development for website discovery and applicable UI, API, and database tests.

**Status:** Sprint 2 in progress. Sprint 1 completed on October 20, 2026. The local prototype runs 10 smoke scenarios through a persistent queue with cancellation, deadlines, destination controls, JSON results, and screenshots. Offline page feature detection is under development. Live discovery/crawling, AI, API/SQL execution, and the dashboard are not implemented yet.

## Project Plans

Sprints follow goals and acceptance criteria without a fixed two-week commitment.

| Sprint | Goal | Status |
|---|---|---|
| 0 | Architecture, models, configuration, GitHub workflow | Completed |
| 1 | First controlled end-to-end execution | Completed |
| 2 | Website discovery | In progress |
| 3 | UI catalog and element matching | Planned |
| 4 | API tests | Planned |
| 5 | Database validation | Planned |
| 6 | AI integration | Planned |
| 7 | Web dashboard | Planned |
| 8 | Reporting and catalog expansion | Planned |
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

- **189 unit tests passed locally:** platform rules and adapters, not 175 website scenarios.
- **3 real OS lifecycle checks passed on Windows:** deadline, active cancellation, and crash lock release.
- **9 real Chromium security checks passed:** forbidden canaries received no connections.
- **10 queued smoke scenarios passed:** matching JSON results and PNG screenshots.
- Dependency compatibility and compilation checks passed.

Remote verification passed for the implementation commit on Linux and Windows. CI installs Chromium/system dependencies, runs security and smoke checks, and uploads `local-browser-evidence` with seven-day retention.

## Smoke Catalog

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

Sprint 2 started on October 20, 2026; its current changes require remote verification. Production deployment and arbitrary-site execution remain outside this completed prototype.

## Sprint 2 Discovery Foundation

[Progress](docs/SPRINT_2.md) and [tracking issue #3](https://github.com/mehtapkirkgoz/Adaptive-QA-Project/issues/3).
Immutable snapshots describe fields, forms, and links without capturing input values.
Initial rules detect login/search using visible controls and English/Turkish action names.
Findings include present/absent/unknown states, reasons, and page-scoped evidence.
A link or partial form is a hint, not proof. Missing evidence on an incomplete page
stays unknown. Even a complete page cannot establish site-wide absence.

This first checkpoint is offline only. Guarded browser collection, bounded crawling,
additional features, aggregation, and test-plan selection are still pending.
