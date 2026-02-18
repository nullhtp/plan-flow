# Project Context

## Purpose

PlanFlow is an AI-powered SaaS that turns any goal into a structured task graph (DAG). Users describe what they want to accomplish in plain language, the system asks adaptive questions to understand the specifics, then generates a directed acyclic graph of tasks with explicit dependency edges, parallel paths, convergence nodes, and a final goal node. The AI stays involved throughout execution, helping users complete tasks and suggesting follow-up goals.

Full project specification: `_docs/PROJECT.md`
Roadmap: `_docs/ROADMAP.md`

## Tech Stack

### Frontend
- **React 19** + **TypeScript** (strict mode)
- **Vite** — build tool and dev server
- **TanStack Router** — type-safe routing with search params validation
- **TanStack Query (React Query)** — server state, caching, optimistic updates
- **Shadcn/ui** — copy-paste Radix-based components
- **Tailwind CSS v4** — utility-first CSS (CSS-first config, no `tailwind.config.js`)
- **Orval** — generates React Query hooks + TypeScript types from OpenAPI spec
- **Biome** — linting and formatting (replaces ESLint + Prettier)

### Backend
- **FastAPI** — Python async web framework
- **Python 3.12+**
- **SQLModel** — ORM built on SQLAlchemy 2.0 + Pydantic (designed for FastAPI)
- **Alembic** — database migrations
- **PostgreSQL** — primary database
- **LangChain / LangGraph** — LLM orchestration and stateful AI pipelines
- **OpenRouter** — multi-provider LLM gateway (GPT-4o, Claude, Llama, etc.)
- **Ruff** — formatting and linting (replaces Black + isort + flake8)
- **Pyright** — static type checking (strict mode)
- **uv** — Python package and virtualenv management

### Infrastructure
- **Docker** + **Docker Compose** — local development environment
- **pnpm** — frontend package manager
- **Monorepo** — single repository, `/frontend` and `/backend` at the root

### API Contract
- Backend auto-generates OpenAPI spec via FastAPI
- Frontend consumes spec via Orval to auto-generate TypeScript types + React Query hooks
- Single source of truth: backend Pydantic/SQLModel schemas define the contract

## Project Conventions

### Code Style

#### Python (Backend)
- **PEP 8** naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants
- **Ruff** for formatting and linting — configured in `pyproject.toml`
- **Pyright strict mode** — all functions must have type annotations
- Line length: 88 characters (Ruff default)
- Use `from __future__ import annotations` for modern type syntax
- Pydantic models for all request/response schemas
- SQLModel models for database entities (combine Pydantic + SQLAlchemy)
- Async everywhere — use `async def` for all route handlers and service functions that do I/O

#### TypeScript (Frontend)
- **Biome** for formatting and linting — configured in `biome.json`
- **Strict TypeScript** — `strict: true` in `tsconfig.json`, no `any` unless explicitly justified
- Functional components only — no class components
- Custom hooks for reusable logic (prefix with `use`)
- Named exports preferred over default exports
- File naming: `kebab-case.tsx` for components, `kebab-case.ts` for utilities
- Component naming: `PascalCase` matching the file (e.g., `board-view.tsx` exports `BoardView`)
- Co-locate related files: component + hook + types in the same directory

#### Shared
- No magic strings — use constants or enums
- No commented-out code in main branch
- TODO comments must reference a specific task or issue

### Architecture Patterns

#### Backend Structure (Domain-Based)

