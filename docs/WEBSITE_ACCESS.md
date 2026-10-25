# Website Access and Inspection Diagnostics

Accepted checkpoint (2026-10-26): 1ebed8e / Core 40240530847 completed all twelve
jobs. All twelve downloaded archives matched source identity, size, SHA-256 and
ZIP checks; 222 PNGs validated. Source free/licensed and installed-licensed reports
confirm the DNS explanation, and owned redirect reports confirm same-origin success
and foreign-scope rejection without canary contact. Installed form/browser/queue
evidence remains intact. See [CI evidence](evidence/website-access-ci-1ebed8e.json).

The existing 8766 preview now runs the verified installed 1ebed8e bundle with its
own versioned dashboard. A fresh backup and row digests were taken before restart;
all twelve prior tables matched afterward. The served index/assets were checked,
including the new access explanation. No target work was started or historical
result rewritten. See [local evidence](evidence/website-access-local-1ebed8e.json).

Owner finding, 2026-10-26: ordinary submitted URLs appeared unusable while QA demo
sites worked. The automatic flow has no QA-domain allowlist. It derives exact host
scope from the submitted HTTPS URL and retains public-IP, TLS, request and deadline
guards. A successful demo run does not prove arbitrary-site compatibility.

The supplied promtgena.com address and its www variant returned a DNS-name-not-found
response from this computer's resolver during diagnosis; demoqa.com resolved. This
establishes a local resolution failure at that time, not domain ownership or a global
claim about registration. Historical failed discovery jobs had no saved reason, so
the panel could not explain their failure. Their records remain unchanged.

## Implemented Fix

Public discovery checks its guarded destination in the existing deadline-bound child
before browser startup. DNS resolution failure and blocked public destinations produce
fixed diagnostic codes. Browser navigation failures additionally distinguish certificate,
connection, timeout, refused HTTP access and unsuccessful HTTP responses. Same-origin
redirects remain supported. Out-of-scope redirects remain blocked and the interface
explains how to submit the browser's final HTTPS URL, including www when applicable.
No alias or third-party hostname is silently authorized.

Only allowlisted diagnostic codes cross the child/worker/owned-queue boundaries.
No raw exception text, response body, credential, header or hidden target URL is stored
as a diagnostic. Cancelled work discards the reason. Failed discovery never admits
test execution or creates pass/fail outcomes. Older errors without reasons retain
their generic explanation; the application does not invent historical causes.

## Validation

Books to Scrape explicitly presents itself as a web-scraping demo sandbox. A bounded
read-only run used the general URL flow, without a site-specific binding: five pages
inspected and five independent HTML checks passed. No sign-in/form submission or
owner workspace change occurred. This demonstrates another site structure, not full
business-flow testing or universal customer-site compatibility. See the safe manual
report in [public-catalog-site-2026-10-26.json](evidence/public-catalog-site-2026-10-26.json).

Owned fixtures verify normal relative redirects and rejection of a foreign destination
without canary contact. Free/licensed browser proofs show the DNS explanation without
new admissions on reload; ownership, cancellation and raw-text redaction unit tests
cover failure propagation. Candidate UI builds use a separate output folder and do
not replace the existing owner preview.
The 914-test regression passed with one existing Windows permission skip. The final
diagnostic cancellation test also passed in the focused eleven-test queue suite;
nineteen destination-guard tests and both real redirect scenarios passed.

This scoped finding is technically ready for owner review. The recurring follow-up
stays active and usage-gated for new CI failures or concrete owner findings; remain
quiet on unchanged state instead of repeating accepted checks or expanding scope.
No protected-site bypass, private target exception, automatic sign-in, customer write
test or external backend activation is authorized by this fix.
