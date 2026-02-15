# api-codegen Specification

## Purpose
TBD - created by archiving change setup-project-foundation. Update Purpose after archive.
## Requirements
### Requirement: OpenAPI Spec Generation
The backend SHALL auto-generate an OpenAPI specification accessible at the `/openapi.json` endpoint.

#### Scenario: OpenAPI spec is served
- **WHEN** a client sends a GET request to `/openapi.json`
- **THEN** the server responds with a valid OpenAPI 3.x JSON document that describes all registered endpoints

### Requirement: Orval TypeScript Code Generation
The frontend SHALL include an Orval configuration that generates TypeScript types and React Query hooks from the backend's OpenAPI specification.

#### Scenario: Codegen produces valid TypeScript
- **WHEN** a developer runs the codegen command (e.g., `pnpm run codegen`)
- **THEN** Orval generates TypeScript types and React Query hooks into the `src/api/` directory
- **AND** the generated code passes TypeScript type checking

### Requirement: Codegen Script
The repository SHALL provide a script or Makefile target to export the OpenAPI spec and run Orval code generation in a single command.

#### Scenario: Single command generates API client
- **WHEN** a developer runs the codegen script (e.g., `make codegen`)
- **THEN** the OpenAPI spec is exported from the backend and Orval generates the frontend client

