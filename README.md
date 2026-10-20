# Adaptive-QA-Project

An AI-powered QA platform that discovers web application features and runs applicable UI, API, and database tests.

**Status:** Sprint 1 in progress. Sprint 0 established the project
foundation. Sprint 1 currently provides three local browser scenarios,
JSON result persistence, and linked screenshot evidence. Queueing and broader
network execution remain under development.

## Product Overview

Users create a project through a web dashboard, provide a target URL and test configuration, review the test plan, and start a test run.

Background workers execute tests independently of web requests. Users access results, screenshots, and run history through the dashboard.

The platform will be accessible through a custom domain. A customer-hosted agent is planned for testing applications inside private networks.

## Planned Components

- Web dashboard and application API.
- Job queue and isolated test workers.
- UI, API, and database testing adapters.
- Provider-independent AI integration for feature discovery, test selection, and element identification.
- Project configuration, secure secret management, reporting, and evidence storage.

Technology decisions are documented in the [architecture record](docs/ARCHITECTURE.md).

## Sprint Tracking

Sprints are organized around defined goals and acceptance criteria.
Duration is estimated according to scope and capacity.
A sprint is completed only when its acceptance criteria are verified.

| Sprint | Goal | Status | Delivered |
|---|---|---|---|
| 0 | Architecture and GitHub workflow | Completed | Python scaffold, architecture record, CI configuration, issue and PR templates, validated test case model, eight passing unit tests |
| 1 | First end-to-end test execution | In progress | Local login form check, JSON results, linked screenshots |
| 2 | Website discovery and feature detection | Planned | — |
| 3 | UI test catalog and element matching | Planned | — |
| 4 | API testing | Planned | — |
| 5 | Database validation | Planned | — |
| 6 | AI integration | Planned | — |
| 7 | Web dashboard and project management | Planned | — |
| 8 | Reporting and test catalog expansion | Planned | — |
| 9 | Custom domain and deployment | Planned | — |
| 10 | Customer management and pilot testing | Planned | — |

Each sprint will record completed work and relevant pull request or release links.

See the [sprint plan](docs/SPRINT_PLAN.md), [GitHub workflow](docs/GITHUB_WORKFLOW.md), and [Sprint 0 progress](docs/SPRINT_0.md) for details.

## Quality Principles

- An undetected feature is distinguished from a confirmed absent feature.
- Test outcomes distinguish passed, failed, skipped, blocked, and execution errors.
- Success criteria are explicitly defined. AI cannot change them to make a failing test pass.
- Tests run only against authorized targets. Data-changing operations are controlled by project policies.
- Credentials, tokens, and connection secrets must not appear in source code or reports.

## Development Setup

Follow the [setup guide](docs/SETUP.md) to create a virtual environment and install the project.

Check the implementation status:

```powershell
python -m adaptive_qa --status
```

This command displays the scaffold status. It does not execute website tests.

## Test Case Models and Validation

Implemented models include:

- Test types: UI, API, and database.
- Execution statuses: passed, failed, skipped, blocked, cancelled, and error.
- Feature discovery statuses: present, absent, and unknown.
- An immutable test case definition with input validation.
- An immutable execution result model with status, duration, and message validation.
- A reusable login form test definition.

One hundred and fifty-four unit tests cover models, configuration, secrets, destination
policies, result classification, and persistence. These are platform unit tests,
not 78 website test scenarios.

Run the tests locally:

```powershell
python -m unittest discover -s tests -v
```

Local verification: **154 tests passed**. The local browser scenario was also
executed successfully, and its saved JSON references an existing PNG screenshot.

GitHub Actions: Sprint 0 verification passed with 38 tests.
The current changes require verification after the next push.

## Project Configuration and Secrets

Project configuration defines the target URL, explicitly allowed
hostnames, and whether data-changing tests are permitted.

Hostname authorization uses exact matching. Subdomains require explicit
permission. This check is not a complete network security boundary:
DNS and public IP validation helpers are implemented. Connection-level
restrictions and complete redirect enforcement remain pending before general
network execution is enabled. The current browser flow is for the controlled
local sample only.

