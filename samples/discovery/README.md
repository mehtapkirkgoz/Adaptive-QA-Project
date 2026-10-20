# Controlled Discovery Fixtures

These local HTML fixtures verify discovery and planning, not visual product design.
No form or commerce action should be submitted during discovery.

| Fixture | Login | Search | Registration | Product | Cart |
| --- | --- | --- | --- | --- | --- |
| plain | absent | absent | absent | absent | absent |
| account | present | present | present | absent | absent |
| store | unknown | absent | present | present | present |
| ambiguous | unknown | unknown | unknown | unknown | unknown |

Statuses refer only to inspected pages. The store registration password is a weak
login hint, so login stays unknown. The four-page store verifies page bindings for
registration/product/cart. All fixtures use the same authorized loopback target,
served one fixture directory at a time; customer URLs remain disabled.

Run from the repository root with port 8000 available:

```powershell
python scripts/check_discovery_acceptance.py
```

The script verifies feature states, case decisions, target-page evidence, discovery
limits, and read-only origin traffic. It writes a controlled-fixture acceptance
report under `artifacts/discovery/acceptance.json`.
