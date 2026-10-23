# Controlled Interactive Form Contracts

This is a non-executing foundation, prepared while local-first remote acceptance
is pending. No worker, UI admission, new catalog scenario or external form
submission is enabled by this increment. Existing LOGIN-001/SEARCH-001 structural
checks still do not fill fields or submit forms. The 100-case catalog is unchanged.

## Fixed Input and Assertion Contract

A frozen InteractiveFormContract binds one project and the exact saved-configuration
fingerprint to a typed login or search operation. Login takes two distinct typed
environment references (username/password); search takes one query reference.
Plaintext input values, unbounded reference names and arbitrary operation strings
are rejected. Construction, validation and fingerprinting never resolve a secret
or contact a target. Future project admission must additionally authenticate the
owner and verify scoped reference names; this model does not grant that authority.

The contract pins an explicit completion mapping: login.accepted/login.rejected or
search.results/search.empty. Changing the completion mapping, input references or
configuration changes its digest. A future worker must prove the completion marker
was absent before one permitted submission and visible afterward; an already
visible marker cannot establish a successful transition. This assertion requirement
is included in the digest but is not implemented as execution in this increment.
AI must not replace a failing assertion or choose a different expected result.

Both operations require explicit project data-change permission, including search:
a form can create sessions, audit records or other side effects. There is one
submission maximum and a bounded five-to-thirty-second operation timeout. These
limits supplement the existing outer process deadline; retries must not repeat a
submission. A changed project/configuration blocks the contract. Project host
allowlisting alone is not enough to authorize a form submission.

## Next Execution Work

After local-first CI/artifact acceptance, add a separately supervised controlled
fixture worker. Before resolving input references it must validate current licensed
admission, exact saved target/profile, form ownership and unique enabled controls,
form action/method and destination/IP guards. Initial proof stays on contrasting
owned loopback fixtures. Customer/public-site credential submission is not enabled.

Input values must remain out of argv, saved configurations, JSON reports and
screenshots. Evidence capture requires an explicit masking/redaction strategy;
structural screenshot code must not be reused blindly after filling a password or
query. Child output is bounded and sanitized; cancellation/deadline/ambiguity must
stop execution. Only after positive/negative, no-retry, wrong-destination,
credential-canary and cleanup checks pass should a separate admission/UI integration
be considered. Keep existing plans non-executing and do not mark catalog entries
executable until their workers and acceptance evidence exist.

## Controlled DOM Probe Increment

An internal probe now exercises client-side form transitions on controlled local
URLs using a caller-owned fresh context that denies all other network traffic.
This is not a supervised child worker or dashboard admission. Its runner fulfills
the initial document from an in-memory fixture and aborts every other request; no
real login endpoint or external site receives inputs. No screenshot/trace is taken.

The probe validates project/configuration/data-change permission, unique connected
controls, field types, effective form/button action/method/target and an absent
completion marker before resolving environment references. It checks the action
and marker again after filling to catch input handlers that mutate them. It
attempts one click and requires the pinned marker afterward. Results use fixed
sanitized messages rather than Playwright exception text. The caller must dispose
the context, retain a network-denial signal and eventually provide hard process
supervision before this can become an executable product scenario.

Sixteen real Chromium scenarios passed: accepted/rejected login, Turkish names,
results/empty search, pre-existing or input-triggered markers, wrong form/button
action, POST method, ambiguous submit, unmasked/missing password, absent transition,
input-mutated action and a denied credential-canary request. Blocked preconditions
resolve no references; no scenario submits more than once. A missing transition
fails and a network attempt returns error. Four contract tests also passed.
The meaningful 100-case catalog and all external execution permissions are unchanged.
Next: supervised child transport/deadline/cancellation and contrasting owned HTTP
fixtures, then explicit licensed admission/UI integration.
