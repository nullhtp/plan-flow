## 1. Monorepo Structure
- [ ] 1.1 Create `/backend` directory with `pyproject.toml` (Python 3.12+, uv managed, project metadata and dependency groups)
- [ ] 1.2 Create `/frontend` directory with `package.json` (React 19, Vite, TypeScript)
- [ ] 1.3 Create root `.gitignore` covering Python, Node.js, IDE, and OS artifacts
- [ ] 1.4 Create root `Makefile` with help target and placeholder targets for lint, format, type-check, test, codegen

## 2. Backend Scaffolding
- [ ] 2.1 Set up `app/main.py` with FastAPI application, CORS middleware, and `/health` endpoint
- [ ] 2.2 Create `app/core/config.py` with pydantic-settings `Settings` class (DATABASE_URL, etc.)
- [ ] 2.3 Create `app/core/db.py` with SQLModel async engine and session factory
- [ ] 2.4 Create empty domain directories (`app/domains/`) with `__init__.py` files
- [ ] 2.5 Configure Alembic (`alembic.ini`, `migrations/env.py`) connected to PostgreSQL
- [ ] 2.6 Configure Ruff in `pyproject.toml` (line-length 88, select rules, format settings)
- [ ] 2.7 Configure Pyright in `pyproject.toml` (strict mode)
- [ ] 2.8 Add pytest + pytest-asyncio to dev dependencies, create `tests/conftest.py` and one placeholder test
- [ ] 2.9 Verify: `ruff check`, `ruff format --check`, `pyright`, and `pytest` all pass

## 3. Frontend Scaffolding
- [ ] 3.1 Initialize Vite React TypeScript project in `/frontend`
- [ ] 3.2 Configure TypeScript strict mode in `tsconfig.json`
- [ ] 3.3 Install and configure TanStack Router with a root route and placeholder page
- [ ] 3.4 Install and configure TanStack Query with `QueryClientProvider` at app root
- [ ] 3.5 Install Tailwind CSS v4 and configure with CSS-first approach
- [ ] 3.6 Initialize Shadcn/ui and install one component (Button) to validate the setup
- [ ] 3.7 Configure Biome in `biome.json` (formatting + linting rules)
- [ ] 3.8 Install Vitest + Testing Library, create one placeholder test
- [ ] 3.9 Verify: `biome check`, `tsc --noEmit`, and `vitest run` all pass

## 4. OpenAPI Code Generation
- [ ] 4.1 Verify `/openapi.json` endpoint is served by FastAPI (auto-generated)
- [ ] 4.2 Install Orval as a dev dependency in `/frontend`
- [ ] 4.3 Create Orval config (`orval.config.ts`) to read from OpenAPI spec and output to `src/api/`
- [ ] 4.4 Add `codegen` script to `frontend/package.json`
- [ ] 4.5 Add `make codegen` target to root Makefile (export spec + run Orval)
- [ ] 4.6 Verify: run codegen, confirm generated TypeScript compiles without errors

## 5. Docker Setup
- [ ] 5.1 Create `backend/Dockerfile` (Python 3.12, uv install, uvicorn entrypoint)
- [ ] 5.2 Create `frontend/Dockerfile` (Node, pnpm install, Vite dev server entrypoint)
- [ ] 5.3 Create root `docker-compose.yml` with backend, frontend, and PostgreSQL services
- [ ] 5.4 Configure volume mounts for hot-reload in both backend and frontend
- [ ] 5.5 Add `.env.example` with required environment variables documented
- [ ] 5.6 Verify: `docker compose up` starts all services, backend connects to DB, frontend is accessible

## 6. CI Pipeline
- [ ] 6.1 Create `.github/workflows/ci.yml` with trigger on push/PR to `main`
- [ ] 6.2 Add backend job: install uv, install deps, run `ruff check`, `ruff format --check`, `pyright`, `pytest`
- [ ] 6.3 Add frontend job: install pnpm, install deps, run `biome check`, `tsc --noEmit`, `vitest run`
- [ ] 6.4 Configure jobs to run in parallel
- [ ] 6.5 Verify: push to a branch, open PR, confirm CI runs and passes

## 7. Pre-Commit Hooks
- [ ] 7.1 Install `pre-commit` framework and create `.pre-commit-config.yaml`
- [ ] 7.2 Configure hooks for Ruff (format + lint) on Python files
- [ ] 7.3 Configure hooks for Biome (format + lint) on TypeScript/React files
- [ ] 7.4 Run `pre-commit install` to activate hooks
- [ ] 7.5 Verify: attempt a commit with a formatting violation, confirm it is rejected

## 8. Integration Verification
- [ ] 8.1 Run full Docker Compose environment and verify all services communicate
- [ ] 8.2 Run OpenAPI codegen against the running backend and verify output
- [ ] 8.3 Confirm all Makefile targets work as documented
- [ ] 8.4 Push branch and verify CI pipeline passes end-to-end
