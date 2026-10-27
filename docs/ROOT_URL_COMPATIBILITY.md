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

Accepted implementation: 5a464290a8a94f19e2760f1776e2b321b05cd1a3 / Core
40448712702. The 938-test regression passed with one existing Windows permission
skip. Twelve successful logical jobs and twelve archives with 226 validated PNGs
were verified. The Windows runtime job passed a targeted retry after an initial
controlled-form precondition failure; the local full installed check also passed
after a numeric-fixture coverage error and a successful targeted/full repeat.
Those initial failures are retained in the acceptance evidence, not relabelled.

The existing preview now runs the verified installed bundle. All thirteen prior
table digests and seven imported reviews were preserved during upgrade. One new
owner-authorized bounded read-only URL check then completed with five passed,
zero failed and zero unevaluated outcomes. All previous rows, including historical
no-test/error records, remained intact. Local target details stay outside source
control. No login, write operation or accepted demo submission was replayed.
See evidence/root-url-ci-5a46429.json and evidence/root-url-preview-5a46429.json.
