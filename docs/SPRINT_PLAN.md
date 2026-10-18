# Sprint Plan

## Planning Approach

Sprint duration is estimated according to scope and capacity.
There is no fixed two-week commitment.
Each sprint is completed when its acceptance criteria are verified.

The first technical demonstration is targeted for Sprint 1,
the integrated MVP for Sprint 7, and the pilot candidate for Sprint 9.
These are scope targets, not delivery date commitments.

Each test case must have a unique identifier, prerequisites, steps,
expected results, and a risk level.

Test counts represent coverage goals. They do not replace acceptance
criteria and must not be inflated by counting minor variations
as independent scenarios.

## Sprint 0 — Architecture and GitHub Workflow

Scope:

- Define component boundaries and record technology decisions.
- Establish the GitHub Project, milestones, issue templates, and PR template.
- Create the Python package scaffold and initial CI workflow.
- Define test case and execution result models.
- Define project configuration and secret reference contracts.
- Document target authorization and data-changing test policies.

Acceptance criteria:

- The package installs successfully in a clean environment.
- The status command runs successfully.
- Model and configuration validation tests pass.
- GitHub Actions completes successfully.
- Architecture and development documentation are available.
- Sprint tracking is configured in GitHub.

## Sprint 1 — First End-to-End Test Execution

Scope:

- Accept a target URL and project configuration through an initial CLI or API.
- Implement destination controls before enabling network execution.
- Introduce Playwright and a browser worker.
- Introduce a job queue, execution timeout, cancellation, and resource cleanup.
- Implement 10 smoke test cases against a controlled sample application.
- Persist execution results and generate test evidence.

Acceptance criteria:

- A test run can be started and its results retrieved.
- Unauthorized destinations are rejected.
- Redirects and outgoing requests are subject to destination policy.
- Cancellation and timeout release browser resources.
- Ten smoke test cases are verified against the sample application.
- Execution failures are distinguished from assertion failures.

## Sprint 2 — Website Discovery and Feature Detection

Scope:

- Discover pages within configured depth and request limits.
- Collect links, forms, accessible roles, and field labels.
- Detect login, registration, search, product, and cart features.
- Distinguish present, absent, and unknown feature states.
- Generate applicable test plans from discovered features.

Acceptance criteria:

- Sample applications with different features produce appropriate plans.
- Missing and uncertain features are reported separately.
- Skipped tests include explicit reasons.
- Discovery respects page, depth, timeout, and request budgets.

## Sprint 3 — UI Test Catalog and Element Matching

Scope:

- Expand the catalog to approximately 40 test cases.
- Cover login, forms, search, and navigation.
- Match elements using roles, labels, and alternative names.
- Support project-specific element mappings.
- Introduce test data preparation and cleanup.
- Include negative scenarios and independent test execution.

Acceptance criteria:

- Shared tests work against sample pages with different element names.
- Ambiguous element matches produce controlled outcomes.
- Tests do not depend on execution order.
- Data-changing tests respect project policy.
- Repeated runs produce explainable results.

## Sprint 4 — API Testing

Scope:

- Configure endpoints or API contracts supplied by the customer.
- Support authentication, status code, response schema, and business rule checks.
- Connect selected UI scenarios to API validations.
- Mask tokens and apply operation limits.
- Expand the catalog to approximately 60 test cases.

Acceptance criteria:

- Positive and negative API scenarios run against a controlled API.
- Missing API configuration produces an explicit non-execution reason.
- Secrets do not appear in logs or reports.
- API operations respect target and data modification policies.

## Sprint 5 — Database Validation

Scope:

- Implement an adapter for the first supported database type.
- Use parameterized queries and query timeouts.
- Limit result sizes and default to read-only permissions.
- Validate records created through UI or API operations.
- Support project-specific query templates.
- Expand the catalog to approximately 75 test cases.

Acceptance criteria:

- A sample scenario validates behavior across UI, API, and database layers.
- Connection errors are distinguished from assertion failures.
- Unauthorized write operations are rejected.
- Database credentials are resolved through secret references.

## Sprint 6 — AI Integration

Scope:

- Introduce a provider-independent AI adapter.
- Validate structured model responses.
- Assist feature classification, test selection, and element identification.
- Define confidence thresholds and fallback behavior.
- Apply request, time, and cost budgets.
- Reduce sensitive data before sending model requests.
- Treat website content as untrusted input.
- Build an evaluation set from controlled sample applications.

Acceptance criteria:

- Feature detection and element selection accuracy are measured.
- Incorrect decisions are recorded and reviewable.
- Invalid responses and provider outages are handled predictably.
- Core execution remains available without AI.
- AI cannot change authorization policies or test success criteria.

## Sprint 7 — Web Dashboard and Project Management

Scope:

- Implement authentication and project management.
- Configure targets, test accounts, API access, and database references.
- Provide test plan review, run start, cancellation, and progress views.
- Display run history and masked configuration values.
- Enforce user and project ownership checks.

Acceptance criteria:

- A user completes an end-to-end run through the dashboard.
- Users cannot access another user's projects, secrets, or evidence.
- Run progress and final results are visible.
- The integrated MVP is demonstrated.

## Sprint 8 — Reporting and Test Catalog Expansion

Scope:

- Provide filterable results, screenshots, and failure evidence.
- Support report export, reruns, and historical comparisons.
- Track flaky tests.
- Reach at least 100 meaningful test cases.
- Define evidence retention and access policies.
- Plan expansion toward 200 cases using pilot findings.

Acceptance criteria:

- At least 100 defined cases are verified in suitable sample environments.
- Reports agree with actual assertions and evidence.
- Total catalog size and applicable test counts are shown separately.
- Evidence access and retention rules are enforced.

## Sprint 9 — Custom Domain and Deployment

Scope:

- Separate staging and production environments.
- Package services for deployment and establish controlled CI/CD.
- Configure domain, DNS, HTTPS, and environment secrets.
- Define database migrations and rollback procedures.
- Isolate workers and enforce network and resource limits.
- Add monitoring, logs, backups, and an operations guide.

Acceptance criteria:

- An end-to-end run succeeds in staging.
- Rollback and backup restoration are demonstrated.
- The dashboard is accessible through HTTPS on the configured domain.
- Production deployment has a concrete release and rollout plan.
- Operational limitations are documented.

Domain purchases and paid service selections are performed
by the repository owner.

## Sprint 10 — Customer Management and Pilot Testing

Scope:

- Introduce organizations, roles, quotas, and usage tracking.
- Strengthen customer isolation and concurrent execution controls.
- Pilot a customer-hosted agent for private network access.
- Define an authenticated outbound connection model for the agent.
- Collect pilot feedback and prepare user and support documentation.

Acceptance criteria:

- Isolation and quotas are verified using at least two sample organizations.
- Private network execution is demonstrated through the agent.
- Pilot findings are recorded in a prioritized backlog.
- Customer onboarding and support procedures are documented.

## Separate Product Decisions

Billing, subscription management, comprehensive load testing,
and automated security scanning require separate scope decisions.

They are not included in the initial goal of 100–200 functional test cases.