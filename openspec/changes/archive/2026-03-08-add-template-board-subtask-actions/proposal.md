# Change: Generate AI actions for subtasks when a board is created from a template

## Why
When boards are created via the AI pipeline, every subtask gets AI-generated action buttons (research, generate, analyze, etc.) that let users trigger contextual AI help. However, boards created from templates skip this step entirely — subtasks are copied with only title, completed, and position. This makes template-created boards feel less capable than AI-generated ones, missing a key productivity feature.

## What Changes
- **Add a background AI action generation step** to the `create_board_from_template` service function. After the board is created (tasks, dependencies, subtasks copied), the system fires off parallel LLM calls (one per task) to generate `action_label`, `action_icon`, and `action_prompt` for each subtask. This runs **after** the board is returned to the user, so board creation remains fast.
- **Apply the same behavior to the `save-generated` path** when `create_board=true` — the board created via `POST /api/templates/save-generated` also gets subtask AI actions generated in the background.
- **No changes to template storage** — `TemplateSubtask` model stays as-is. Actions are generated fresh each time a board is created, keeping them context-specific and avoiding staleness.
- **Graceful degradation** — if AI action generation fails for any task, the board remains fully usable; subtasks simply won't have action buttons. Users can still trigger action generation manually via the existing `POST /api/tasks/{task_id}/subtasks/{subtask_id}/actions/generate` endpoint.

## Impact
- Affected specs: `board-templates`, `ai-task-actions`
- Affected code:
  - `backend/app/domains/templates/service.py` — `create_board_from_template()` (add background action generation)
  - `backend/app/domains/ai/service.py` — `generate_subtask_actions()` (already exists, reused)
  - `backend/app/domains/templates/router.py` — `save-generated` endpoint (ensure board path triggers actions)
  - `backend/app/domains/boards/subtask_repository.py` — batch update subtask action fields
