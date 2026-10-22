# Developer Setup

Requirements: Git and Python 3.13 or later. The verified local and CI runtime is
Python 3.13. Browser checks require the separate Chromium installation below.
No paid AI key is required for the local prototype.

Run these PowerShell commands from the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m adaptive_qa --status
```

Virtual environment activation is optional when using its Python executable
directly. No PowerShell execution policy change is needed.

Verify source compilation:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src
```

The status command reports implemented local capabilities and does not execute
tests against a website.


Sprint progress and acceptance are tracked in the sprint documents.


## Browser Automation Dependencies

Install the pinned runtime dependencies and project package:

```powershell
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps -e .
```

Install the Chromium browser used by Playwright:

```powershell
python -m playwright install chromium
```

The browser binary is installed separately and must not be committed.

The runtime dependency snapshot was initially verified on Windows
with Python 3.13. Other supported environments require CI verification.

## Local Dashboard Authentication

Create a local account in an interactive terminal:

```powershell
.\.venv\Scripts\python.exe -m adaptive_qa dashboard create-user
```

Enter an email and a password twice. Password input is hidden and must contain
at least 12 characters and at most 256 UTF-8 bytes. There is no default account
or public registration endpoint. Provisioning refuses redirected input; do not
put passwords in command arguments, files, source code, or chat messages.

Start the local authentication API in a separate terminal:

```powershell
.\.venv\Scripts\python.exe -m adaptive_qa dashboard serve
```

The server binds only to `127.0.0.1:8765`, uses one process, ignores forwarded
headers, disables access logging, and bounds concurrent connections. Stop it
with Ctrl+C. After building the React interface below, open `/` to sign in. Opening
`http://127.0.0.1:8765/api/auth/me` returns an authentication error until a session
is established; that is expected. The `localhost` alias is deliberately rejected.

Both commands default to `artifacts/dashboard/auth.sqlite`, an ignored local file
containing password hashes and session digests. Protect this file with your OS
account permissions. An explicit `--database` path can be supplied to either
command; both must use the same path. `serve --port 8766` changes the exact allowed
Host and Origin as well as the listener. Public binding, proxy deployment, and
multi-process mode are not exposed. Cookies lack Secure for this loopback HTTP
prototype; production HTTPS configuration remains future work.

Verify browser authentication without creating a persistent user:

```powershell
.\.venv\Scripts\python.exe scripts/check_web_auth.py
```

This check owns a temporary account/database and loopback server on port 8765.
Stop an existing dashboard server first. It verifies cookies and logout in real
Chromium, cleans up its server and database, and saves a value-free report under
`artifacts/dashboard/auth.json`.

## Build the React Dashboard

Install Node.js 24, then run from the repository root:

```powershell
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe -m adaptive_qa dashboard serve
```

Open `http://127.0.0.1:8765/`. The TypeScript check and Vite build produce ignored
`frontend/dist` assets. Python serves the built index and assets alongside the API.
No CORS exceptions, external CDN or separate development server are needed.
`serve --ui-directory` selects a trusted build. Without a build, `/` returns 404.

The panel supports sign-in/out, paginated projects, create/rename, target/host
settings, data-change policy and masked references. Run controls and reports remain
unfinished. Credentials are not saved in localStorage or other browser storage.

Verify the built interface with no persistent account or server:

```powershell
.\.venv\Scripts\python.exe scripts/check_dashboard_ui.py
```

Keep port 8765 available. The check saves a report and desktop/mobile fixture
screenshots under `artifacts/dashboard/` and cleans up its temporary storage.

## Trusted Discovery Worker

The dashboard dispatch core can now process one queued local discovery job from
a separate terminal process:

```powershell
.\.venv\Scripts\python.exe -m adaptive_qa dashboard discovery-once
```

This command uses `artifacts/dashboard/projects.sqlite` by default, unlike the
account/server commands whose database option selects the authentication database.
Pass `--database` to select a trusted project database. No job is submitted by
this command; an empty queue reports no work. Submit with the panel's Queue local
discovery button, then run this command in a separate terminal. The panel polls
progress, supports cancellation and reviews completed plans. Only the controlled root fixture on `127.0.0.1:8000` is
supported, and the fixture must be running. No customer target is supported.

The worker holds the project database's OS lock across claim, guarded child
discovery and result commit. Discovery has a 30-second process deadline and polls
persisted cancellation requests. Its reduced, non-executing plan report is stored
atomically with completion. Selected definitions do not authorize test execution.

After a worker crash, explicit operator recovery never replays interrupted work:

```powershell
.\.venv\Scripts\python.exe -m adaptive_qa dashboard recover-discovery
```

Recovery refuses an active worker lock. Interrupted running jobs become errors,
pending cancellations become cancelled, and unclaimed queued jobs remain queued.

Verify the separate worker against an owned temporary fixture and database:

```powershell
.\.venv\Scripts\python.exe scripts/check_dashboard_worker.py
```

Keep port 8000 available. The check starts/stops its fixture and worker, persists
the reduced report under `artifacts/dashboard/worker.json`, and removes temporary
storage. It does not run the selected UI cases or contact external sites.