Secrets are referenced by environment variable name and resolved at
runtime. Standard string and repr output hide resolved values.
Direct value access and serialization must never be logged.

Environment variables are the initial development mechanism.
Production secret storage will require a dedicated provider.

Project configuration and secret references are currently standalone
components. They are not yet connected to a test runner.

See the [target authorization and secret management contract](docs/SECURITY_CONTRACT.md)
for implemented controls, current limitations, and execution prerequisites.

Sprint 1 implementation progress is tracked in [Sprint 1](docs/SPRINT_1.md).
## Local Browser Evidence

Run the sample server and browser check in separate terminals from the repository root:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory samples/web
```

```powershell
python -m adaptive_qa.local_browser
```

Results are written to `artifacts/results/`. The `result.evidence_paths` array
references screenshots that exist at result creation time. Paths are relative
to the repository root for this local workflow. Older records without this
optional field remain unchanged. Generated evidence is ignored by Git.

Screenshots are captured after successful checks and, when the page is available,
after assertion or execution failures. Screenshot errors do not replace the test
outcome. Only complete PNG files are published; missing evidence is not linked.
Failures before page creation cannot produce a screenshot. Evidence retention
and report access controls remain pending.

## Automated Local Browser Check

With port 8000 available, run:

```powershell
python scripts/check_local_browser.py
```

The script starts the sample server, runs the browser check in a child process,
and stops the server afterward. It returns a nonzero exit code on failure or
a 60-second browser command timeout. It refuses to reuse an existing server.

GitHub Actions has separate unit and browser jobs. The browser job installs
Chromium and its Linux system dependencies, runs the same script, and uploads
JSON results and PNG screenshots as `local-browser-evidence` for seven days.
Artifact upload is attempted even if the browser check fails. No screenshot
is available if the browser fails before a page can be captured.

Local verification passed. The new Linux CI job still requires verification
after push. This runner is a development check, not the queued production worker.

Browser lifecycle unit tests verify cleanup after success, context creation
failure, page creation failure, and a simulated navigation timeout. These tests
verify exception handling; they do not demonstrate forced termination of a
hung browser process or cancellation of a queued worker job.

## Local Job Queue Foundation

`LocalJobQueue` supports FIFO submission, atomic claiming, queued-job
cancellation, result attachment, and immutable status snapshots. A completed
job means execution finished; its test result can still be failed or error.
Unknown job identifiers raise `KeyError`.

This is an in-memory, single-process development component. It has no durable
queue state or customer authorization,
and does not stop running jobs. State is lost when the process exits, and
job history remains in memory until then. Redis/Celery dispatch, durable state,
worker recovery remain planned work. Active cancellation is supported by the
SQLite-backed supervisor, not this in-memory component.

## Queued Local Browser Execution

The managed browser check now submits the registered smoke catalog to `SQLiteJobQueue` and invokes
`process_next` through `adaptive_qa.local_worker`. Each saved result includes
its `job_id`. Pending cancelled jobs are skipped. Unsupported cases produce
blocked results; unexpected executor failures produce error results.

A persistence failure returns an error result in memory and no result path;
it is never reported as successfully saved. Job completion still means that
processing finished, not that the test passed or that persistence succeeded.
The CLI returns nonzero for any outcome other than passed.

To run with the sample server already started:

```powershell
python -m adaptive_qa.local_worker submit LOGIN-001
python -m adaptive_qa.local_worker run-next
```

For automatic server management, continue using `python scripts/check_local_browser.py`.
The script and CI now exercise the queued local path. This is synchronous local
execution after claiming, not a persistent background service. The SQLite-backed
supervisor supports active cancellation as described below.

## Durable Local Queue Adapter

`SQLiteJobQueue` provides the same submission, lookup, claiming, queued
cancellation, and completion operations with persisted job state and results.
Transactional claims prevent competing connections from claiming the same job.
Reopening an adapter preserves pending, cancelled, running, and completed jobs.

This adapter is now the CLI default. The in-memory queue remains available
for isolated development and tests.
A running job interrupted by process termination stays running and is not
silently replayed; recovery policy is still pending.

SQLite is an incremental local development adapter, not a replacement for
planned Redis/Celery dispatch and PostgreSQL production storage. It targets a
single machine and does not provide customer isolation or distributed locking.
Do not share a live database through synchronized folders or network storage
between workers on different machines.

## Persistent Worker Commands

Run from the repository root. The default queue is `artifacts/jobs.sqlite3`:

```powershell
python -m adaptive_qa.local_worker submit LOGIN-001
python -m adaptive_qa.local_worker status <job-id>
python -m adaptive_qa.local_worker run-next
python -m adaptive_qa.local_worker status <job-id>
```

Start the sample server separately before `run-next`. Each command opens the same
database, so pending jobs and completed results survive between CLI processes.
`run-next` claims the oldest queued job, not necessarily the most recently submitted
job. It processes one job and exits; it is not a background worker loop.

Cancel a pending job:

```powershell
python -m adaptive_qa.local_worker cancel <job-id>
```

Use `--database <path>` before the subcommand to select a different local database.
Unknown jobs and failed execution return a nonzero exit code. An empty queue is
a successful no-op. Calling the worker without a subcommand displays usage.

The managed CI script uses a fresh temporary queue for each check, submits in
one process, and executes in another. The temporary database is removed afterward;
JSON/PNG evidence remains under `artifacts/`. No live queue database is committed.
Active cancellation is supported by the SQLite-backed supervisor; interrupted-job
automatic recovery remains pending; explicit local recovery is available below.

## Inspecting Persisted Jobs

List jobs without claiming or running them:

```powershell
python -m adaptive_qa.local_worker list
python -m adaptive_qa.local_worker list --status running
python -m adaptive_qa.local_worker list --status cancelled --limit 20 --offset 0
```

Results are JSON arrays ordered by submission. The default limit is 50, the
maximum is 500, and offsets must be non-negative. Status values are queued,
running, cancel_requested, finalizing, completed, and cancelled. Listing running jobs makes unfinished work
visible after restart; it neither proves a worker is dead nor retries the job.
Heartbeat-based automatic recovery remains pending; explicit local recovery is available below.

## Explicit Retry Attempts

Create a new queued attempt for a completed failed or error result:

```powershell
python -m adaptive_qa.local_worker retry <job-id>
```

The original job and result stay unchanged. The new job has a different identifier,
no result, and a persisted `retry_of` reference to the previous attempt. It is
not executed until claimed by `run-next`. Successful, skipped, blocked, queued,
running, and cancelled jobs cannot be retried through this command.

Retries are explicit and are not deduplicated: each command creates a new attempt.
This command does not recover or replay interrupted running jobs. Before retrying
data-changing tests, callers must account for previous side effects; the current
local executor only checks the login form and does not submit credentials.

Existing SQLite queue files gain a nullable `retry_of` column on opening, without
removing existing records. No manual database reset is required.

## Isolated Browser Deadline

The local worker now runs the browser executor in a separate Python process.
Its default total execution limit is 30 seconds, in addition to individual
Playwright operation timeouts. The internal Python API accepts a positive finite
timeout; the CLI currently uses the default.

A timeout terminates the child process tree and returns an error result. Windows
uses taskkill with tree termination; POSIX uses a dedicated process group.
Termination errors propagate to the worker as execution errors. Invalid or missing
child output and abnormal exits are also reported as errors, not passed checks.
The child transports structured results through a temporary JSON file.

Local verification includes a real successful Chromium run and a Windows timeout
check with a parent and descendant process. The POSIX termination path still
requires Linux CI verification. Recovery after an abrupt supervisor crash and
production worker isolation remain pending.
The managed script retains a separate 60-second outer command limit.

## Active Local Cancellation

In a second terminal, using the same database as the running worker:

```powershell
python -m adaptive_qa.local_worker cancel <job-id>
python -m adaptive_qa.local_worker status <job-id>
```

Pending jobs become cancelled immediately. Running jobs become cancel_requested.
The supervisor polls requests between bounded waits (normally every 0.2 seconds,
plus database and process termination time), terminates the child tree, and records
cancelled job/result states. A failed termination remains an execution error;
a request alone never proves the process has stopped.

Before saving the JSON, the worker transactionally moves the job to finalizing.
Cancellation accepted before that boundary is resolved into the saved outcome;
later requests are rejected. Finalization prevents JSON and queue outcomes from
disagreeing due to a late cancellation request. Execution errors are preserved.
If persistence fails, the result has no saved path; cancellation remains explicit.

A process killed mid-execution/finalization may leave running, cancel_requested,
or finalizing records behind. Explicit repair of these states is available through recover-interrupted; automatic recovery remains pending.
Cancelled jobs are not retried automatically, and the retry command rejects them.
Windows active cancellation was verified with a separate CLI requester and a real
parent/descendant process tree. POSIX behavior requires Linux verification.

## Explicit Interrupted-Job Recovery

After an interrupted local worker, inspect and repair the queue:

```powershell
python -m adaptive_qa.local_worker list --status running
python -m adaptive_qa.local_worker recover-interrupted
```

Execution and recovery use the same OS process lock. The supported local CLI now
allows one executor or recovery operation per database at a time. Status, submit,
and cancellation commands remain available during execution. A second run-next
or recovery attempt fails while the worker owns the lock. Lock files remain on
disk; their existence does not mean the OS lock is held. Never delete the lock
file to bypass this check.

Once the supervisor lock is released, recovery transactionally marks running,
cancel_requested, and finalizing records as completed with error results. Pending
and terminal jobs remain unchanged. Repeated recovery is a no-op. No job is
replayed automatically. This protects supported CLI workers, not callers that
bypass the lock and directly manipulate adapter methods.

Recovery repairs SQLite records only. It does not prove orphan browser processes
have stopped or roll back side effects. Review process cleanup and previous
operations before explicitly retrying. Previous JSON files remain historical
snapshots; use status to read the recovered queue result. If no duration was
recorded before interruption, the recovery result uses 0 seconds as unknown.

The OS lock release after abrupt process exit was verified on Windows. POSIX
locking and process cleanup still require Linux verification. Automatic recovery,
production multi-worker coordination, and orphan cleanup remain future work.

## Sample Smoke Catalog — Initial Expansion

Three explicit sample scenarios are now available:

| Case | Behavior |
|---|---|
| LOGIN-001 | Login fields and submit button are visible; password input is masked |
| SEARCH-001 | Search field is visible and its submit button is enabled |
| SEARCH-002 | Submitting a query displays the expected no-results message |

With the sample server running, select a direct browser check:

```powershell
python -m adaptive_qa.local_browser --case SEARCH-002
```

Each check opens a fresh browser context, produces a structured result, saves
JSON through this command, and attempts screenshot capture. Shared page title
and heading assertions remain preconditions. These are controlled sample checks,
not universal executors for arbitrary sites or automatic interpretation of text steps.

The persistent worker and isolated child dispatch all three registered checks
through the same execution path. Direct local_browser
execution uses operation timeouts, not the supervisor's total process deadline.
The 10-scenario Sprint 1 target is not complete.

## Queued Smoke Catalog Execution

With the sample server running, search cases use the same persistent worker:

```powershell
python -m adaptive_qa.local_worker submit SEARCH-001
python -m adaptive_qa.local_worker submit SEARCH-002
python -m adaptive_qa.local_worker run-next
python -m adaptive_qa.local_worker run-next
```

Each job runs in an isolated browser process with a total timeout and cancellation
polling. The child result identifier must match the submitted case. Unknown cases
remain blocked without launching a browser. Login compatibility entry points remain
available for existing callers.

The managed script now submits every catalog case to a fresh temporary queue and
processes each in turn. Ordinary failed checks do not prevent remaining checks
from running; the script returns nonzero if any check failed. Its outer command
timeout still aborts the overall check. Three real scenarios are currently present;
seven more are needed to reach the Sprint 1 smoke target.
