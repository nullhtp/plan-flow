## MODIFIED Requirements

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
