# Empty-root URL compatibility

Concrete owner finding: submitting https://promptgena.com produced discovery
bindings for https://promptgena.com/. Five applicable document checks were selected
by planning but rejected by literal saved-URL binding, leaving no automatic tests.
This mismatch was verified from the preserved local discovery report, without
repeating target requests or inventing historical test verdicts.

HTTP(S) empty root paths are now represented internally as /. Saved owner strings
remain unchanged. Discovery configuration, serialized document/form bindings and
the isolated document child use this same representation. Non-root paths, hosts,
ports, encodings, queries and fragments are not equated. No redirect following,
DNS/IP exception, TLS bypass, resource activation or write authority is added.

Unit tests cover both saved root spellings, exact path/host/port rejection and
managed selection of the five DOC checks. An owned real-child browser proof loads
a bare controlled root successfully while retaining existing redirect, script,
asset, iframe, native-form and no-mutation boundaries. Installed release acceptance
requires the same empty_root_url_passed proof.

Pending: full regression, exact-commit CI/archive acceptance and installed preview
upgrade. Only after acceptance, one bounded read-only automatic check may verify
the specific authorized owner target. Preserve all old no-test/error rows; new
results must be recorded as a new run rather than rewriting history.
