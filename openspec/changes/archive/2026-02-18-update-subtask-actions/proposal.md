# Change: Move AI Action Buttons from Task Level to Subtask Level

## Why

Currently, AI action buttons are generated at the task level (2-4 generic actions per task). Users need more granular, actionable help — specifically, one-click AI assistance for individual subtasks like "Draft rental agreement" or "Research watch options". Moving actions to the subtask level makes the AI assistant feel more targeted and useful, reducing the gap between seeing a subtask and getting AI help with it.

## What Changes

- **Subtask model extended**: Add nullable `action_label`, `action_icon`, `action_prompt` fields to the `Subtask` model and a new Alembic migration
- **Enrichment pipeline extended**: The task enrichment LLM call now also produces subtask action data (label, icon, prompt) for each subtask where AI automation is feasible. Subtasks that cannot be meaningfully automated get no action.
- **New subtask action generation service**: A batch LLM function `generate_subtask_actions` analyzes all subtasks of a task and returns actions for automatable ones. Used during enrichment and when new subtasks are created.
- **On-creation action generation**: When a user manually adds a subtask, an action is generated for it (if applicable) and persisted
- **Task-level action buttons removed**: The `TaskAiActions` component and `POST /tasks/{task_id}/actions/suggest` endpoint are deprecated and replaced by per-subtask inline actions
- **Subtask action UI**: Each subtask in the checklist shows an inline action button (sparkle icon) when an action is available. Clicking it sends a targeted prompt to the task chat, including subtask context.
- **Quick-reply clarification flow**: The task chat prompt is updated so the AI may ask clarifying questions using quick-reply button options before executing the subtask work, when it determines more context is needed.

## Impact

- Affected specs: `ai-task-actions`, `board-management`, `board-ui`, `ai-pipeline`, `task-chat-ui`
- Affected code:
  - `backend/app/domains/boards/models.py` (Subtask model)
  - `backend/app/core/types.py` (SubtaskOutput, TaskEnrichmentOutput)
  - `backend/app/domains/ai/prompts/action_suggestions.py` (repurposed for subtask actions)
  - `backend/app/domains/ai/prompts/enrich_task.py` (updated to include action generation)
  - `backend/app/domains/ai/service.py` (new `generate_subtask_actions` function)
  - `backend/app/domains/ai/router.py` (new endpoint for single-subtask action generation)
  - `backend/app/domains/boards/subtask_service.py` (trigger action generation on create)
  - `frontend/src/features/board/components/SubtaskChecklist.tsx` (inline action buttons)
  - `frontend/src/features/board/components/TaskAiActions.tsx` (removed)
  - `frontend/src/features/board/components/TaskDetailPanel.tsx` (remove AI Actions section)
  - `frontend/src/features/board/components/TaskChat.tsx` (quick-reply buttons)
  - New Alembic migration for subtask action fields
