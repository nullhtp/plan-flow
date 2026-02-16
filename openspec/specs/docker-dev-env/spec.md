# docker-dev-env Specification

## Purpose
Docker Compose local development environment. Defines services for the FastAPI backend, React frontend, and PostgreSQL database with volume mounts, environment variables, and health checks.
## Requirements
### Requirement: Docker Compose Local Environment
The repository SHALL include a `docker-compose.yml` that defines services for the backend, frontend, and PostgreSQL database for local development.

#### Scenario: All services start with Docker Compose
- **WHEN** a developer runs `docker compose up`
- **THEN** the backend, frontend, and PostgreSQL services start
- **AND** the backend can connect to the PostgreSQL database
- **AND** the frontend dev server is accessible in a browser

### Requirement: Backend Dockerfile
The backend SHALL include a Dockerfile that builds the FastAPI application with all dependencies.

#### Scenario: Backend container starts successfully
- **WHEN** the backend Docker image is built and run
- **THEN** the FastAPI application starts and responds to health check requests

### Requirement: Frontend Dockerfile
The frontend SHALL include a Dockerfile that runs the Vite development server with all dependencies.

#### Scenario: Frontend container starts successfully
- **WHEN** the frontend Docker image is built and run
- **THEN** the Vite dev server starts and serves the application

### Requirement: Hot Reload in Docker
The Docker Compose configuration SHALL mount source code as volumes so that code changes are reflected without rebuilding containers.

#### Scenario: Backend code changes are reflected
- **WHEN** a developer modifies a Python file in `/backend` while Docker Compose is running
- **THEN** the backend server detects the change and reloads automatically

#### Scenario: Frontend code changes are reflected
- **WHEN** a developer modifies a TypeScript/React file in `/frontend` while Docker Compose is running
- **THEN** the Vite dev server applies the change via hot module replacement

