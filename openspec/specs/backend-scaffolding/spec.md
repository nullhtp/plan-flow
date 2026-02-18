# backend-scaffolding Specification

## Purpose
Backend project scaffolding. Covers FastAPI application structure (domain-based layout), SQLModel ORM with Alembic migrations, PostgreSQL connection, pydantic-settings configuration, Ruff formatting/linting, and Pyright strict type checking.
## Requirements
### Requirement: FastAPI Application Structure
The backend SHALL follow the domain-based structure defined in project conventions: `app/main.py` as the entry point, `app/core/` for shared infrastructure (including `core/types.py` for cross-domain Pydantic schemas), and `app/domains/` for domain modules. Each domain SHALL separate concerns into: `models.py` (SQLModel table definitions), `schemas.py` (request/response Pydantic models), `repository.py` (database query encapsulation), `service.py` (business logic), `router.py` (HTTP layer), and optional `deps.py` (FastAPI dependencies). Services SHALL call repositories for data access and MUST NOT use `session.execute()` or `session.get()` directly. Domains with multiple entities MAY split services and repositories by entity (e.g., `board_service.py`, `task_service.py`).

#### Scenario: Application starts successfully
- **WHEN** a developer runs the FastAPI application with uvicorn
- **THEN** the server starts without errors and listens for HTTP requests

#### Scenario: Repository pattern enforced
- **WHEN** a service function needs to query or persist data
- **THEN** it calls a repository method instead of using SQLAlchemy session directly

#### Scenario: Cross-domain types in core
- **WHEN** a Pydantic schema is used by multiple domains
- **THEN** it is defined in `app/core/types.py` and imported from there by each domain

### Requirement: Health Check Endpoint
The backend SHALL expose a `GET /health` endpoint that returns HTTP 200 to confirm the application is running.

#### Scenario: Health check returns OK
- **WHEN** a client sends a GET request to `/health`
- **THEN** the server responds with HTTP 200 and a JSON body indicating healthy status

### Requirement: Database Connection Configuration
The backend SHALL configure a PostgreSQL connection using SQLModel with connection parameters loaded from environment variables via pydantic-settings.

#### Scenario: Database connection uses environment variables
- **WHEN** the application starts with `DATABASE_URL` set in the environment
- **THEN** the database engine connects to the specified PostgreSQL instance

### Requirement: Alembic Migration Pipeline
The backend SHALL include an Alembic configuration that connects to the same PostgreSQL database and supports auto-generating migrations from SQLModel models.

#### Scenario: Alembic generates an empty initial migration
- **WHEN** a developer runs `alembic revision --autogenerate -m "initial"`
- **THEN** a migration file is created in the `migrations/versions/` directory
- **AND** the migration can be applied with `alembic upgrade head` without errors

### Requirement: Backend Linting and Formatting
The backend SHALL use Ruff for formatting and linting, configured in `pyproject.toml` with an 88-character line length.

#### Scenario: Ruff checks pass on scaffolded code
- **WHEN** a developer runs `ruff check` and `ruff format --check` in the backend directory
- **THEN** no errors or formatting violations are reported

### Requirement: Backend Type Checking
The backend SHALL use Pyright in strict mode, configured in `pyproject.toml`, with all source files passing type checks.

#### Scenario: Pyright passes on scaffolded code
- **WHEN** a developer runs `pyright` in the backend directory
- **THEN** no type errors are reported

### Requirement: Backend Test Runner
The backend SHALL include pytest configured with pytest-asyncio for async test support, with at least one placeholder test that passes.

#### Scenario: Pytest runs successfully
- **WHEN** a developer runs `pytest` in the backend directory
- **THEN** at least one test passes and the exit code is 0

