# Controlled UI Catalog

The catalog contains 40 distinct definitions and registered sample executors:
ten login cases, eight search cases, sixteen native-form cases, and six navigation
cases. Language and project-mapping variants exercise the same IDs and do not
increase the scenario count. Definitions live in `catalog.py`/`extra_ui_checks.py`.

| IDs | Behaviors |
| --- | --- |
| LOGIN-001–004 | Visible form, required username/password, demo submission |
| LOGIN-005–010 | Username pattern, password length, Enter submission, reset, independent search state, password toggle |
| SEARCH-001–004 | Visible form, no-results message, required query, whitespace prompt |
| SEARCH-005–008 | Enter submission, reset, maximum length, literal markup rendering |
| FORM-001–007 | Email validity, required agreement, checkbox, radio exclusivity, selection, multiline notes |
| FORM-008–013 | Numeric minimum/maximum/step/validity, disabled and read-only editing |
| FORM-014–016 | Restoring defaults, blocked invalid submission, valid submission status |
| NAV-001–006 | Section links, keyboard activation, named targets, retained input, browser history |

Every added definition has concrete prerequisites, steps, and an explicit expected
outcome. Every executor makes browser assertions; unsupported or ambiguous bindings
cannot pass. Native validation checks assert browser validity flags, while action
checks assert the resulting status, field state, fragment, or DOM structure.

These are controlled local sample behaviors, not universal application assertions.
No login server, purchase, or customer data mutation is performed. Submit listeners
update local DOM text only; network writes remain blocked by the route/proxy guard.
Runtime selectors and expected results are never supplied by page text or AI.

The general `forms` feature means visible native form fields exist; `navigation`
means a supported visible link exists. These are prerequisites, not evidence that
every scenario has a compatible binding. The runtime executor still validates its
specific controls and fixed fixture destination before performing actions.

New action scenarios prepare and clear browser-local fake test data explicitly;
screenshots retain the asserted state before cleanup. Cleanup failures are errors.
All scenarios also run in fresh browser processes and pass reverse-order checks.
Backend/customer data provisioning and deletion remain outside this local adapter.
