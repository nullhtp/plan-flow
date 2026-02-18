# Change: Refactor backend to domain-driven architecture with SOLID, KISS, and DRY principles

## Why
The backend has grown organically and accumulated significant structural debt: `boards/service.py` is 865 lines with 7+ responsibilities, `boards/router.py` has a 180-line endpoint, there are ~200 lines of duplicated code between graph files, circular dependencies between `boards` and `ai` domains managed via lazy imports, business logic duplication across `ai/pending_actions.py` and `boards/service.py`, goal state transitions living in the wrong domain, dead code, and inline schemas. This refactoring enforces clean domain boundaries, introduces a repository layer for DB access separation, eliminates duplication, and produces a file structure where each module has a single clear responsibility.

## What Changes

### 1. Split `boards/service.py` (865 lines) into entity-focused modules
- `boards/board_service.py` — Board CRUD + list + response building
- `boards/task_service.py` — Task CRUD + status validation + board generation orchestration
- `boards/subtask_service.py` — Subtask CRUD
- `boards/position_utils.py` — Fractional indexing utilities (extracted)
- `boards/ownership.py` — Ownership validation (extracted, shared across services)

### 2. Introduce repository layer per domain
- Each domain gets repository classes that encapsulate all DB queries
- Services contain business logic only, calling repositories for data access
- `boards/board_repository.py`, `boards/task_repository.py`, `boards/subtask_repository.py`
- `goals/repository.py`, `auth/repository.py`, `ai/repositories.py`

### 3. Move goal state transitions to goals domain
- `transition_goal_to_generating()`, `transition_goal_to_active()`, `revert_goal_to_answered()` move from `boards/service.py` to `goals/service.py`
- Boards service calls goals service for state transitions

### 4. Extract shared types to break circular dependencies
- Create `core/types.py` for cross-domain types (`BoardSkeletonOutput`, `TaskEnrichmentOutput`, etc.)
- AI and boards domains import from `core/types.py` instead of from each other

### 5. DRY the AI domain
- Extract `ai/graphs/base.py` with shared `should_continue()`, `execute_tools()`, `_extract_field()` from duplicated graph code
- Extract `ai/llm.py` with shared `get_llm()` factory (duplicated across 4 node files)
- `ai/pending_actions.py` delegates to boards service instead of reimplementing business logic

### 6. Move generate_board orchestration from router to service
- Extract the 180-line `generate_board_endpoint` logic into `boards/task_service.py` as `generate_board()`
- Router becomes a thin HTTP/SSE layer

### 7. Dead code and housekeeping cleanup
- Remove unused `ai/pipeline.py` (89 lines, never imported)
- Move inline schema classes from `ai/router.py` to `ai/schemas.py`
- Remove duplicated `_validate_board_ownership()` from `ai/router.py` (use `boards/ownership.py`)
- Add `__all__` exports to key modules

## Impact
- Affected specs: `backend-scaffolding`, `board-management`, `goal-management`, `ai-pipeline`, `ai-tools`, `task-dag`
- Affected code: All files under `backend/app/domains/` and `backend/app/core/`
- No API contract changes — all endpoints, request/response schemas, and behavior remain identical
- Tests will need import path updates but no logic changes
- **No breaking changes** — this is a purely internal restructuring
