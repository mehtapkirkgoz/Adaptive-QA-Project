# Licensed Single-Device Startup

This local command path reuses the existing engine and free workspace. No remote
account, license server or payment service is activated. A real publisher public
key and matching signed customer license must be supplied separately; the repo
contains neither production trust keys nor issuer private keys. Tests use ephemeral
keys only. Do not put private signing keys in a customer workspace or source control.

## Prepare and Upgrade

Build the real interface with `npm ci` and `npm run build` in frontend/. Stop the
free workspace server and its workers before switching that workspace to licensed
mode. Keep a backup of the workspace, including projects.sqlite, auth.sqlite (once
created) and license.sqlite. Existing project IDs, results and evidence are retained.
Do not run the development dashboard worker commands against a licensed workspace:
the customer worker commands below explicitly select the licensed project store.
The owner-controlled development compatibility entry points are not commercial
packaging or tamper-proof local enforcement.

The publisher supplies a separate JSON public-key map with one to ten key IDs and
64-character hexadecimal Ed25519 public keys. Imported licenses cannot add trust
keys. Changing issuer trust is a deliberate local distribution/configuration task.
Offline clock rollback and immediate remote revocation are not prevented.

From the repository root, provision a local administrator interactively. Passwords
are entered without echo and are not passed in command arguments:

```powershell
python -m adaptive_qa local create-admin --workspace artifacts/local-free
```

Import the publisher-issued signed license and inspect its validity:

```powershell
python -m adaptive_qa local license-import --workspace artifacts/local-free --trusted-keys C:/QA/publisher-public-keys.json --license-file C:/QA/customer-license.json
python -m adaptive_qa local license-status --workspace artifacts/local-free --trusted-keys C:/QA/publisher-public-keys.json
```

The paths above are examples, not files included in the project. Status prints
validity, expiry and capacity only; it does not print customer IDs or test records.
An invalid replacement leaves the previous stored license intact. Status reports
invalid_or_expired without granting execution; existing records are not erased.

## Run the Local Application

Use the email provisioned by create-admin:

```powershell
python -m adaptive_qa local serve --workspace artifacts/local-free --trusted-keys C:/QA/publisher-public-keys.json --administrator owner@example.test --port 8767
```

The dashboard binds only to 127.0.0.1, requires password authentication and retains
Host/Origin/CSRF protections. Only the designated administrator maps to the existing
single-device workspace. An expired or absent license still permits authenticated
local reads, but prevents licensed project creation and execution admission.

Process one queued item with the corresponding licensed worker command in another
terminal. Both commands share the same signed concurrent execution capacity:

```powershell
python -m adaptive_qa local discovery-once --workspace artifacts/local-free --trusted-keys C:/QA/publisher-public-keys.json
python -m adaptive_qa local run-once --workspace artifacts/local-free --trusted-keys C:/QA/publisher-public-keys.json
```

These are bounded one-shot workers, not an installed background service. No work is
executed by license import/status or a dashboard page load. Queued work waits while
the license is absent/expired or capacity is occupied. Existing deadlines and
cancellation continue to govern active child processes. Targets, credentials,
results and screenshots stay local. The licensed dashboard also supports signed-document import and status after
password login. Packaged customer startup/backup/rollback verification remains
unfinished.
