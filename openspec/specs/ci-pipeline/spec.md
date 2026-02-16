# ci-pipeline Specification

## Purpose
GitHub Actions CI pipeline. Runs lint, format, type check, and tests for both frontend and backend on pushes and pull requests to main.
## Requirements
### Requirement: GitHub Actions CI Workflow
The repository SHALL include a GitHub Actions workflow that runs on pushes and pull requests to the `main` branch.

#### Scenario: CI triggers on push to main
- **WHEN** a commit is pushed to the `main` branch
- **THEN** the CI workflow starts and runs all configured checks

#### Scenario: CI triggers on pull request to main
- **WHEN** a pull request is opened or updated targeting the `main` branch
- **THEN** the CI workflow starts and runs all configured checks

### Requirement: Backend CI Checks
The CI workflow SHALL run backend checks including linting (ruff check), formatting (ruff format --check), type checking (pyright), and tests (pytest).

#### Scenario: Backend CI checks pass on clean code
- **WHEN** the backend source code has no lint, format, or type errors and all tests pass
- **THEN** the backend CI job completes successfully

#### Scenario: Backend CI checks fail on violations
- **WHEN** the backend source code contains a lint or type error
- **THEN** the backend CI job fails and reports the violations

### Requirement: Frontend CI Checks
The CI workflow SHALL run frontend checks including linting and formatting (biome check), type checking (tsc --noEmit), and tests (vitest run).

#### Scenario: Frontend CI checks pass on clean code
- **WHEN** the frontend source code has no lint, format, or type errors and all tests pass
- **THEN** the frontend CI job completes successfully

#### Scenario: Frontend CI checks fail on violations
- **WHEN** the frontend source code contains a lint or type error
- **THEN** the frontend CI job fails and reports the violations

### Requirement: Parallel CI Jobs
The CI workflow SHALL run backend and frontend checks in parallel to minimize total pipeline time.

#### Scenario: Backend and frontend jobs run concurrently
- **WHEN** the CI workflow is triggered
- **THEN** the backend and frontend jobs start at the same time rather than sequentially

