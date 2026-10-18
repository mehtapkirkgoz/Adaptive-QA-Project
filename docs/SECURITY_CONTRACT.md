# Target Authorization and Secret Management Contract

Status: Initial contract — partially implemented.

## 1. Authorized Targets

Each project must explicitly define its allowed hostnames.

Implemented:

- Only HTTP and HTTPS target URLs are accepted.
- The base URL must match an explicitly allowed hostname.
- Hostname matching is case-insensitive for incoming URLs.
- Subdomains require separate authorization.
- Wildcards are not supported.
- Credentials embedded in URLs are rejected.

Current authorization matches hostnames only. It does not restrict
schemes or ports beyond URL validation.

Required before network execution is enabled:

- Validate every navigation, redirect, and outgoing request.
- Restrict destination ports according to project policy.
- Validate resolved IPv4 and IPv6 addresses.
- Block unauthorized private, loopback, link-local, and reserved addresses.
- Prevent DNS changes from bypassing destination restrictions.
- Enforce network restrictions at the worker infrastructure level.
- Apply explicit policies for customer-hosted agents on private networks.

Hostname matching alone is not sufficient to prevent server-side
request forgery (SSRF).

## 2. Data-Changing Tests

Implemented:

- Project configuration defaults allow_data_changes to false.
- Test definitions declare changes_data.

Required before test execution:

- Reject data-changing tests when project policy disables them.
- Record the reason as a blocked result.
- Require approved test accounts and test data.
- Define cleanup procedures for created or modified records.

The configuration flag does not currently enforce execution behavior.
Tests are responsible for declaring their side effects accurately.

## 3. Secret References

Implemented:

- Secrets are referenced by environment variable name.
- Values are resolved from the current process environment.
- Missing and blank values are rejected.
- Secret values are excluded from standard repr output.
- Standard string output displays [REDACTED].

Current limitations:

- Direct access through the value attribute exposes the secret.
- Serialization is not automatically redacted.
- Environment variables do not provide customer-level isolation.

Required for integrated execution and production use:

- Never log secret values or include them in reports.
- Sanitize request headers, URLs, errors, screenshots, and other evidence.
- Never send secrets to an AI provider.
- Authorize secret access by organization, project, and worker job.
- Use a dedicated production secret provider.
- Support secret rotation and access auditing.

## 4. AI Boundaries

Required when AI integration is introduced:

- Treat website content as untrusted data.
- Ignore instructions embedded in pages or retrieved content.
- Validate model responses before using them.
- Keep target permissions and execution policies outside model control.
- Do not allow AI to modify test success criteria.
- Apply explicit request, time, and cost budgets.

## 5. Implementation Gate

Network test execution must remain disabled until the relevant
destination controls are implemented and verified.

This document describes implementation requirements. It does not claim
that pending controls already exist.