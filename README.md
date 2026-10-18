# Adaptive-QA-Project

An AI-powered QA platform that discovers web application features and runs applicable UI, API, and database tests.

**Status:** Sprint 0 completed. The project foundation and 38 unit tests
are verified. The test execution engine is planned for Sprint 1.

## Product Overview

Users create a project through a web dashboard, provide a target URL and test configuration, review the test plan, and start a test run.

Background workers execute tests independently of web requests. Users access results, screenshots, and run history through the dashboard.

The platform will be accessible through a custom domain. A customer-hosted agent is planned for testing applications inside private networks.

## Planned Components

- Web dashboard and application API.
- Job queue and isolated test workers.
- UI, API, and database testing adapters.
- Provider-independent AI integration for feature discovery, test selection, and element identification.
- Project configuration, secure secret management, reporting, and evidence storage.

Technology decisions are documented in the [architecture record](docs/ARCHITECTURE.md).

## Sprint Tracking

Sprints are organized around defined goals and acceptance criteria.
Duration is estimated according to scope and capacity.
A sprint is completed only when its acceptance criteria are verified.

| Sprint | Goal | Status | Delivered |
|---|---|---|---|
| 0 | Architecture and GitHub workflow | Completed | Python scaffold, architecture record, CI configuration, issue and PR templates, validated test case model, eight passing unit tests |
| 1 | First end-to-end test execution | Planned | — |
| 2 | Website discovery and feature detection | Planned | — |
| 3 | UI test catalog and element matching | Planned | — |
| 4 | API testing | Planned | — |
| 5 | Database validation | Planned | — |
| 6 | AI integration | Planned | — |
| 7 | Web dashboard and project management | Planned | — |
| 8 | Reporting and test catalog expansion | Planned | — |
| 9 | Custom domain and deployment | Planned | — |
| 10 | Customer management and pilot testing | Planned | — |

Each sprint will record completed work and relevant pull request or release links.

See the [sprint plan](docs/SPRINT_PLAN.md), [GitHub workflow](docs/GITHUB_WORKFLOW.md), and [Sprint 0 progress](docs/SPRINT_0.md) for details.

## Quality Principles

- An undetected feature is distinguished from a confirmed absent feature.
- Test outcomes distinguish passed, failed, skipped, blocked, and execution errors.
- Success criteria are explicitly defined. AI cannot change them to make a failing test pass.
- Tests run only against authorized targets. Data-changing operations are controlled by project policies.
- Credentials, tokens, and connection secrets must not appear in source code or reports.

## Development Setup

Follow the [setup guide](docs/SETUP.md) to create a virtual environment and install the project.

Check the implementation status:

```powershell
python -m adaptive_qa --status
```

This command displays the scaffold status. It does not execute website tests.

## Test Case Models and Validation

Implemented models include:

- Test types: UI, API, and database.
- Execution statuses: passed, failed, skipped, blocked, and error.
- Feature discovery statuses: present, absent, and unknown.
- An immutable test case definition with input validation.
- An immutable execution result model with status, duration, and message validation.
- A reusable login form test definition.

Thirty-eight unit tests cover test case validation, execution results,
project configuration, hostname authorization, and secret resolution.

Run the tests locally:

```powershell
python -m unittest discover -s tests -v
```

Local verification: **38 tests passed**.

GitHub Actions verification: **38 tests passed**.

## Project Configuration and Secrets

Project configuration defines the target URL, explicitly allowed
hostnames, and whether data-changing tests are permitted.

Hostname authorization uses exact matching. Subdomains require explicit
permission. This check is not a complete network security boundary:
DNS resolution, private IP restrictions, and redirect validation
remain pending before network execution is enabled.

Secrets are referenced by environment variable name and resolved at
runtime. Standard string and repr output hide resolved values.
Direct value access and serialization must never be logged.

Environment variables are the initial development mechanism.
Production secret storage will require a dedicated provider.

Project configuration and secret references are currently standalone
components. They are not yet connected to a test runner.

See the [target authorization and secret management contract](docs/SECURITY_CONTRACT.md)
for implemented controls, current limitations, and execution prerequisites.