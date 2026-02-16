# PlanFlow

> AI-powered SaaS that turns any goal into a structured, actionable task graph.

## Vision

PlanFlow transforms ambitions into action. Users describe what they want to accomplish in plain language — bake a cake, move to another city, launch a product, learn a language — and the system intelligently breaks it down into a directed acyclic graph (DAG) of tasks with explicit dependencies, tailored to that specific goal. The AI stays involved throughout the entire journey, helping users complete tasks, adapt to changes, and discover what to do next.

## Problem

People struggle to turn ambitions into action. The gap between "I want to do this" and "here's exactly what I need to do, step by step" is where most goals die. Existing tools fail in three ways:

1. **Project management tools** (Trello, Asana, Notion) require users to already know how to break down their goals — they provide structure but not strategy. Their flat task lists and kanban columns don't express which tasks block others.
2. **AI chatbots** can generate plans, but the output is ephemeral text that doesn't translate into a persistent, interactive workflow.
3. **Goal-tracking apps** focus on habits and metrics, not on turning a complex goal into a concrete graph of dependent tasks.

PlanFlow sits at the intersection: **AI that understands your goal + a persistent, interactive task graph to execute it.**

---

## Solution

PlanFlow operates as a three-phase loop:

### Phase 1: Understand the Goal

The user provides a goal in natural language. Examples:

- "Bake a three-tier wedding cake for 50 guests"
- "Move from Berlin to Lisbon within 3 months"
- "Launch an MVP for my SaaS product"
- "Learn conversational Japanese in 6 months"
- "Train for a half marathon by September"

The system presents a **dynamic, AI-generated form** with adaptive follow-up questions to understand the specifics. Questions are goal-specific — a baking goal gets different questions than a relocation goal. The form adapts as the user answers, showing or hiding follow-ups based on responses.

Typical question areas (goal-dependent):
- Timeline and deadlines
- Budget and resource constraints
- Current experience level / starting point
- Preferences and priorities
- Known blockers or concerns
- Desired outcome quality / depth

The AI asks **3–7 clarifying questions** depending on goal complexity — enough to generate a good plan, not so many that the user loses interest.

### Phase 2: Generate the Task Graph

Based on the gathered context, the AI generates a directed acyclic graph (DAG) of tasks with explicit dependencies:

- **Dependency-driven structure** — tasks are connected by directed edges showing what must be done before what. No generic "To Do / Doing / Done" columns — the graph topology itself captures the plan's structure.
- **Parallel paths** for independent work streams — tasks with no dependency relationship can be worked on simultaneously. Examples:
  - Moving: "Research neighborhoods" and "Check visa requirements" can be done in parallel, both feeding into "Finalize relocation timeline"
  - Product launch: "Design mockups" and "Set up CI/CD" run in parallel before converging at "Build MVP"
- **Convergence nodes** — milestone tasks where parallel paths merge (e.g., "Finalize relocation timeline" depends on both housing and employment research)
- **Goal node** — exactly one final task representing the user's original goal (e.g., "Complete: Relocate to Lisbon") that depends on all leaf tasks. This is the single sink of the DAG — the finish line.
- **Actionable tasks** with clear descriptions, each connected to its prerequisites via dependency edges
- **Progressive metadata** — the AI suggests adding due dates, priorities, or time estimates where they naturally make sense for the goal type (e.g., a move has hard deadlines, a hobby project might not)
- **Game-like unlock mechanic** — completing a task unlocks its dependents. Locked tasks (unmet prerequisites) are visually grayed out with a lock icon. This makes progress visible and motivating.

Board generation is **purely dynamic** — no pre-built templates. The AI generates everything from scratch based on the specific goal and context gathered in Phase 1. This ensures every graph is genuinely tailored, not a generic template with names swapped in.

The graph is immediately usable — **no blank-slate problem.**

The user can **edit task details** — titles, descriptions, metadata, subtasks. Dependency editing is AI-only for MVP (manual dependency editing planned for a future release).

### Phase 3: AI-Assisted Execution

The AI stays involved as the user works through their board:

