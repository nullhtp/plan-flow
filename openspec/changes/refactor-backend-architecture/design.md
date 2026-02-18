## Context
The backend has grown to ~4,500 lines of Python across 4 domains. While the domain-based layout is sound, several modules have accumulated multiple responsibilities, duplication exists across domains, and circular dependencies between `boards` and `ai` are managed through brittle lazy imports. This refactoring restructures the backend internals without changing any external API behavior.

**Stakeholders:** Solo developer + AI assistants. No external API consumers are affected since all endpoints, schemas, and behavior remain identical.

## Goals / Non-Goals

### Goals
- **Single Responsibility:** Every module has one clear reason to change
- **Repository Pattern:** Separate DB access from business logic in services
- **DRY:** Eliminate all identified code duplication (~400+ lines)
- **Clean domain boundaries:** No circular imports; clear dependency direction
- **Logical file structure:** Files named and organized by what they contain
- **Testability:** Repository layer enables unit testing services without DB

### Non-Goals
- Changing any API endpoint, request/response schema, or behavior
- Introducing new abstractions (DI containers, event buses, CQRS)
- Optimizing query performance (N+1, O(n^2) computations) — separate concern
- Adding new features or capabilities
- Changing the test framework or test patterns
- Frontend changes of any kind

## Decisions

### Decision 1: Split boards/service.py by entity, not by concern
**What:** Create `board_service.py`, `task_service.py`, `subtask_service.py` instead of `crud.py`, `validation.py`, `generation.py`.

**Why:** Entity-based splitting maps naturally to the domain model. Each service file is cohesive — all operations on a task live together. Concern-based splitting scatters related logic across files.

**Alternatives considered:**
- Concern-based split (`crud.py`, `validation.py`, `generation.py`): Creates artificial boundaries that fragment related logic. A task status update requires reading validation + crud.
- Keep single file: Already at 865 lines and growing. Unsustainable.

### Decision 2: Repository pattern with thin repository classes
**What:** Each domain gets repository classes that encapsulate SQLAlchemy queries. Services call repositories, never use `session.execute()` directly.

**Why:** Separates data access from business logic. Enables unit testing services with mock repositories. Makes query logic reusable and discoverable.

**Pattern:**
```python
# boards/board_repository.py
class BoardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, board_id: UUID) -> Board | None: ...
    async def get_by_goal_id(self, goal_id: UUID) -> Board | None: ...
    async def create(self, board: Board) -> Board: ...
    async def list_by_user(self, user_id: UUID) -> list[Board]: ...
```

**Alternatives considered:**
- No repositories (current state): Mixes SQL queries with business logic. Services are 500+ lines partly because of query boilerplate.
- Generic repository base class: Over-engineered for this codebase size. Each entity has different query patterns.

### Decision 3: Extract shared types to `core/types.py`
**What:** Move `BoardSkeletonOutput`, `TaskEnrichmentOutput`, and other cross-domain Pydantic schemas from `ai/schemas.py` to `core/types.py`.

