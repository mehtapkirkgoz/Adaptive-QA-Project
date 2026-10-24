# Single-Device Local Quick Start

Use this path for the account-free edition. The public GitHub Pages site is an
interface demo; it cannot connect to your local worker or run tests. The older
`dashboard serve` command is an authenticated development compatibility mode,
not the account-free startup command below.

## Prepare the Application

From the repository root, install Python dependencies and Chromium using
[SETUP.md](SETUP.md). Build the real dashboard with Node.js 24:

```powershell
cd frontend
npm ci
npm run build
cd ..
```

The commands below use the repository's Python environment directly; activation
and PowerShell execution-policy changes are unnecessary. Keep an existing
workspace/server running if you are only reading this guide. Choose a different
unused port and workspace for a separate session.

## Open the Free Workspace

In one terminal, start the loopback dashboard:

```powershell
.\.venv\Scripts\python.exe -m adaptive_qa dashboard free-serve --database artifacts/local-free/projects.sqlite --port 8766
```

Open `http://127.0.0.1:8766/`. Use the numeric address, not `localhost`. No account
or API key is required. Create one project, open its configuration, enter a target
URL and list explicitly allowed host names, then save. Saving does not start a
test. The free edition allows one active project; changing its saved target is
permitted. It is not a lifetime single-domain or tamper-proof offline limit.

For an authorized public HTTPS target, use port 443 and inspect the **Execution
support** message after saving. These checks are read-only: they do not sign in,
fill forms or submit searches. A saved unsupported target does not become runnable.
Do not assume that all 100 catalog definitions apply to the target.

## Discover, Select and Run

1. In the dashboard, choose **Queue HTTPS discovery** for a supported HTTPS target,
   or **Queue local discovery** for the controlled local fixture.
2. In a second terminal at the same repository root, process the workspace queue:

   ```powershell
   .\.venv\Scripts\python.exe -m adaptive_qa dashboard free-worker-cycle --database artifacts/local-free/projects.sqlite
   ```

3. Return to the dashboard and choose **Review discovery plan**. Inspect supported
   cases and select the tests you want, then choose **Start selected tests**.
4. Run the same worker command again. Read the resulting statuses and available
   evidence in the dashboard.

The cycle attempts one discovery job, one read-only run and one explicitly
confirmed interactive job, then exits. It is not a background service. The
dashboard may show queued work until a worker for the same database is run.
Reviewing a plan does not execute it. After target or binding changes, perform
fresh discovery and review rather than reusing an old plan.

## Explicit API and Database Jobs

API and database jobs use separate saved contracts, review and confirmation
panels. The current reusable profiles are restricted to owned controlled fixtures
at `http://127.0.0.1:8000/`; entering another API URL or a production database path
does not authorize execution. See [API support](LOCAL_API_EXECUTION.md) and
[database support](LOCAL_DATABASE_EXECUTION.md).

After separately reviewing and explicitly queuing one supported job, run its
corresponding command:

```powershell
.\.venv\Scripts\python.exe -m adaptive_qa dashboard free-api-once --database artifacts/local-free/projects.sqlite
.\.venv\Scripts\python.exe -m adaptive_qa dashboard free-database-once --database artifacts/local-free/projects.sqlite
```

Run only the command for the job you queued. The three-queue worker cycle does
not process these two queues. Database counts additionally require an owned
SQLite fixture in the fixed workspace `database-fixtures/<project-id>` directory
and its scoped environment reference set in the worker terminal. The panel shows
the reference name; never enter its resolved path or secret value in a report.
No arbitrary SQL, row values or general customer database connector is exposed.

## Results, Cancellation and Recovery

Targets, settings, results and evidence stay in the selected local workspace;
secret values remain in the local worker environment. Closing a browser does not
erase saved data. Protect the workspace with operating-system permissions.
Use a job's cancel control if necessary. Cancellation may remain pending while
the worker stops its isolated child; never infer success from an interrupted
terminal, and do not automatically retry an uncertain run.

Follow [offline backup and recovery](LOCAL_LICENSED_SETUP.md#complete-offline-workspace-backup)
with the workspace stopped. Restore to a fresh directory; do not overwrite a live
workspace. Backups do not include target fixture databases, environment values or
publisher trust files. Restore those separately only when needed and authorized.

For multiple projects and password-authenticated local administration, follow
[licensed setup](LOCAL_LICENSED_SETUP.md) using a separately issued signed license
and publisher public keys. No production license or issuer private key ships in
this repository. Paid licensing does not remove execution or concurrency guards.