- **Task guidance** — users can ask the AI for help completing any specific task ("How do I find a reliable moving company in Lisbon?")
- **Progress adaptation** — the graph adjusts as circumstances change ("My budget dropped by 30%, what should I reprioritize?")
- **Blocker resolution** — if a user is stuck, the AI suggests alternatives or breaks the task down into subtasks
- **Smart suggestions** — AI proactively suggests next steps based on what's been completed and what's now unlocked
- **Completion and follow-up** — when the goal node is completed (all prerequisites done), a celebration animation plays and the AI suggests logical next goals or deeper explorations

---

## Core User Flow

```
Describe Goal → Answer Questions → Review Graph → Work Tasks → Complete Goal Node
      ↑                                                                |
      |_____________ AI suggests follow-up goals ______________________|
```

1. **Input goal** — free-text description of what the user wants to achieve
2. **Adaptive questioning** — AI presents a dynamic form with 3–7 clarifying questions
3. **Graph generation** — AI produces a DAG of tasks with dependency edges, parallel paths, convergence nodes, and a final goal node
4. **Review and adjust** — user can edit task details or ask the AI to regenerate
5. **Execute** — user works through the graph, completing tasks to unlock dependents. Locked tasks are visually grayed out until prerequisites are done.
6. **Complete** — completing the final goal node triggers a celebration and AI suggests what to do next

---

## Cross-Goal Intelligence

PlanFlow remembers context across all of a user's boards and goals. This enables:

- **Building on past work** — if a user completed "Learn basic Japanese" and starts "Pass JLPT N3", the AI knows their starting point
- **Avoiding redundancy** — the AI won't generate tasks the user has already completed in a prior goal
- **Smarter follow-up suggestions** — recommendations are based on the user's actual history, not generic ideas
- **Progress patterns** — the system learns how the user works (speed, preferences, common blockers) and adapts accordingly

---

## Key Differentiators

| Aspect | Traditional Tools | PlanFlow |
|--------|------------------|----------|
| Starting point | Blank board, user builds everything | AI generates a complete task graph from a goal description |
| Structure | Flat lists or kanban columns — no dependency tracking | DAG with explicit dependencies, parallel paths, and convergence nodes |
| Intelligence | None — static containers | Adaptive AI that understands goal domains and generates dependency graphs |
| Progress visibility | Manual status tracking | Game-like unlock mechanic — completing tasks visually unlocks dependents |
| Ongoing help | None | AI assists with individual tasks and adapts the plan |
| Goal continuity | Isolated projects | Cross-goal memory and follow-up suggestions |
| User effort | High — user must know how to plan | Low — user describes the outcome, AI handles the planning |

---

## Target Users

### Primary

- **Individuals** planning personal projects, life changes, learning goals, or creative endeavors
- **Freelancers and solopreneurs** who need to plan and execute without a team to delegate planning to

### Secondary (future)

- **Small teams** looking for a fast way to go from idea to actionable plan
- **Coaches and mentors** who want to give clients structured action plans

---

## Task Model

Tasks use **progressive metadata** — starting minimal and growing richer as context demands:

**Always present:**
- Title
- Description
- Status (`not_started` / `in_progress` / `done`)
- Dependencies (which tasks must be completed first)
- `is_goal_node` flag (exactly one per board — the final goal completion task)

**AI-suggested when relevant:**
- Due date — for goals with hard deadlines (moves, launches, exams)
- Priority (low / medium / high) — when tasks compete for limited time/resources
- Estimated time — for goals where time management matters
- Subtasks — when a task is complex enough to break down further

The AI decides which metadata to include per-task based on the goal type. A "plan a wedding" graph gets due dates on everything. A "learn to paint" graph might have none.

---

## Business Model

### MVP Phase

Everything free. No payment infrastructure. Focus on validating the core loop (goal → questions → board → execution → follow-up).

### Post-MVP Tiers

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | Limited active boards (e.g., 2), basic AI assistance |
| **Pro** | TBD | Unlimited boards, full AI assistance, board history, export, cross-goal intelligence |
| **Team** | TBD | Shared boards, real-time collaboration, team-level insights |

---

