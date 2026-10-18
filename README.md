# Adaptive-QA-Project

An AI-powered QA platform that discovers web application features and runs applicable UI, API, and database tests.

**Status:** Sprint 0 in progress. The project scaffold and test case model are implemented. The test execution engine is not implemented yet.

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

Sprints target approximately two weeks of work. Dates will be determined according to capacity and scope. A sprint is completed only when its acceptance criteria are verified.

| Sprint | Goal | Status | Delivered |
|---|---|---|---|
| 0 | Architecture and GitHub workflow | In progress | Python scaffold, architecture record, CI configuration, issue and PR templates, validated test case model, eight passing unit tests |
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

Eight unit tests cover valid definitions, required fields, collection validation, test types, and data modification flags.

Run the tests locally:

```powershell
python -m unittest discover -s tests -v
```

Local verification: **8 tests passed**.

GitHub Actions results must be verified after pushing the changes.