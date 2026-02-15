## Context
PlanFlow is a greenfield monorepo with a Python backend (FastAPI) and TypeScript frontend (React/Vite). This change sets up the entire dev infrastructure from scratch. The decisions here affect every future milestone, so they need to align with the tech stack defined in `openspec/project.md`.

Solo developer, AI-assisted. Tooling must be simple, fast, and low-maintenance.

## Goals / Non-Goals
- Goals:
  - Buildable, lintable, type-checkable monorepo from day one
  - One-command local dev environment (Docker Compose)
  - Automated OpenAPI → TypeScript codegen pipeline
  - CI that catches lint/type/test failures before merge
  - Pre-commit hooks that enforce code quality locally
- Non-Goals:
  - Production deployment (that's M9)
  - Any user-facing features
  - Database schema beyond what Alembic needs to initialize
  - Test coverage — just wire up test runners with a placeholder test each

## Decisions

### Monorepo layout
- Decision: Flat `/frontend` and `/backend` at repo root. No monorepo framework (Nx, Turborepo).
- Rationale: Only two packages. A monorepo framework adds complexity without benefit at this scale. pnpm workspaces are not needed since there's only one JS package.

### Python project management
- Decision: Use `uv` for virtual environment and dependency management. Single `pyproject.toml` in `/backend`.
- Rationale: `uv` is fast, handles venvs and lockfiles, and is specified in the tech stack.

### Frontend package manager
- Decision: `pnpm` as specified in the tech stack.
- Rationale: Fast, disk-efficient, strict dependency resolution.

### Backend structure
- Decision: Follow the domain-based structure from `project.md` — `app/main.py`, `app/core/`, `app/domains/`. Scaffold with a single health-check endpoint.
- Rationale: Matches the conventions doc exactly. A health endpoint validates the full stack works.

### Frontend structure
- Decision: Follow the feature-based structure from `project.md` — `src/routes/`, `src/features/`, `src/shared/`, `src/api/`. Scaffold with a root route and placeholder page.
- Rationale: Matches the conventions doc. Minimal but demonstrable.

### Shadcn/ui initialization
- Decision: Initialize Shadcn/ui with default config. Install a single component (Button) to validate the setup.
- Rationale: Shadcn is copy-paste — init sets up the `components.json` and tailwind integration. One component proves it works.

### OpenAPI codegen
- Decision: Backend exposes OpenAPI JSON at `/openapi.json`. Orval reads it and generates TypeScript types + React Query hooks into `frontend/src/api/`. A script (`make codegen` or `pnpm run codegen`) automates this.
- Rationale: Matches the API contract strategy from `project.md`. Backend must be running (or spec exported as file) for codegen.

### Docker Compose
- Decision: Three services — `backend` (FastAPI/uvicorn), `frontend` (Vite dev server), `db` (PostgreSQL 16). Backend and frontend use Dockerfiles with multi-stage builds. Dev mode mounts source code as volumes for hot-reload.
- Rationale: Standard local dev setup. PostgreSQL 16 is current stable.

### CI pipeline
- Decision: GitHub Actions with a single workflow that runs on push/PR to `main`. Jobs: backend (ruff check, ruff format --check, pyright, pytest), frontend (biome check, tsc --noEmit, vitest run). Jobs run in parallel.
- Rationale: Catches issues early. Parallel jobs keep CI fast.

### Pre-commit hooks
- Decision: Use `pre-commit` framework (Python) for backend hooks (ruff) and `lint-staged` + `husky` for frontend hooks (biome). Alternatively, use `pre-commit` for everything since it supports both Python and Node.
- Final decision: Use the `pre-commit` framework for both — it handles multi-language repos well, and keeps configuration in one `.pre-commit-config.yaml`.
- Rationale: Single tool, single config, runs ruff + biome + pyright + tsc before commit.

### Database initialization
- Decision: Alembic `env.py` configured to connect to PostgreSQL. Initial migration is empty (just proves the pipeline works). No application tables yet.
- Rationale: Application models come in M1+. This change only validates the migration pipeline.

## Risks / Trade-offs
- `pre-commit` hooks running pyright/tsc on every commit can be slow → Mitigation: Only run fast checks (ruff, biome format) as pre-commit; leave type checking to CI. Include a `make check` command for manual full checks.
- Docker Compose adds startup time for dev → Mitigation: Developers can also run frontend/backend natively outside Docker. Docker Compose is optional convenience, not mandatory.
- Orval codegen requires backend to be running → Mitigation: Add a `make export-openapi` command that starts the backend temporarily, exports the spec to a JSON file, then stops. Orval reads from the file.

## Open Questions
- None — the tech stack and conventions are well-defined in `project.md`.
