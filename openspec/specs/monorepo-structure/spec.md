# monorepo-structure Specification

## Purpose
Monorepo directory layout. Defines the `/frontend` and `/backend` top-level structure, shared tooling configuration, and root-level Makefile for common development commands.
## Requirements
### Requirement: Monorepo Directory Layout
The repository SHALL contain a `/frontend` directory for the React/TypeScript application and a `/backend` directory for the FastAPI/Python application at the repository root.

#### Scenario: Repository root contains frontend and backend
- **WHEN** a developer clones the repository
- **THEN** the root contains `/frontend` and `/backend` directories
- **AND** each directory is a self-contained project with its own dependency manifest (`package.json` and `pyproject.toml` respectively)

### Requirement: Backend Project Configuration
The `/backend` directory SHALL use `uv` for Python virtual environment and dependency management, with a `pyproject.toml` that declares Python 3.12+ as the minimum version.

#### Scenario: Backend dependencies install with uv
- **WHEN** a developer runs `uv sync` in the `/backend` directory
- **THEN** a virtual environment is created and all dependencies are installed
- **AND** a `uv.lock` lockfile is present for reproducible installs

### Requirement: Frontend Project Configuration
The `/frontend` directory SHALL use `pnpm` as the package manager, with a `package.json` declaring all frontend dependencies.

#### Scenario: Frontend dependencies install with pnpm
- **WHEN** a developer runs `pnpm install` in the `/frontend` directory
- **THEN** all dependencies are installed
- **AND** a `pnpm-lock.yaml` lockfile is present for reproducible installs

