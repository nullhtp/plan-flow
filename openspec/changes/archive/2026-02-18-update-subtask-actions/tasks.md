## 1. Backend: Subtask Model & Migration

- [x] 1.1 Add nullable `action_label` (varchar 60), `action_icon` (varchar 20), `action_prompt` (text, max 500) fields to the `Subtask` model in `backend/app/domains/boards/models.py`
- [x] 1.2 Create Alembic migration to add the three columns to the `subtask` table
- [x] 1.3 Update `SubtaskOutput` in `backend/app/core/types.py` to include optional `action_label`, `action_icon`, `action_prompt` fields
- [x] 1.4 Update subtask response schemas in `backend/app/domains/boards/schemas.py` to include the action fields

## 2. Backend: Subtask Action Generation Service

- [x] 2.1 Create `SubtaskActionOutput` and `SubtaskActionsResponse` Pydantic schemas in `backend/app/domains/ai/schemas.py` for the batch LLM output
- [x] 2.2 Repurpose `backend/app/domains/ai/prompts/action_suggestions.py` for subtask-level action generation (batch prompt analyzing all subtasks of a task)
- [x] 2.3 Add `generate_subtask_actions(task_title, task_description, task_status, subtasks, model=None) -> list[SubtaskActionOutput]` in `backend/app/domains/ai/service.py`
- [x] 2.4 Add `POST /api/tasks/{task_id}/subtasks/{subtask_id}/actions/generate` endpoint in AI router for on-demand single-subtask action generation (used when user creates a subtask)

## 3. Backend: Enrichment Pipeline Integration

- [x] 3.1 Update enrichment pipeline in `backend/app/domains/boards/task_service.py` to call `generate_subtask_actions` after subtasks are created during `update_task_with_enrichment`
- [x] 3.2 Persist generated action fields on the Subtask records
- [x] 3.3 Ensure action generation failure does not block enrichment (graceful degradation — subtasks are created without actions)

## 4. Backend: Manual Subtask Creation Hook

- [x] 4.1 Update `POST /api/tasks/{task_id}/subtasks` endpoint or service to trigger async action generation for the new subtask
- [x] 4.2 Add endpoint or mechanism to return the generated action to the frontend after creation (e.g., return updated subtask with action fields, or use a follow-up request)

## 5. Backend: Deprecate Task-Level Actions

- [x] 5.1 Remove or deprecate `POST /api/tasks/{task_id}/actions/suggest` endpoint
- [x] 5.2 Remove or deprecate `generate_action_suggestions` function from AI service
- [x] 5.3 Clean up the old `ActionSuggestion`/`ActionSuggestionsResponse` schemas (or keep if reused for subtask actions)

## 6. Backend: Quick-Reply Support in Chat

- [x] 6.1 Update task chat system prompt (`backend/app/domains/ai/prompts/chat.py`) to instruct the AI to ask clarifying questions with quick-reply options when executing subtask actions, using a structured JSON format
- [x] 6.2 Define the quick-reply JSON format in the chat response schema (e.g., `quick_replies: list[QuickReply]` with `label` and `value` fields)

## 7. Frontend: Subtask Action Buttons

- [x] 7.1 Update `SubtaskChecklist` component to show an inline action button (sparkle/wand icon) next to each subtask that has a non-null `action_prompt`
- [x] 7.2 Wire action button click to send the `action_prompt` (with subtask context) to the task chat
- [x] 7.3 Remove `TaskAiActions` component
- [x] 7.4 Remove the "AI Actions" section from `TaskDetailPanel`
- [x] 7.5 Update Orval types to include action fields in subtask responses
- [x] 7.6 Remove `use-action-suggestions` hook

## 8. Frontend: Quick-Reply Buttons in Chat

- [x] 8.1 Detect quick-reply options in AI chat responses
- [x] 8.2 Render clickable quick-reply buttons below the AI message
- [x] 8.3 Clicking a quick-reply button sends its value as the next chat message

## 9. Frontend: Action Generation on Subtask Creation

- [x] 9.1 After creating a subtask, call the action generation endpoint and update the subtask's action fields in the UI
- [x] 9.2 Show a loading indicator on the subtask while action is being generated

## 10. Testing

- [x] 10.1 Backend: Test subtask action generation service (batch call, empty results for non-automatable subtasks)
- [x] 10.2 Backend: Test enrichment pipeline includes action generation
- [x] 10.3 Backend: Test manual subtask creation triggers action generation
- [x] 10.4 Backend: Test deprecated task-level endpoint is removed
- [x] 10.5 Frontend: Test subtask action button rendering and click behavior
- [x] 10.6 Frontend: Test quick-reply button rendering in chat
