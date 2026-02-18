## Phase 1: Extract utilities and shared modules (non-breaking)

- [x] 1.1 Create `app/core/types.py` — move `BoardSkeletonOutput`, `BoardSkeletonTaskOutput`, `TaskEnrichmentOutput`, `SubtaskOutput` from `ai/schemas.py`; add re-exports in `ai/schemas.py` for backward compatibility
- [x] 1.2 Create `app/domains/boards/position_utils.py` — extract `_midpoint()`, `_midpoint_after()`, `generate_position_between()`, `generate_position_after()` from `boards/service.py`; add re-exports in `boards/service.py`
- [x] 1.3 Create `app/domains/boards/ownership.py` — extract `_validate_board_ownership()`, `_validate_task_ownership()`, `_validate_subtask_ownership()` from `boards/service.py`; make them public functions
- [x] 1.4 Create `app/domains/ai/llm.py` — extract shared `get_llm()` factory function; update `nodes/classify.py`, `nodes/enrich_task.py`, `nodes/generate_board.py`, `nodes/questions.py` to import from `ai/llm.py`
- [x] 1.5 Create `app/domains/ai/graphs/base.py` — extract `should_continue()`, `execute_tools()`, `_extract_field()` from `graphs/chat.py`; update both `graphs/chat.py` and `graphs/board_chat.py` to import from `base.py`
- [x] 1.6 Run tests to verify no regressions

## Phase 2: Create repository layer

- [x] 2.1 Create `app/domains/auth/repository.py` — `UserRepository` class with `get_by_email()`, `get_by_id()`, `create()`
- [x] 2.2 Update `app/domains/auth/service.py` to use `UserRepository` instead of direct session queries
- [x] 2.3 Create `app/domains/goals/repository.py` — `GoalRepository` class with `get_by_id()`, `get_for_user()`, `create()`, `update_status()`, `update_ai_context()`
- [x] 2.4 Update `app/domains/goals/service.py` to use `GoalRepository`
- [x] 2.5 Create `app/domains/boards/board_repository.py` — `BoardRepository` class with `get_by_id()`, `get_by_goal_id()`, `create()`, `update()`, `list_by_user()`, `get_with_relations()`
- [x] 2.6 Create `app/domains/boards/task_repository.py` — `TaskRepository` class with `get_by_id()`, `create()`, `update()`, `delete()`, `get_dependencies()`, `get_dependents()`, `are_dependencies_met()`, `create_dependency()`, `delete_dependencies_for_task()`
- [x] 2.7 Create `app/domains/boards/subtask_repository.py` — `SubtaskRepository` class with `get_by_id()`, `create()`, `update()`, `delete()`, `get_last_position()`
- [x] 2.8 ~~Create `app/domains/ai/repositories.py`~~ — SKIPPED: memory.py and pending_actions.py are already well-structured; adding repos would be pure boilerplate
- [x] 2.9 Run tests to verify no regressions

## Phase 3: Split services and move logic

- [x] 3.1 Create `app/domains/boards/board_service.py` — move board CRUD, list, response building (`build_board_response`, `format_qa_pairs`, `list_boards`, `get_board`, `get_board_by_goal`, `update_board`, `get_user_meta_for_board`) from `boards/service.py`; update to use `BoardRepository`
- [x] 3.2 Create `app/domains/boards/task_service.py` — move task CRUD, status validation, dependency logic, board generation orchestration (`create_task`, `update_task`, `_validate_status_transition`, `delete_task`, `create_board_from_skeleton`, `update_task_with_enrichment`, `validate_goal_for_generation`, `generate_board`) from `boards/service.py`; update to use `TaskRepository`
- [x] 3.3 Create `app/domains/boards/subtask_service.py` — move subtask CRUD (`create_subtask`, `update_subtask`, `delete_subtask`) from `boards/service.py`; update to use `SubtaskRepository`
- [x] 3.4 Move goal state transitions to `goals/service.py` — add `transition_goal_to_generating()`, `transition_goal_to_active()`, `revert_goal_to_answered()` functions; `boards/task_service.py` calls these instead of modifying Goal directly
- [x] 3.5 Move board generation orchestration from `boards/router.py::generate_board_endpoint` body into `boards/task_service.py::generate_board()` — router is now thin HTTP wrapper
- [x] 3.6 Update `boards/router.py` — replaced all `boards.service` imports with `boards.board_service`, `boards.task_service`, `boards.subtask_service`; uses `boards.ownership` for validation
- [x] 3.7 Replace `boards/service.py` with backward-compat re-export shim (external consumers still import from here until Phase 4)
- [x] 3.8 Run tests (20/20 pass), verify all imports work, no circular dependencies

## Phase 4: Clean up AI domain

- [x] 4.1 Update `ai/pending_actions.py` — import `are_dependencies_met` from `boards/task_service` instead of `boards/service`. Full delegation of `_execute_*` handlers deferred (they do custom low-level DB operations with different return semantics than the board service functions).
- [x] 4.2 Move inline schema classes from `ai/router.py` (`TaskChatRequest`, `BoardChatRequest`, `TaskChatResponse`, `ActionConfirmResponse`) to `ai/schemas.py`
- [x] 4.3 Kept `_validate_board_ownership()` in `ai/router.py` — it's a router-level helper that raises HTTPException directly and returns (board, goal) tuple; NOT the same as `boards.ownership.validate_board_ownership`. Added docstring clarification.
- [x] 4.4 Deleted `ai/pipeline.py` (dead code — never imported)
- [x] 4.5 Updated `ai/service.py` to import cross-domain types from `core/types.py`
- [x] 4.6 All key modules already had `__all__` exports from Phase 1/2
- [x] 4.7 Removed backward-compatibility re-exports from `ai/schemas.py`; updated all consumers (`ai/nodes/generate_board.py`, `ai/nodes/enrich_task.py`, `tests/conftest.py`) to import from `core/types.py`. Also updated `tests/conftest.py` and `tests/.../test_fractional_indexing.py` to import from canonical locations. Updated `ai/tools/mutations.py` imports.
- [x] 4.8 Run tests (20/20 pass), all imports verified, app loads successfully

## Phase 5: Final verification

- [x] 5.1 Full test suite: 33/33 unit tests pass. DB-dependent tests (136) fail with pre-existing `pgvector` infrastructure issue (`type "vector" does not exist`) — not introduced by this refactoring.
- [x] 5.2 `ruff check` — all checks passed. `ruff format --check` — 114 files already formatted.
- [x] 5.3 pyright — no new type errors introduced. All LSP errors are pre-existing (SQLAlchemy type stubs, langchain type stubs).
- [x] 5.4 No circular imports: `python -c "from app.main import app"` succeeds.
- [x] 5.5 API contract unchanged — router endpoints are identical, only internal imports changed. No endpoint, schema, or behavior modifications.
- [x] 5.6 Update `openspec/project.md` backend structure section to reflect new file layout
