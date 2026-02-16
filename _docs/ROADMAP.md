# PlanFlow — MVP Roadmap

> Milestone-based roadmap for building PlanFlow from zero to public MVP.
> Solo developer, full-time, AI-assisted. No time estimates — milestones ship when their deliverables are done.

## Approach

**Vertical slice first.** Each milestone builds a thin, working end-to-end slice before going wide. This means the product is demoable and testable at every stage — not just at the end.

**Two-phase MVP.** The MVP is split into Alpha and Beta:

- **Alpha** — the core magic: goal → questions → DAG generation → task graph interaction. This is the minimum needed to validate the product's core value ("describe a goal, get a real plan with dependencies").
- **Beta** — AI-assisted execution, cross-goal intelligence, and polish. These features deepen engagement but depend on users already having boards to work with.

**Testing integrated.** Each milestone includes testing for its deliverables. Focus on critical paths: AI output validation, board CRUD correctness, auth security. No coverage targets — test what matters.

---

## Milestone Overview

```
M0  Project Foundation
 │
M1  Auth System
 │
M2  AI Pipeline — Goal Understanding
 │
M3  AI Pipeline — Board Generation
 │
M4  Board UI — Display & Manual Editing
 │
M5  Core Loop Integration
 │
 ├──── ALPHA RELEASE ────
 │
M6  AI-Assisted Execution
 │
M7  Cross-Goal Intelligence
 │
M8  Polish, Edge Cases & Hardening
 │
M9  Deployment & Launch Infrastructure
 │
 └──── BETA / PUBLIC MVP ────
```

---

## M0: Project Foundation

Set up the monorepo, tooling, and dev infrastructure. Nothing user-facing — this is the foundation everything builds on.

### Deliverables

- **Monorepo structure**
  - `/frontend` — React + TypeScript (Vite)
  - `/backend` — FastAPI (Python)
  - `/shared` or codegen output directory for OpenAPI-generated types
- **Frontend scaffolding**
  - React + TypeScript + Vite
  - React Query configured
  - Router setup ( TanStack Router)
  - Base UI component library chosen and installed (e.g., Shadcn/ui, Radix, or Mantine)
  - Biome configured
- **Backend scaffolding**
  - FastAPI project structure (routers, services, schemas, models)
  - SQLAlchemy or equivalent ORM configured
  - Alembic for database migrations
  - PostgreSQL connection (local Docker or hosted dev instance)
  - Ruff for Python formatting/linting
  - Pyright
- **OpenAPI code generation pipeline**
  - Backend auto-generates OpenAPI spec
  - Frontend auto-generates TypeScript API client + types from spec
  - Script or Makefile command to regenerate (`make codegen` or similar)
- **Docker setup**
  - `docker-compose.yml` for local development (frontend, backend, Postgres)
  - Dockerfiles for frontend and backend
- **CI pipeline** (GitHub Actions or similar)
  - Lint + format check (frontend and backend)
  - Type check (frontend `tsc --noEmit`, backend `pyright`)
  - Test runner wired up (even if no tests yet)
- **Git setup**
  - `.gitignore`, branch strategy decided
  - Pre-commit hooks (lint, format, type check)

### Tests

- CI pipeline runs successfully on an empty project
- OpenAPI codegen produces valid TypeScript types from a dummy endpoint
- Docker Compose brings up all services and they can communicate

---

## M1: Auth System

Email + password authentication. Users can register, log in, log out, and access protected routes.

### Deliverables

- **Backend**
  - User model + migration (id, email, password_hash, created_at, updated_at)
  - Password hashing (bcrypt)
  - Registration endpoint (`POST /auth/register`)
  - Login endpoint (`POST /auth/login`) — returns JWT or sets session cookie
  - Logout endpoint (`POST /auth/logout`)
  - Current user endpoint (`GET /auth/me`)
  - Auth middleware / dependency that protects routes
  - Input validation (email format, password strength)
  - Duplicate email handling