## Technical Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React + TypeScript |
| **State / Data Fetching** | React Query (TanStack Query) |
| **DAG Visualization** | React Flow (`@xyflow/react`) + dagre (auto-layout) |
| **Backend** | FastAPI (Python) |
| **Database** | PostgreSQL |
| **AI Framework** | LangChain / LangGraph |
| **AI Providers** | OpenRouter (multi-provider access to GPT-4o, Claude, Llama, etc.) |
| **API Contract** | OpenAPI spec with code generation (frontend types + API client auto-generated from backend schema) |
| **Auth** | Email + password (session or JWT-based) |

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                   │
│  React Query ←→ Auto-generated API Client (OpenAPI)  │
└──────────────────────┬──────────────────────────────┘
                       │ REST / HTTP
┌──────────────────────▼──────────────────────────────┐
│                  Backend (FastAPI)                    │
│                                                      │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │ Auth     │  │ Board     │  │ AI Service       │  │
│  │ Service  │  │ Service   │  │ (LangChain/      │  │
│  │          │  │           │  │  LangGraph)       │  │
│  └──────────┘  └───────────┘  └────────┬─────────┘  │
│                                        │             │
└───────────┬────────────────────────────┼─────────────┘
            │                            │
   ┌────────▼────────┐        ┌─────────▼──────────┐
   │   PostgreSQL    │        │   OpenRouter API   │
   │                 │        │   (LLM providers)  │
   └─────────────────┘        └────────────────────┘
```

### Key Technical Decisions

**OpenAPI Code Generation** — the backend defines the API contract via OpenAPI (auto-generated by FastAPI). The frontend consumes this spec to auto-generate TypeScript types and an API client. This eliminates type drift between frontend and backend and reduces boilerplate.

**LangChain / LangGraph** — provides structured LLM orchestration for:
- Multi-step goal understanding (question generation → follow-ups → board generation)
- Stateful conversations during task assistance
- Tool use (if the AI needs to look things up, calculate timelines, etc.)

**OpenRouter** — single API gateway to multiple LLM providers. Enables switching models without code changes, A/B testing different models, and falling back if a provider is down.

**React Flow + dagre** — React Flow provides the interactive graph canvas (pan, zoom, custom nodes, minimap) and dagre computes the automatic top-to-bottom hierarchical layout. Together they render the DAG without requiring users to manually position nodes.

**React Query** — handles server state, caching, optimistic updates (important for task status transitions and graph interactions), and background refetching.

### Data Model (Core Entities)

```
User
├── id (UUID)
├── email
├── password_hash
├── created_at
└── updated_at

Goal
├── id (UUID)
├── user_id (FK → User)
├── title
├── original_input (raw user text)
├── status (input | classifying | questioning | answered | generating | active | completed | archived)
├── ai_context (JSON — classification, questions, answers, used for cross-goal intelligence)
├── created_at
└── updated_at

Board
├── id (UUID)
├── goal_id (FK → Goal, unique — one board per goal)
├── title
├── created_at
└── updated_at

Task
├── id (UUID)
├── board_id (FK → Board)
├── title
├── description
├── status (not_started | in_progress | done)
├── is_goal_node (boolean — exactly one per board, the DAG sink)
├── due_date (nullable)
├── priority (nullable: low | medium | high)
├── estimated_minutes (nullable)
├── created_at
└── updated_at

TaskDependency (junction table — directed edges in the DAG)
├── id (UUID)
├── dependent_task_id (FK → Task — the blocked task)
├── dependency_task_id (FK → Task — the prerequisite)
├── created_at
└── unique constraint on (dependent_task_id, dependency_task_id)

Subtask
├── id (UUID)
├── task_id (FK → Task)
├── title
├── completed (boolean)
├── position (varchar — fractional index string for ordering)
├── created_at
└── updated_at

Conversation
├── id
├── goal_id (FK → Goal)
├── task_id (nullable FK → Task — if conversation is about a specific task)
├── phase (questioning | execution)
├── messages (JSON array of {role, content, timestamp})
├── created_at
└── updated_at
```

### AI Pipeline

```
User Input (goal text)
       │
       ▼
┌─────────────────────┐
│  Goal Classification │ ← Determine domain, complexity, key dimensions
└──────────┬──────────┘  ← Reject if confidence < threshold (too vague)
           ▼