**Why:** These types are consumed by both `ai` and `boards` domains. Placing them in `core/` eliminates the circular dependency (both domains import from core, neither imports from the other's schemas).

**Alternatives considered:**
- Protocol/interface pattern: More SOLID but adds complexity for types that are simple data containers. Protocols make sense for behavior, not data transfer objects.
- Keep in `ai/schemas.py` with lazy imports: Current approach. Works but produces fragile import chains.

### Decision 4: Extract shared graph utilities to `ai/graphs/base.py`
**What:** Move duplicated `should_continue()`, `execute_tools()`, `_extract_field()` from `chat.py` and `board_chat.py` into a shared `base.py` module.

**Why:** ~200 lines of identical code across two files. Any bug fix must be applied twice. The shared functions have identical signatures and behavior.

**Alternatives considered:**
- Single parameterized graph: Merging both graphs into one function with a mode parameter couples task chat and board chat evolution. They may diverge in the future.
- Leave as-is: Active maintenance cost. Bug fixes must be synchronized.

### Decision 5: Extract shared LLM factory to `ai/llm.py`
**What:** Create `ai/llm.py` with `get_llm(model: str | None = None)` that replaces the 4 duplicated `_get_llm()` functions across node files.

**Why:** Identical 5-line function copied 4 times. Single point of change for LLM configuration.

### Decision 6: Goal state transitions move to goals domain
**What:** Move `transition_goal_to_generating()`, `transition_goal_to_active()`, `revert_goal_to_answered()` from `boards/service.py` to `goals/service.py`.

**Why:** Goal is the domain entity. Its state machine should be owned by its domain. Boards domain should request a transition, not perform it directly.

### Decision 7: Pending actions delegate to boards service
**What:** `ai/pending_actions.py` calls `boards/task_service.py` and `boards/subtask_service.py` for mutations instead of reimplementing status transition validation and task deletion.

**Why:** Single source of truth for business rules. Currently, two codepaths can diverge (and already have subtle differences).

### Decision 8: Move board generation orchestration to service layer
**What:** Extract the 180-line `generate_board_endpoint` logic from `boards/router.py` into `boards/task_service.py::generate_board()`.

**Why:** Router should be thin HTTP layer. Business orchestration (calling AI, persisting skeleton, running enrichment, managing state transitions) belongs in the service layer.

## Target File Structure

```
backend/app/
├── main.py
├── core/
│   ├── config.py          # Settings (unchanged)
│   ├── db.py              # Engine, session (unchanged)
│   ├── deps.py            # Shared FastAPI dependencies (unchanged)
│   ├── security.py        # JWT, passwords (unchanged)
│   ├── types.py           # Cross-domain Pydantic schemas (NEW)
│   └── exceptions.py      # Shared exception base classes (NEW, optional)
├── domains/
│   ├── auth/
│   │   ├── models.py      # (unchanged)
│   │   ├── schemas.py     # (unchanged)
│   │   ├── repository.py  # (NEW) User DB queries
│   │   ├── service.py     # (updated) Uses repository
│   │   ├── deps.py        # (unchanged)
│   │   └── router.py      # (unchanged)
│   ├── goals/
│   │   ├── models.py      # (unchanged)
│   │   ├── schemas.py     # (unchanged)
│   │   ├── repository.py  # (NEW) Goal DB queries
│   │   ├── service.py     # (updated) +goal state transitions, uses repository
│   │   └── router.py      # (unchanged)
│   ├── boards/
│   │   ├── models.py          # (unchanged)
│   │   ├── schemas.py         # (unchanged)
│   │   ├── dag_utils.py       # (unchanged)
│   │   ├── position_utils.py  # (NEW) Fractional indexing extracted from service.py
│   │   ├── ownership.py       # (NEW) Ownership validation, shared by boards + ai
│   │   ├── board_repository.py  # (NEW) Board DB queries
│   │   ├── task_repository.py   # (NEW) Task + TaskDependency DB queries
│   │   ├── subtask_repository.py # (NEW) Subtask DB queries
│   │   ├── board_service.py   # (NEW) Board CRUD + list + response building
│   │   ├── task_service.py    # (NEW) Task CRUD + status validation + board generation
│   │   ├── subtask_service.py # (NEW) Subtask CRUD
│   │   └── router.py         # (updated) Thin HTTP layer, delegates to services
│   └── ai/
│       ├── models.py      # (unchanged)
│       ├── schemas.py     # (updated) +inline schemas moved here, -cross-domain types moved to core
│       ├── llm.py         # (NEW) Shared LLM factory
│       ├── lang_utils.py  # (unchanged)
│       ├── service.py     # (updated) Uses core/types.py
│       ├── checkpointer.py # (unchanged)
│       ├── memory.py      # (unchanged)
│       ├── pending_actions.py # (updated) Delegates to boards services
│       ├── router.py      # (updated) Thin HTTP, no inline schemas, no duplicated validation
│       ├── nodes/
│       │   ├── classify.py       # (updated) Uses ai/llm.py
│       │   ├── enrich_task.py    # (updated) Uses ai/llm.py
│       │   ├── generate_board.py # (updated) Uses ai/llm.py
│       │   └── questions.py      # (updated) Uses ai/llm.py
│       ├── prompts/       # (unchanged)
│       ├── graphs/
│       │   ├── base.py          # (NEW) Shared graph utilities
│       │   ├── chat.py          # (updated) Uses base.py
│       │   └── board_chat.py    # (updated) Uses base.py
│       └── tools/         # (unchanged except pending_actions delegation)
```

**Removed files:**
- `boards/service.py` — replaced by `board_service.py`, `task_service.py`, `subtask_service.py`
- `ai/pipeline.py` — dead code, never imported

## Risks / Trade-offs

### Risk: Large number of files changed simultaneously
**Mitigation:** Implementation in ordered phases. Each phase is independently testable. Tests run after each phase to catch regressions.

### Risk: Import path changes break existing code
**Mitigation:** Phase 1 creates new modules and re-exports from old locations. Phase 2 updates all consumers. Phase 3 removes re-exports.

### Risk: Repository pattern adds boilerplate
**Mitigation:** Repositories are thin — just query encapsulation, no generic base class overhead. Each repository class is 30-80 lines. The net effect is fewer lines in service files, not more total code.

### Trade-off: More files, smaller modules
**Accept:** More files is a feature, not a bug. Each file is <200 lines with a single responsibility. Navigation by filename is easier than scrolling through 865-line files.

## Migration Plan

### Phase 1: Extract utilities and create new modules (non-breaking)
Create `position_utils.py`, `ownership.py`, `core/types.py`, `ai/llm.py`, `ai/graphs/base.py`. Old locations re-export for backward compatibility.

### Phase 2: Create repository layer
Add repository classes. Update services to use repositories. No behavior change.

### Phase 3: Split services and move logic
Split `boards/service.py` into entity services. Move goal transitions. Move board generation orchestration. Update all imports.

### Phase 4: Clean up AI domain
Update pending_actions delegation. Remove inline schemas. Remove duplicated validation. Remove dead pipeline.py.

### Phase 5: Update tests and verify
Update test imports. Run full test suite. Verify no behavior changes.

### Rollback
Each phase can be reverted independently via git. No database migrations involved. No API changes. Rollback = `git revert`.

## Open Questions
None — all decisions were confirmed via user input before proposal creation.