- **Frontend**
  - Registration page
  - Login page
  - Auth state management (React context or similar)
  - Protected route wrapper (redirects to login if unauthenticated)
  - Auto-generated API client includes auth endpoints
  - Token/session persistence across page reloads
- **Security**
  - Passwords never stored in plain text
  - JWT expiry and refresh strategy (if using JWT)
  - Rate limiting on auth endpoints (optional for MVP but recommended)

### Tests

- Register with valid credentials → success, user exists in DB
- Register with duplicate email → proper error
- Login with valid credentials → returns token/session
- Login with wrong password → proper error
- Protected endpoint without auth → 401
- Protected endpoint with valid auth → success

---

## M2: AI Pipeline — Goal Understanding

The first half of the AI pipeline: user enters a goal, AI classifies it and generates adaptive questions presented as a dynamic form.

### Deliverables

- **Backend — AI Service**
  - OpenRouter client configured (API key management, model selection)
  - LangChain/LangGraph pipeline setup
  - **Goal classification node** — takes raw goal text, outputs: domain category, estimated complexity, key dimensions to explore
  - **Question generation node** — takes classification output, produces 3–7 structured questions as JSON (each with: question text, field type [text/select/multiselect/number], options if applicable, why this question matters)
  - Structured output enforcement — LLM responses validated against JSON schemas, retry on malformed output
  - Goal model + migration (id, user_id, title, original_input, status, ai_context, created_at, updated_at)
  - Conversation model + migration (stores the questioning phase exchange)
- **API Endpoints**
  - `POST /goals` — create a new goal from raw text, triggers classification + question generation
  - `GET /goals/:id/questions` — returns generated questions for the goal
  - `POST /goals/:id/answers` — submit answers to the generated questions, stores in ai_context
- **Frontend**
  - "New Goal" page with free-text input
  - Dynamic form renderer — takes the AI-generated question schema and renders appropriate form fields
  - Form submission flow — answers sent back to the API
  - Loading/streaming states while AI generates questions
  - Error handling for AI failures (timeout, malformed output, provider errors)
- **Prompt Engineering**
  - System prompts for goal classification
  - System prompts for question generation
  - Output schemas (JSON) for both stages
  - Test with diverse goal types: personal, professional, creative, learning, health, logistical

### Tests

- Goal classification returns valid domain + complexity for a variety of inputs
- Question generation produces 3–7 questions with correct schema
- Malformed LLM output triggers retry and eventually returns valid output or clear error
- API flow: create goal → get questions → submit answers → answers stored correctly
- Frontend renders different field types correctly (text, select, number)

---

## M3: AI Pipeline — Board Generation

The second half of the AI pipeline: given a goal + answers, AI generates a DAG of tasks with dependency edges.

### Deliverables

- **Backend — AI Service**
  - **Board generation node** — takes goal + ai_context (answers), produces structured board JSON:
    - Flat list of tasks: id, title, description, `depends_on` (array of prerequisite task IDs), `is_goal_node` (boolean), and progressive metadata (due_date, priority, estimated_minutes — included only when relevant)
    - Dependency edges forming a valid DAG (no cycles)
    - Exactly one task with `is_goal_node: true` as the DAG sink
    - Convergence nodes where parallel paths merge into milestones
  - Structured output enforcement — board JSON validated against Pydantic schema
  - DAG validation — Kahn's algorithm for cycle detection, goal node validation (single sink, no dependents)
  - Board, Task, TaskDependency, Subtask models + migrations
  - Board creation service — takes AI-generated JSON, validates DAG structure, and persists to DB (creates Board → Tasks → TaskDependency edges in a transaction)
- **API Endpoints**
  - `POST /goals/:id/generate-board` — triggers board generation from goal context
  - `GET /boards/:id` — returns full board with tasks, dependency edges, and computed `is_locked` per task
