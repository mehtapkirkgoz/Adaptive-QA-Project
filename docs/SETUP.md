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
with Ctrl+C. The React interface is not implemented yet. Opening
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
