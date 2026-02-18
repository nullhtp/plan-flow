## 1. Backend: Artifact Data Model & Migration
- [x] 1.1 Add `Artifact` SQLModel to `app/domains/boards/models.py` (id, task_id FK with cascade, title, content, content_type, created_by, created_at, updated_at, index on task_id)
- [x] 1.2 Create Alembic migration for the `artifact` table
- [x] 1.3 Run migration and verify table creation

## 2. Backend: Artifact Repository & Service
- [x] 2.1 Create `app/domains/boards/artifact_repository.py` with `ArtifactRepository` (create, list_by_task, get_by_id, delete, count_by_task)
- [x] 2.2 Create `app/domains/boards/artifact_service.py` with service functions (create_artifact, list_artifacts, get_artifact, delete_artifact)
- [x] 2.3 Add `ArtifactResponse`, `ArtifactListResponse` schemas to `app/domains/boards/schemas.py`
- [x] 2.4 Add `artifact_count` field to `TaskResponse` schema and update the board response builder to compute it

## 3. Backend: Artifact CRUD Endpoints
- [x] 3.1 Add artifact endpoints to `app/domains/boards/router.py`: GET list, GET single, DELETE
- [x] 3.2 Wire ownership validation for artifact endpoints using existing `ownership.py`
- [x] 3.3 Write integration tests for artifact CRUD endpoints (happy path + auth + 404)

## 4. Backend: Action Suggestion System
- [x] 4.1 Add `ActionSuggestion` and `ActionSuggestionsResponse` schemas to `app/domains/ai/schemas.py`
- [x] 4.2 Create action suggestion prompt at `app/domains/ai/prompts/action_suggestions.py`
- [x] 4.3 Add `AI_ACTION_SUGGEST_MODEL` to config settings with fallback chain
- [x] 4.4 Implement `generate_action_suggestions()` in `app/domains/ai/service.py` (single structured output LLM call)
- [x] 4.5 Add `POST /api/tasks/{task_id}/actions/suggest` endpoint to `app/domains/ai/router.py` with ownership validation and context building
- [x] 4.6 Write integration tests for action suggestion endpoint

## 5. Backend: Save Artifact Tool
- [x] 5.1 Create `make_save_artifact` tool factory in `app/domains/ai/tools/mutations.py` (immediate execution, creates Artifact record)
- [x] 5.2 Register `save_artifact` in `get_task_chat_tools()` in `app/domains/ai/tools/registry.py`
- [x] 5.3 Update task chat system prompt in `app/domains/ai/prompts/chat.py` to include `save_artifact` instructions
- [x] 5.4 Write unit test for `save_artifact` tool execution

## 6. Frontend: Regenerate API Client
- [x] 6.1 Run Orval to regenerate TypeScript types and React Query hooks from updated OpenAPI spec
- [x] 6.2 Verify new types are generated: `ActionSuggestion`, `ActionSuggestionsResponse`, `ArtifactResponse`, `ChatResponse`, `ToolAction`, `ActionConfirmResponse`

## 7. Frontend: AI Actions Component
- [x] 7.1 Create `TaskAiActions` component in `src/features/board/components/` (fetches suggestions on mount, displays 2-4 action buttons in grid, refresh button, loading skeleton, error state)
- [x] 7.2 Create `useActionSuggestions(taskId)` hook in `src/features/board/hooks/` (React Query wrapper for POST /api/tasks/{task_id}/actions/suggest)
- [x] 7.3 Map `icon` hint to appropriate Lucide icons (generate, research, plan, analyze, summarize, review, compare, create)

## 8. Frontend: Artifacts Section Component
- [x] 8.1 Create `TaskArtifacts` component in `src/features/board/components/` (list artifacts, expand/collapse content, copy button, delete button with confirmation)
- [x] 8.2 Create `useArtifacts(taskId)` and `useDeleteArtifact()` hooks in `src/features/board/hooks/`
- [x] 8.3 Add markdown rendering for artifact content (use existing markdown renderer or add `react-markdown` dependency)

## 9. Frontend: Chat Section Component
- [x] 9.1 Create `TaskChat` component in `src/features/board/components/` (message list, input field, loading state, empty state placeholder)
- [x] 9.2 Create `useTaskChat(taskId)` hook in `src/features/board/hooks/` (manages local message state, calls POST /api/tasks/{task_id}/chat, appends responses)
- [x] 9.3 Create `ChatMessage` component for rendering individual messages (user vs AI, markdown formatting)
- [x] 9.4 Create `ToolActionCard` component for rendering inline tool action cards (tool name, description, status badge)
- [x] 9.5 Create `PendingActionCard` component with Confirm/Reject buttons (calls POST /api/actions/{id}/confirm or reject)
- [x] 9.6 Add board query invalidation after chat responses with executed tool actions or confirmed pending actions
- [x] 9.7 Add artifacts query invalidation after chat responses with `save_artifact` tool action

## 10. Frontend: Integrate into TaskDetailPanel
- [x] 10.1 Add AI Actions section to TaskDetailPanel after Subtasks section
- [x] 10.2 Add Artifacts section after AI Actions section
- [x] 10.3 Add Chat section at the bottom of the panel
- [x] 10.4 Wire action button clicks to send prompts to the chat component
- [x] 10.5 Ensure panel scrolls to chat section when an action is clicked

## 11. Testing & Polish
- [x] 11.1 Manual E2E test: open task → see action suggestions load → click action → chat sends message → AI responds → artifact created → artifact visible in Artifacts section
- [x] 11.2 Test action suggestions for tasks in different statuses (not_started, in_progress, done)
- [x] 11.3 Test action suggestions for non-English tasks
- [x] 11.4 Test pending action confirm/reject flow via chat
- [x] 11.5 Verify board DAG updates after AI tool mutations