- **Prompt Engineering**
  - System prompt for board generation — instructs AI to create a valid DAG with parallel paths, convergence nodes, and exactly one goal node
  - Prompt includes the goal text, classification, and all answers as context
  - Output schema for DAG structure (tasks with `depends_on` arrays)
  - Progressive metadata instructions — AI decides which metadata fields to include based on goal type
  - Test with the same diverse goal types from M2

### Tests

- Board generation produces valid DAG with tasks and dependency edges for a variety of goal types
- Generated DAGs include parallel paths for independent work streams
- Generated tasks have descriptions and correct dependency relationships
- Exactly one goal node exists per board, serving as the DAG sink
- Progressive metadata is present where expected (deadlines for time-bound goals) and absent where not (hobby goals)
- DAG validation catches cycles and rejects invalid graphs
- Database persistence: generated board is correctly stored with all relations (tasks + edges)
- API returns full board structure with tasks, edges, and computed `is_locked` fields

---

## M4: Board UI — DAG Visualization & Task Interaction

The task graph interface. Users can view their generated DAG, interact with tasks (toggle status, edit details), and see dependencies visually.

### Deliverables

- **DAG View**
  - React Flow-based DAG visualization — tasks as custom nodes, dependencies as bezier curve edges
  - Dagre auto-layout (top-to-bottom hierarchy) — no manual node positioning
  - Pan (drag background) and zoom (scroll wheel) support
  - Clean plain canvas (no dot grid), styled minimap in bottom-right corner
  - Optimistic updates via React Query — UI updates immediately, syncs with server in background
  - Loading spinner while board data loads
- **Task Node Display**
  - Custom task nodes with very rounded corners, soft shadows, status-dependent coloring
  - Lock icon and muted appearance for tasks with unmet prerequisites
  - Priority color tinting (rose=high, amber=medium, sky=low)
  - Due date, subtask progress, and estimated time shown on nodes when present
  - Enhanced green treatment for completed tasks
  - Smooth CSS transitions on status changes
  - Connection handles hidden (nodes not user-connectable)
- **Goal Node Display**
  - Larger node with accent border for the final goal node
  - Progress bar showing completed/total tasks across the board
  - Trophy icon when completed, lock icon when locked
  - Completing the goal node triggers a confetti celebration animation
- **Edge Styling**
  - Smooth bezier curve edges with arrowheads
  - Thick colored edges for unlocked paths, thin gray edges for locked paths
- **Task Interactions**
  - Click task node to open slide-in detail panel (right side)
  - Task detail panel: edit title, description, due date, priority, estimated minutes, status
  - Status toggle: click node status icon to cycle `not_started` → `in_progress` → `done`
  - Locked task status toggle disabled (tooltip shows blocking tasks)
  - "Dependencies" section listing prerequisite tasks
  - "Unlocks" section listing dependent tasks
  - Delete task with confirmation (warns about dependent tasks)
  - Task detail panel state reflected in URL via `?task=<taskId>` search param
- **Subtask Checklist**
  - Subtasks rendered as checklist in detail panel
  - Add, toggle, and delete subtasks with optimistic updates
- **API Endpoints (CRUD)**
  - `GET /boards` — list boards with progress stats
  - `GET /boards/:id` — full board with tasks, edges, is_locked, is_completed
  - `PATCH /boards/:id` — update board title
  - `POST /boards/:id/tasks` — add task
  - `PATCH /tasks/:id` — update task (title, description, metadata, status with dependency validation)
  - `DELETE /tasks/:id` — delete task (cascades to subtasks and dependency edges)
  - `POST /tasks/:id/subtasks` — add subtask
  - `PATCH /subtasks/:id` — update subtask
  - `DELETE /subtasks/:id` — delete subtask
- **Board List**
  - Home page showing all user's boards as cards with progress bars
  - Board cards show title, goal title, task completion fraction, and progress percentage
  - Navigation from home to individual boards
  - Empty state with "Create a goal" prompt

### Tests