┌─────────────────────┐
│  Question Generation │ ← Generate 3-7 adaptive questions as form fields
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Answer Collection   │ ← User fills dynamic form (+ optional 1 follow-up round)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Board Generation    │ ← Generate flat task list with dependency edges (DAG)
└──────────┬──────────┘  ← Validate: no cycles, single goal node, valid DAG
           ▼
┌─────────────────────┐
│  Execution Support   │ ← Ongoing: task help, adaptation, follow-ups
└─────────────────────┘
```

Each step is a LangGraph node with structured output (JSON schemas for tasks, dependencies, questions, etc.) to ensure the AI output is parseable and consistently structured. The board generation node produces a flat list of tasks with `depends_on` arrays forming a DAG, not column-grouped tasks.

---

## Platform Strategy

**Phase 1: Web application** — React SPA, responsive design that works on mobile browsers but optimized for desktop.

**Phase 2: PWA / Mobile** — add PWA capabilities for offline access and mobile home screen install. Evaluate native mobile apps based on demand.

---

## Collaboration (Future)

Single-user only for MVP. Team features planned for the Team tier post-MVP:

- Shared task graphs with role-based access
- Real-time collaborative editing (WebSocket-based)
- Assignment of tasks to team members
- Team-level goal tracking and insights

---

## MVP Scope

The MVP includes all three phases of the core loop:

| Feature | Included in MVP |
|---------|:-:|
| Free-text goal input | Yes |
| Adaptive AI questioning (dynamic form) | Yes |
| AI graph generation (DAG with dependency edges) | Yes |
| Task status management with unlock mechanic | Yes |
| Task detail editing (title, description, metadata, subtasks) | Yes |
| DAG visualization with React Flow + dagre auto-layout | Yes |
| Goal node with progress tracking + celebration on completion | Yes |
| AI task guidance (ask AI for help on a task) | Yes |
| Progress adaptation (AI adjusts graph based on changes) | Yes |
| Blocker resolution (AI breaks down stuck tasks) | Yes |
| Goal completion + follow-up suggestions | Yes |
| Cross-goal context / memory | Yes |
| Unlimited active boards | Yes |
| Email + password auth | Yes |
| Manual dependency editing by users | No (AI-only for MVP) |
| Payment / subscriptions | No |
| Team collaboration | No |
| Real-time multi-user editing | No |
| Native mobile apps | No |
| Export / import | No |

---

## Success Metrics

| Metric | What it measures |
|--------|-----------------|
| **Activation rate** | % of signups who complete questioning and generate a board |
| **Board quality** | % of generated tasks that users keep (vs. delete immediately) |
| **Task completion rate** | Average tasks completed per board |
| **AI assistance usage** | % of users who engage AI for task help during execution |
| **Goal completion rate** | % of generated goals that reach "done" |
| **Follow-up rate** | % of users who start a new goal after completing one |
| **Retention (D7 / D30)** | Users returning to work on boards within 7 / 30 days |

---

## Deployment (TBD)

Hosting strategy to be decided. Candidates:

- **Vercel + Railway/Render** — Vercel for frontend static hosting, Railway or Render for FastAPI backend + managed Postgres
- **AWS** — ECS/Fargate for backend, RDS for Postgres, CloudFront + S3 for frontend
- **VPS** — Hetzner or DigitalOcean with Docker Compose for simpler self-managed setup

Decision will be made based on cost, scaling needs, and operational complexity once the MVP is ready to deploy.

---

## Open Questions

- What model(s) should be the default via OpenRouter? Cost vs. quality tradeoff for different pipeline stages (classification might use a cheaper model, board generation needs a stronger one).
- How should board versioning work? Should users be able to "undo" AI-generated changes or revert to a previous graph state?
- What's the right limit for free-tier boards post-MVP?
- Should the AI proactively reach out (notifications/reminders) or only respond when asked?
- When should manual dependency editing be added? What's the right UX for users to add/remove edges in the DAG?
- How to handle AI-generated DAGs that are too linear (not enough parallelism) or too wide (overwhelming number of parallel paths)?
