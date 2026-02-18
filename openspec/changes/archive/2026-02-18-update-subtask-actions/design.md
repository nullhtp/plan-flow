## Context

The existing `add-task-ai-actions` change introduced task-level AI action buttons (2-4 per task, generated on-demand). This change evolves the system to subtask-level actions: each subtask can have 0 or 1 AI action, persisted in the database, generated during board enrichment or when subtasks are created.

The change touches the AI pipeline (enrichment), data model (Subtask), backend services, and frontend UI.

## Goals / Non-Goals

- **Goals**:
  - Move action buttons from task level to subtask level (inline in the checklist)
  - Persist subtask actions in the Subtask model (no extra table)
  - Generate actions during enrichment pipeline (pre-populated for instant display)
  - Generate actions on manual subtask creation
  - Only generate actions for subtasks where AI automation is feasible
  - Support quick-reply clarification buttons in task chat when the AI needs more context
  - Remove the task-level AI Actions section from the UI

- **Non-Goals**:
  - Auto-completing subtasks (user still marks them done manually)
  - A separate question form modal (clarification happens via chat quick-reply buttons)
  - Changing the subtask data model beyond adding action fields
  - Changing how task-level chat works (the chat itself stays the same)

## Decisions

### 1. Store actions as fields on Subtask, not a separate table

- **Decision**: Add nullable `action_label` (str|null), `action_icon` (str|null), `action_prompt` (str|null) columns to the `subtask` table.
- **Why**: At most 1 action per subtask. A separate table adds JOIN complexity for zero benefit. Nullable fields clearly express "no action available".
- **Alternatives**: Separate `subtask_action` table (rejected — over-engineered for 0-or-1 relationship).

### 2. Generate actions in a single batch LLM call per task

- **Decision**: A single LLM call receives all subtasks of a task and returns actions for the automatable ones.
- **Why**: Cheaper and faster than one call per subtask. The LLM has full context of all subtasks to avoid duplicating action types.
- **Alternatives**: Per-subtask calls (rejected — N times more expensive, slower).

### 3. Integrate action generation into the enrichment pipeline

- **Decision**: After the existing enrichment call generates subtasks, a follow-up call generates actions for those subtasks. Both are part of the enrichment phase so actions are ready when the board first loads.
- **Why**: Users see actions immediately. No separate loading step.
- **Alternatives**: 
  - Combined in single enrichment prompt (rejected — enrichment already has a complex output schema; adding actions would make it unreliable).
  - Separate async background job (rejected — user may open a task before actions are ready).

### 4. Generate actions when subtasks are manually created

- **Decision**: When a user creates a subtask via the API, the backend triggers a single-subtask action generation call and persists the result. This happens asynchronously — the subtask is created immediately and the action is populated afterward.
- **Why**: New subtasks should also benefit from AI actions.
- **Alternatives**: Only generate during initial board creation (rejected — user wants actions for manually added subtasks too).

### 5. Quick-reply buttons for clarification in chat

- **Decision**: When a subtask action prompt is sent to chat, the task chat system prompt instructs the AI to ask clarifying questions using a structured format that the frontend renders as quick-reply buttons. The AI decides whether questions are needed based on subtask complexity.
- **Why**: Reduces user effort vs. typing answers. Keeps everything in the chat — no separate modal.
- **Format**: The AI includes a JSON block in its response with options. The frontend detects this and renders clickable buttons.

### 6. Deprecate task-level action suggestions

- **Decision**: Remove the `TaskAiActions` component and the `POST /tasks/{task_id}/actions/suggest` endpoint. All actions are now at the subtask level.
- **Why**: Having both levels would confuse users about where to find actions. Subtask-level is strictly more granular and useful.

## Risks / Trade-offs

- **Enrichment latency increase**: Adding a second LLM call per task during enrichment adds ~1-3 seconds per task. Mitigated by using a fast/cheap model (`AI_ACTION_SUGGEST_MODEL`) and running the call after enrichment data is persisted (subtasks exist before actions are generated).
- **LLM may not produce useful actions**: Some subtasks (e.g., "Go to the store") genuinely cannot be automated. The LLM is instructed to return empty actions for such subtasks, which is the correct behavior.
- **Quick-reply button parsing**: The frontend needs to detect and render quick-reply options from AI responses. This is a new pattern that needs reliable detection. Mitigated by using a clear JSON format with a known key.

## Open Questions

- None — all major decisions resolved via clarifying questions.