- DAG renders correctly with nodes and edges from API data
- Task status toggle updates status and persists to server
- Locked tasks cannot be started (server returns 409, UI shows lock)
- Completing a task unlocks dependents (visual transition from locked to unlocked)
- Goal node completion triggers celebration animation
- CRUD operations for tasks: create, read, update, delete — all persist correctly
- Subtask operations: add, toggle complete, delete
- Optimistic update: UI reflects change before server confirms
- Optimistic update rollback: if server rejects, UI reverts and shows toast
- Task detail panel opens/closes correctly and reflects in URL

---

## M5: Core Loop Integration

Connect all pieces into the complete end-to-end flow. This is primarily integration work — the individual pieces exist, this milestone makes them a product.

### Deliverables

- **End-to-end flow wired up**
  - User signs up → enters goal → answers questions → DAG is generated → task graph is displayed and interactive
  - All transitions are smooth (no manual page refreshes, proper loading states, error handling)
- **Navigation and UX flow**
  - Clear path from goal input through questions to task graph
  - "Generating your board..." transition with appropriate feedback (progress indicator or streaming)
  - Back navigation — user can revisit their answers before generating
  - Board generation error recovery — if AI fails, user can retry without re-entering everything
- **Goal management**
  - `GET /goals` — list all user's goals
  - Goal status transitions (active → completed, active → archived)
  - Mark goal as complete from board view (completing the goal node)
- **Board regeneration**
  - User can ask AI to regenerate the entire board (re-run generation with same or modified answers)
  - "Regenerate" action with confirmation (destructive — replaces current graph)
- **Edge cases**
  - Empty states (no goals yet, no boards yet)
  - Long goal text handling
  - AI timeout handling with user-friendly messaging
  - Network error handling and retry UI

### Tests

- Full E2E flow: register → create goal → answer questions → generate DAG → toggle task statuses → complete goal node → celebration
- Board regeneration produces a new graph, old board data is replaced
- Error states render correctly (AI timeout, network error)
- Empty states render correctly
- Goal status transitions work correctly

---

## --- ALPHA RELEASE ---

At this point, the core product loop works end-to-end. A user can describe a goal, answer AI-generated questions, receive a fully structured task DAG with dependencies, and work through it by completing tasks to unlock dependents. The board is persistent, interactive, and the user's data is secured behind auth.

**Alpha is testable with real users.** The "wow moment" — describing a goal and seeing it become a visual dependency graph with unlockable tasks — is fully functional. Share with early testers, collect feedback.

---

## M6: AI-Assisted Execution

Phase 3 of the core loop. The AI helps users execute their tasks, not just plan them.

### Deliverables

- **Task-level AI chat**
  - User can open an AI chat panel from any task
  - AI has context: the goal, the board structure, the specific task, and the user's progress
  - User asks questions like "How do I do this?", "What tools do I need?", "Can you break this down further?"
  - AI responses are contextual and actionable
  - Conversation persisted in the Conversation model (phase: execution, linked to task)
- **AI board adaptation**
  - User can request board-level changes through AI: "My budget changed, update the plan", "I have less time than expected"
  - AI modifies the graph structure (add/remove/modify tasks and dependency edges) based on the request
  - Changes are shown as a diff or preview before applying (user confirms)
- **Blocker resolution**
  - When a user is stuck on a task, they can tell the AI
  - AI responds with: alternative approaches, subtask breakdown, simplified version of the task, or suggests skipping and coming back later
  - AI can create subtasks directly on the task from within the chat
- **Goal completion flow**
  - When the goal node is marked as done (all prerequisites are done), AI generates follow-up suggestions
  - Follow-up suggestions are based on: what the user accomplished, natural next steps, the goal domain
  - User can start a new goal directly from a suggestion (pre-fills the goal input)