Each domain owns its own models, schemas, router, and service. Shared infrastructure lives in `core/`.

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, middleware, startup, router aggregation
│   ├── core/                      # Shared infrastructure (not a domain)
│   │   ├── config.py              # Settings via pydantic-settings
│   │   ├── db.py                  # Database engine, session factory, base model
│   │   ├── deps.py                # Shared dependencies (DB session, current user)
│   │   ├── security.py            # Password hashing, JWT/token utilities
│   │   └── types.py               # Cross-domain Pydantic schemas (BoardSkeletonOutput, etc.)
│   ├── domains/
│   │   ├── auth/
│   │   │   ├── models.py          # User SQLModel
│   │   │   ├── schemas.py         # RegisterRequest, LoginRequest, TokenResponse, etc.
│   │   │   ├── repository.py      # UserRepository (DB queries)
│   │   │   ├── router.py          # POST /auth/register, /auth/login, etc.
│   │   │   ├── service.py         # Auth business logic (uses UserRepository)
│   │   │   └── deps.py            # Domain-specific dependencies (e.g., get_current_user)
│   │   ├── goals/
│   │   │   ├── models.py          # Goal SQLModel
│   │   │   ├── schemas.py         # GoalCreate, GoalResponse, QuestionSchema, etc.
│   │   │   ├── repository.py      # GoalRepository (DB queries)
│   │   │   ├── router.py          # POST /goals, GET /goals, POST /goals/:id/answers
│   │   │   └── service.py         # Goal CRUD, question flow, state transitions
│   │   ├── boards/
│   │   │   ├── models.py          # Board, Task, TaskDependency, Subtask SQLModels
│   │   │   ├── schemas.py         # BoardResponse, EdgeResponse, TaskCreate, etc.
│   │   │   ├── dag_utils.py       # DAG validation (Kahn's algorithm), goal node validation
│   │   │   ├── position_utils.py  # Fractional indexing for ordered positioning
│   │   │   ├── ownership.py       # Board/task/subtask ownership validation + error classes
│   │   │   ├── board_repository.py   # BoardRepository (DB queries)
│   │   │   ├── task_repository.py    # TaskRepository + dependency queries
│   │   │   ├── subtask_repository.py # SubtaskRepository
│   │   │   ├── board_service.py   # Board CRUD, list, response building
│   │   │   ├── task_service.py    # Task CRUD, status validation, board generation
│   │   │   ├── subtask_service.py # Subtask CRUD
│   │   │   ├── service.py         # Backward-compat re-export shim (will be removed)
│   │   │   └── router.py          # Thin HTTP layer, delegates to services
│   │   └── ai/
│   │       ├── schemas.py         # AI schemas (classification, questions, chat, tool actions)
│   │       ├── llm.py             # Shared LLM factory (get_llm, get_chat_llm)
│   │       ├── router.py          # POST /tasks/:id/chat, POST /boards/:id/chat, etc.
│   │       ├── service.py         # High-level AI operations (classify, generate, chat)
│   │       ├── memory.py          # AI memory retrieval and storage
│   │       ├── pending_actions.py # PendingAction CRUD and tool execution dispatcher
│   │       ├── checkpointer.py    # LangGraph checkpoint persistence
│   │       ├── lang_utils.py      # Language detection utilities
│   │       ├── nodes/             # Individual LangGraph nodes
│   │       │   ├── classify.py
│   │       │   ├── questions.py
│   │       │   ├── generate_board.py
│   │       │   └── enrich_task.py
│   │       ├── graphs/            # LangGraph graph definitions
│   │       │   ├── base.py        # Shared graph utilities (should_continue, execute_tools)
│   │       │   ├── chat.py        # Task chat graph
│   │       │   └── board_chat.py  # Board chat graph
│   │       ├── tools/             # AI chat tools (retrieval, mutations, structure)
│   │       └── prompts/           # System prompts and output JSON schemas
├── migrations/                    # Alembic migrations
├── tests/
│   ├── domains/                   # Tests mirror domain structure
│   │   ├── auth/
│   │   ├── goals/
│   │   ├── boards/
│   │   └── ai/
│   ├── conftest.py                # Shared fixtures (db session, test client, auth helpers)
│   └── factories.py               # Test data factories
├── pyproject.toml
└── Dockerfile
```

**Domain rules:**
- Each domain is self-contained: owns its models, schemas, repositories, services, and router
- **Repository pattern**: each domain has repository classes that encapsulate DB queries. Services call repositories, never use `session.execute()` directly.
- A domain may import from `core/` (shared infrastructure and cross-domain types)
- A domain may import **models and schemas** from other domains when needed (e.g., `boards` references `goals.models.Goal`)
- A domain must NOT import **services or routers** from other domains — use dependency injection or pass data through the router/service layer instead
- **Exception**: `boards/task_service.py` imports `goals/service.py` for goal state transitions (board generation needs to transition goals). This is the only cross-domain service import.
- The `ai/` domain is a service provider — other domains call it, it does not call other domain services
- Routers are thin HTTP layers — they call services and convert domain errors to HTTP responses
- Services contain business logic and use repositories for data access
- All models from all domains are importable by Alembic for migration auto-generation

#### Frontend Structure
```
frontend/
├── src/
│   ├── main.tsx                 # App entry point
│   ├── app.tsx                  # Root component, providers
│   ├── routes/                  # TanStack Router route definitions
│   ├── features/                # Feature-based modules
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── types.ts
│   │   ├── goals/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── types.ts
│   │   ├── board/
│   │   │   ├── components/      # DagView, TaskNode, GoalNode, TaskDetailPanel, etc.
│   │   │   ├── hooks/           # useBoard, useBoardList, useTaskMutations, etc.
│   │   │   ├── utils/           # dagre-layout.ts (React Flow + dagre auto-layout)
│   │   │   ├── __tests__/
│   │   │   └── types.ts
│   │   └── ai-chat/
│   │       ├── components/
│   │       └── hooks/
│   ├── shared/                  # Shared utilities, components, hooks
│   │   ├── components/          # Generic UI components (wrappers over Shadcn)
│   │   ├── hooks/
│   │   ├── lib/                 # Utility functions
│   │   └── types.ts             # Shared TypeScript types
│   ├── api/                     # Orval-generated API client + hooks
│   └── styles/                  # Global styles, Tailwind config
├── public/
├── index.html
├── biome.json
├── tsconfig.json
├── vite.config.ts
└── package.json
```

**Frontend rules:**
- Feature modules are self-contained — a feature can import from `shared/` and `api/` but not from other features
- Cross-feature communication happens through routes (URL state) or a shared context at the app level
- API layer is auto-generated — never hand-write API calls, always regenerate from OpenAPI spec
- React Query manages all server state — no manual fetch + useState for API data

#### AI Pipeline Pattern
- LangGraph defines the pipeline as a state graph
- Each node is a single responsibility (classify goal, generate questions, generate board, etc.)
- All LLM outputs use structured output (JSON schemas via `.with_structured_output()`) — never parse free-text
- Board generation produces a flat list of tasks with `depends_on` arrays forming a DAG — validated via Kahn's algorithm before persistence
- Prompts are stored as separate files or constants, not inline in business logic
- AI service exposes simple async functions to the rest of the backend — callers don't know about LangGraph internals

### Testing Strategy

Tests are integrated into each milestone, focused on critical paths.

#### Backend
- **pytest** + **pytest-asyncio** for async test support
- **httpx** `AsyncClient` for API integration tests (test FastAPI app directly)
- Test layers:
  - **Unit tests** — services and utility functions
  - **Integration tests** — API endpoints with real DB (test database, reset between tests)
  - **AI output tests** — validate LLM output against JSON schemas, test with mocked LLM responses for determinism
- Test naming: `test_<module>/test_<function_or_scenario>.py`
- Fixtures for: database session, authenticated user, sample goals/boards

#### Frontend
- **Vitest** for unit and component tests
- **Testing Library** (`@testing-library/react`) for component interaction tests
- Test what matters: user flows, form validation, error states, conditional rendering
- Mock API responses via MSW (Mock Service Worker) or Orval-generated mocks
- No snapshot tests unless explicitly justified

#### AI-Specific Testing
- Golden tests: known goal inputs → validate output structure (not exact content)
- Schema validation: every LLM response must parse against its Pydantic/JSON schema
- Fallback tests: verify behavior when LLM returns malformed output or times out

### Git Workflow

#### Branching
- **Trunk-based development** — `main` is the primary branch
- Short-lived feature branches: `feat/description`, `fix/description`, `refactor/description`
- Branches merge back to `main` via PR (even solo — keeps history clean)
- No long-lived `develop` or `staging` branches

#### Commit Messages
- **Conventional Commits** format:
  ```
  feat: add goal classification AI node
  fix: correct task status transition validation
  refactor: extract board service from router
  chore: update dependencies
  docs: add API endpoint documentation
  test: add integration tests for auth endpoints
  ```
- Scope is optional but encouraged for clarity:
  ```
  feat(ai): add board generation pipeline
  fix(board): correct column reorder persistence
  ```
- Commits should be atomic — one logical change per commit

#### PR Conventions
- PR title follows Conventional Commits format
- PR description references the relevant openspec change if applicable
- All CI checks must pass before merge

## Domain Context

### Key Domain Concepts
- **Goal** — a user's desired outcome described in natural language (e.g., "Move from Berlin to Lisbon")
- **Board** — a task graph (DAG) generated from a goal, containing tasks connected by dependency edges
- **Task** — an actionable item with status (`not_started` / `in_progress` / `done`), progressive metadata, and dependency relationships
- **TaskDependency** — a directed edge in the DAG: the dependent task is blocked until the prerequisite task is `done`
- **Goal node** — exactly one task per board with `is_goal_node: true`, the final sink of the DAG representing the user's original goal. Depends on all leaf tasks.
- **Convergence node** — a task that depends on multiple parallel paths, merging independent work streams into a shared milestone
- **Lock mechanic** — a task is locked (`is_locked: true`) when any of its dependencies is not `done`. Locked tasks cannot be started. This creates a game-like unlock experience.
- **Progressive metadata** — task fields (due date, priority, time estimate) that the AI adds only when relevant to the goal type
- **Adaptive questioning** — AI generates goal-specific questions as a dynamic form, not a chat
- **Cross-goal intelligence** — AI remembers context from a user's past goals to improve future plans
- **AI-assisted execution** — ongoing AI help during task completion (guidance, adaptation, blocker resolution)

### AI Pipeline Stages
1. **Goal classification** — determine domain, complexity, key dimensions; reject if confidence < threshold
2. **Question generation** — produce 3–7 adaptive form fields (+ optional 1 follow-up round)
3. **Board generation** — create flat task list with dependency edges forming a valid DAG, including convergence nodes and a single goal node
4. **Execution support** — task-level chat, board adaptation, follow-up suggestions

### Business Rules
- Board generation is purely dynamic — no pre-built templates
- AI generates dependency graph; users can edit task details but not dependencies manually (AI-only for MVP)
- Task status transitions are validated server-side: `in_progress` requires all dependencies `done`; `done` requires currently `in_progress`
- Exactly one goal node per board (DAG sink) — board completion is detected by goal node status
- Unlimited active boards during MVP (no limits)
- Email + password auth only for MVP (no OAuth)
- All features free during MVP — no payment infrastructure
- Single-user only — no collaboration features in MVP

## Important Constraints

### Technical Constraints
- **Monorepo** — frontend and backend must coexist in one repository
- **OpenAPI as contract** — backend defines the API, frontend generates client from it. No hand-written API calls on the frontend.
- **Structured AI output only** — all LLM responses must conform to JSON schemas. No free-text parsing.
- **Async Python** — all I/O-bound operations in the backend must be async
- **No SSR** — frontend is a client-side SPA (Vite), not server-rendered

### Operational Constraints
- Solo developer + AI coding assistants
- Full-time availability
- MVP target: 1–2 months
- Hosting strategy TBD — code must be containerized (Docker) for portability

### Cost Constraints
- AI API costs must be monitored — use cheaper models for low-stakes pipeline stages (classification), stronger models for high-stakes stages (board generation)
- OpenRouter enables model switching without code changes

## External Dependencies

### APIs
- **OpenRouter** (`https://openrouter.ai/api/v1`) — LLM gateway for all AI operations. Provides access to OpenAI, Anthropic, Meta, and other models through a single API.

### Key Libraries (Backend)
- **FastAPI** — web framework
- **SQLModel** — ORM (SQLAlchemy 2.0 + Pydantic)
- **Alembic** — database migrations
- **LangChain** — LLM abstraction and tooling
- **LangGraph** — stateful AI pipeline orchestration
- **Pydantic v2** — data validation (used by FastAPI, SQLModel, and AI output schemas)
- **uvicorn** — ASGI server

### Key Libraries (Frontend)
- **React 19** — UI framework
- **TanStack Router** — routing
- **TanStack Query** — server state management
- **Shadcn/ui** — component library (Radix primitives + Tailwind)
- **Tailwind CSS v4** — styling
- **Orval** — OpenAPI → React Query codegen
- **@xyflow/react** (React Flow v12) — interactive DAG graph visualization (pan, zoom, custom nodes)
- **dagre** — hierarchical auto-layout for the DAG (top-to-bottom positioning)
- **canvas-confetti** — celebration animation when goal node is completed

### Infrastructure
- **PostgreSQL** — primary database
- **Docker** — containerization for local dev and deployment
- **GitHub Actions** (planned) — CI/CD pipeline
