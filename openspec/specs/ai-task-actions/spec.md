# ai-task-actions Specification

## Purpose
TBD - created by archiving change add-task-ai-actions. Update Purpose after archive.
## Requirements
### Requirement: Subtask Action Generation Service
The system SHALL provide an async function `generate_subtask_actions(task_title: str, task_description: str, task_status: str, subtasks: list[dict], model: str | None = None) -> list[SubtaskActionOutput]` in the AI service layer. The function SHALL call the LLM with structured output using the subtask action prompt. The function SHALL receive all subtasks of a task in a single batch call. The function SHALL return a `SubtaskActionOutput` for each subtask that can be meaningfully automated by AI (e.g., research, drafting, analysis). Subtasks that cannot be automated (e.g., physical actions, in-person tasks) SHALL be returned with null action fields. The function SHALL use `AI_ACTION_SUGGEST_MODEL` (falling back to `AI_CHAT_MODEL`, then `AI_DEFAULT_MODEL`). The function SHALL NOT use LangGraph or tools — it is a single structured output LLM call.

#### Scenario: Batch action generation for mixed subtasks
- **WHEN** `generate_subtask_actions` is called with subtasks ["Draft rental agreement", "Sign documents at notary", "Research neighborhood options"]
- **THEN** it returns actions for "Draft rental agreement" (e.g., label: "Generate agreement draft", icon: "generate") and "Research neighborhood options" (e.g., label: "Research neighborhoods", icon: "research"), but no action for "Sign documents at notary" (physical task)

#### Scenario: All subtasks non-automatable
- **WHEN** `generate_subtask_actions` is called with subtasks ["Go to the store", "Meet with landlord", "Pack boxes"]
- **THEN** it returns empty/null actions for all subtasks

#### Scenario: Language matching
- **WHEN** the task title is in German "Wohnung finden" with German subtask titles
- **THEN** the returned action labels and prompts are in German

### Requirement: Subtask Action Schemas
The system SHALL define Pydantic schemas for subtask actions: `SubtaskActionOutput` with fields `subtask_title` (str, to match against the subtask), `action_label` (str | None, max 60 chars, null if not automatable), `action_icon` (str | None, one of: "generate", "research", "plan", "analyze", "summarize", "review", "compare", "create", null if not automatable), and `action_prompt` (str | None, max 500 chars, null if not automatable). `SubtaskActionsResponse` SHALL contain a field `actions` (list of `SubtaskActionOutput`).

#### Scenario: Valid subtask action structure
- **WHEN** the LLM produces subtask actions
- **THEN** each action conforms to the `SubtaskActionOutput` schema with subtask_title for matching and nullable action fields

#### Scenario: Non-automatable subtask has null fields
- **WHEN** the LLM determines a subtask "Visit the office" cannot be automated
- **THEN** the corresponding `SubtaskActionOutput` has `action_label: null`, `action_icon: null`, `action_prompt: null`

### Requirement: Subtask Action Prompt Module
The system SHALL store the subtask action system prompt in `app/domains/ai/prompts/action_suggestions.py` (repurposed from the task-level prompt). The prompt SHALL instruct the LLM to: analyze each subtask in the context of the parent task; determine if AI can meaningfully help with each subtask (research, content generation, analysis, planning, drafting); generate an action label, icon, and prompt only for automatable subtasks; return null action fields for subtasks requiring physical presence, manual work, or human interaction that AI cannot perform; use the same language as the task content; and produce diverse action types across subtasks.

#### Scenario: Prompt loaded from module
- **WHEN** the subtask action generation feature is invoked
- **THEN** the system prompt is loaded from `app/domains/ai/prompts/action_suggestions.py`

#### Scenario: Prompt produces diverse actions
- **WHEN** a task has 4 subtasks that are all automatable
- **THEN** the actions vary in icon/type (not all "generate" or all "research")

### Requirement: Single Subtask Action Generation Endpoint
The system SHALL provide a `POST /api/tasks/{task_id}/subtasks/{subtask_id}/actions/generate` endpoint that generates an action for a single newly-created subtask. The endpoint SHALL validate task ownership. The endpoint SHALL build context from the parent task (title, description, status) and the subtask title. The endpoint SHALL call the LLM to determine if the subtask is automatable and generate action fields if so. The endpoint SHALL update the subtask record with the generated action fields and return the updated subtask.

#### Scenario: Action generated for new automatable subtask
- **WHEN** a user creates a subtask "Research visa requirements" and the action generation endpoint is called
- **THEN** the subtask is updated with `action_label: "Research visa requirements"`, `action_icon: "research"`, `action_prompt: "Research the visa requirements for..."` and the updated subtask is returned

#### Scenario: No action for non-automatable subtask
- **WHEN** a user creates a subtask "Pack suitcase" and the action generation endpoint is called
- **THEN** the subtask's action fields remain null

#### Scenario: Unauthorized access
- **WHEN** a user calls the endpoint for a task they do not own
- **THEN** the endpoint returns 403 Forbidden

### Requirement: Background Subtask Action Generation for Template Boards
The system SHALL provide an async function `generate_board_subtask_actions(session: AsyncSession, board_id: str, user_id: str)` in the templates service layer (or a shared utility) that generates AI actions for all subtasks on a newly created board. The function SHALL: (1) load all tasks with their subtasks for the given board, (2) for each task that has subtasks, call `generate_subtask_actions` with the task's title, description, status, and subtask list, (3) run these calls in parallel using `asyncio.gather` with `return_exceptions=True`, (4) for each successful result, match actions to subtasks by title and update the `action_label`, `action_icon`, and `action_prompt` fields via a batch DB update, (5) resolve `user_context` from the board's goal `ai_context.user_meta` when available. The function SHALL use graceful degradation: if an LLM call fails for a particular task, that task's subtasks are skipped (no action fields set) and processing continues for other tasks. The function SHALL log errors but never raise exceptions.

#### Scenario: Actions generated for all tasks in parallel
- **WHEN** `generate_board_subtask_actions` is called for a board with 5 tasks, each having 3 subtasks
- **THEN** 5 parallel LLM calls are made (one per task)
- **AND** each subtask's `action_label`, `action_icon`, and `action_prompt` are populated based on the LLM response

#### Scenario: Partial failure does not block other tasks
- **WHEN** `generate_board_subtask_actions` is called and the LLM call for task 3 fails
- **THEN** subtasks for tasks 1, 2, 4, and 5 still receive their AI actions
- **AND** subtasks for task 3 retain null action fields
- **AND** the error is logged

#### Scenario: Tasks without subtasks are skipped
- **WHEN** a board has 3 tasks but only 2 of them have subtasks
- **THEN** only 2 LLM calls are made (tasks without subtasks are skipped)

#### Scenario: User context passed to action generation
- **WHEN** the board's goal has `ai_context.user_meta` with timezone and locale information
- **THEN** the `user_context` string is passed to `generate_subtask_actions` for each task