- **API Endpoints**
  - `POST /tasks/:id/chat` — send a message to AI about a specific task, get response
  - `POST /goals/:id/chat` — send a message to AI about the goal/board level
  - `POST /goals/:id/adapt-board` — AI-generated board modifications (returns diff, user confirms)
  - `POST /goals/:id/complete` — mark goal complete, triggers follow-up suggestion generation
  - `GET /goals/:id/follow-ups` — get AI-suggested follow-up goals

### Tests

- Task chat: AI receives correct context (goal, board state, task details)
- Task chat: conversation is persisted and retrievable
- Board adaptation: AI-generated changes produce a valid DAG (no cycles)
- Board adaptation: user confirmation applies changes correctly
- Board adaptation: user rejection leaves graph unchanged
- Blocker resolution: AI creates valid subtasks
- Goal completion: follow-up suggestions are relevant to the completed goal
- Follow-up goal: pre-fills goal input correctly

---

## M7: Cross-Goal Intelligence

The AI remembers context across all of a user's goals and uses it to generate better plans and suggestions.

### Deliverables

- **User context aggregation**
  - Service that builds a user profile from their goal history: completed goals, common domains, preferences, pace, patterns
  - Stored as a JSON summary that can be injected into AI prompts
  - Updated when goals are completed or significant progress is made
- **Context-aware goal understanding**
  - Question generation considers past goals ("You've already completed X, so I won't ask about Y")
  - Board generation builds on prior work ("Since you already learned basic Japanese, this plan starts at intermediate level")
- **Context-aware follow-ups**
  - Follow-up suggestions after goal completion reference the user's full history, not just the last goal
  - Suggestions form logical progressions (beginner → intermediate → advanced)
- **AI context window management**
  - User history summary is concise enough to fit in prompts without blowing token limits
  - Summarization strategy for users with many completed goals

### Tests

- User with prior goals: question generation reflects past context
- User with prior goals: board generation avoids redundant tasks
- Follow-up suggestions reference user history
- Context summary stays within token budget even with many goals
- New user (no history): everything works normally without cross-goal context

---

## M8: Polish, Edge Cases & Hardening

Tighten everything up before public release. Fix what's broken, smooth what's rough, secure what's exposed.

### Deliverables

- **UI/UX polish**
  - Responsive design — works on tablet and mobile browsers (not optimized, but usable)
  - Consistent loading states, error messages, and empty states across all pages
  - Keyboard shortcuts for common task graph actions (if time permits)
  - Smooth transitions and animations for task status changes and graph interactions
  - Accessibility basics: semantic HTML, focus management, ARIA labels on interactive elements
- **Error handling hardening**
  - AI failure graceful degradation — every AI call has a fallback (retry, cached response, or manual mode)
  - Network error recovery — offline-tolerant behavior where possible (queued writes)
  - Rate limiting on all public endpoints
  - Input sanitization and validation on all user inputs
- **Performance**
  - DAG rendering performance with many tasks (50+ tasks and edges)
  - API response times — board load under 500ms, AI operations have streaming or progress feedback
  - Database query optimization (N+1 prevention, proper indexes on task_dependency)
- **Security**
  - Auth token security review
  - API authorization checks — users can only access their own data
  - SQL injection prevention (ORM parameterization)
  - XSS prevention (React default + any raw HTML handling)
  - CORS configuration
  - Environment variable management (no secrets in code)
- **Edge cases**
  - Very long goal descriptions
  - Goals in non-English languages (if OpenRouter models support it)
  - Rapid successive AI requests
  - Concurrent board edits from multiple browser tabs
  - Browser back/forward navigation through the goal creation flow

### Tests

- Authorization: user A cannot access user B's goals, boards, or tasks
- Performance: DAG with 50 tasks and dependency edges renders and is interactive
- AI failures: UI degrades gracefully, user can retry
- All previously passing tests still pass (regression)

---

## M9: Deployment & Launch Infrastructure

Get the application running in production. Not just "it works on my machine" — real deployment with monitoring.

### Deliverables

- **Hosting setup**
  - Production deployment for frontend (static hosting)
  - Production deployment for backend (containerized)
  - Managed PostgreSQL instance
  - Environment configuration (production env vars, secrets management)
  - Domain + SSL/TLS
- **CI/CD for production**
  - Automated deployment pipeline (push to main → deploy)
  - Staging environment (optional but recommended — deploy PRs or staging branch)
  - Database migration strategy for production (Alembic in CI/CD)
- **Monitoring and observability**
  - Application error tracking (Sentry or similar)
  - Basic uptime monitoring
  - AI cost tracking — monitor OpenRouter spend per user/per request
  - Structured logging (backend)
- **Operational basics**
  - Database backups (automated)
  - Rollback strategy (deploy previous version)
  - Health check endpoints (`/health` for backend)

### Tests

- Deployment pipeline: push triggers build + deploy successfully
- Health check endpoint returns 200
- SSL/TLS configured correctly
- Database migrations run in production without errors
- Error tracking captures and reports a test exception
- Smoke test: full user flow works in production environment

---

## --- BETA / PUBLIC MVP ---

The product is deployed, monitored, and ready for real users. All three phases work end-to-end with cross-goal intelligence. The system is secured, errors are tracked, and the deployment pipeline supports rapid iteration.

**Start collecting real user feedback and iterating.**

---

## Milestone Dependency Graph

```
M0 (Foundation)
 └─► M1 (Auth)
      ├─► M2 (Goal Understanding)
      │    └─► M3 (Board Generation)
      │         └─► M4 (Board UI)
      │              └─► M5 (Integration)
      │                   │
      │              ═══ ALPHA ═══
      │                   │
      │                   ├─► M6 (AI Execution)
      │                   │    └─► M7 (Cross-Goal)
      │                   │
      │                   └─► M8 (Polish) ◄── M6, M7
      │                        └─► M9 (Deploy)
      │                             │
      │                        ═══ BETA ═══
```

Notes:

- M6 and M7 can partially overlap — M7 doesn't strictly require M6 to be fully complete
- M8 (Polish) should start after M6 and M7 are substantially done, but minor polish can happen throughout
- M9 (Deploy) can start in parallel with late M8 work — infrastructure setup doesn't depend on final polish

---

## Risk Register

| Risk                              | Impact                                                       | Mitigation                                                                                                                                             |
| --------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AI output quality is inconsistent | Generated DAGs are useless (too linear, cycles, poor dependencies) | Invest in prompt engineering + structured output validation + DAG cycle detection. Test with 20+ diverse goals before Alpha. Add regeneration as escape hatch. |
| AI costs higher than expected     | Burns through budget during development and testing          | Use cheaper models for classification/questions, strong models for board generation. Track cost per request from M2 onwards. Set per-user rate limits. |
| AI generates poor dependency graphs | Too linear (no parallelism), missing convergence nodes, cycles | Validate DAG structure post-generation (topological sort). Add prompt engineering to encourage parallel paths. Retry on cycle detection. |
| React Flow + dagre rendering issues | Large graphs render slowly or layout looks cluttered        | Lazy-load the DAG view. Dagre handles hierarchical layout well for 5-30 tasks. React Flow supports tree-shaking. Cap task count at 30. |
| Scope creep during polish phase   | M8 expands indefinitely, never ships                         | Timebox M8. Define a "good enough" bar before starting. Ship, then iterate.                                                                            |
| OpenRouter provider outages       | AI features completely unavailable                           | Configure fallback models. Cache recent AI outputs. Degrade gracefully (task editing works without AI).                                               |
| Solo developer burnout            | Progress stalls                                              | Milestones are designed to produce shippable increments. Alpha is a real checkpoint. Take breaks between milestones.                                   |

---

## Definition of Done (per milestone)

A milestone is complete when:

1. All listed deliverables are implemented and functional
2. All listed tests pass
3. No known critical bugs in the milestone's scope
4. Code is committed, CI passes
5. Feature is demoable end-to-end (where applicable)
