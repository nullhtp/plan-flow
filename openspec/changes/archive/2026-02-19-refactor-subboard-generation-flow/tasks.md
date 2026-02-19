## 1. Backend: New SSE endpoint for sub-board generation
- [x] 1.1 Add `POST /api/tasks/{task_id}/generate-sub-board/stream` endpoint in `boards/router.py` that returns `StreamingResponse` with `text/event-stream` content type
- [x] 1.2 Implement the streaming orchestrator logic: validate ownership/nesting/existing sub-board, resolve context, delete subtasks, auto-start parent task, then pipe `generate_sub_board_stream()` events through a persistence layer (skeleton -> persist board, enrichment -> persist enrichment) and forward SSE events to client
- [x] 1.3 Emit the same event types as main board generation: `skeleton_ready` (with `board_id`, `board_title`, `tasks`), `task_enriched` (with `task_id`, `title`), `generation_complete` (with `board_id`, `failed_tasks`), `generation_error` (with `error`)
- [x] 1.4 Handle reconnection case: if sub-board already partially exists, return 409
- [x] 1.5 Verify endpoint works with manual testing (curl or similar)

## 2. Frontend: Generalize generation progress components
- [x] 2.1 Refactor `useBoardGenerationStream` hook to accept a configurable SSE URL instead of hardcoding the goal-based endpoint path
- [x] 2.2 Refactor `BoardGenerationProgress` component to accept the SSE URL and optional `onComplete(boardId)` callback instead of hardcoding auto-navigation to `/boards/:id`
- [x] 2.3 Verify main board generation still works correctly after refactoring

## 3. Frontend: Sub-board expansion route and page
- [x] 3.1 Create route file `frontend/src/routes/boards.$boardId.expand.$taskId.tsx` with auth guard
- [x] 3.2 Implement page state machine with states: `loading-questions`, `questions`, `generating`, `error`
- [x] 3.3 In `loading-questions` state: call `POST /api/tasks/:id/sub-board-questions`, show loading spinner with context header (task title, parent board name)
- [x] 3.4 In `questions` state: render full-size question fields (reuse shared `QuestionFieldWrapper`, `OptionField`, `MultiselectOptionField` without `compact` prop) in a centered card layout, with task title as heading and "Expanding task from [Board Name]" as subtitle
- [x] 3.5 In `generating` state: render the generalized `BoardGenerationProgress` component pointing to the new SSE endpoint (`/api/tasks/:id/generate-sub-board/stream`)
- [x] 3.6 On generation complete: auto-navigate to `/boards/:subBoardId` after 1.5s delay
- [x] 3.7 Add route guards: redirect to `/boards/:existingSubBoardId` if task already has a sub-board, redirect to board page if task not found or nesting depth exceeded
- [x] 3.8 Handle error states: question loading failure shows retry, generation failure shows retry/back buttons

## 4. Frontend: Update TaskDetailPanel navigation
- [x] 4.1 Change "Expand to Board" button in `TaskDetailPanel` to navigate to `/boards/$boardId/expand/$taskId` instead of toggling inline `SubBoardCreationFlow`
- [x] 4.2 Keep the subtask confirmation dialog before navigation (if task has subtasks, show dialog, then navigate on confirm)
- [x] 4.3 Remove or deprecate the `SubBoardCreationFlow` component and related inline state management from `TaskDetailPanel`

## 5. Spec updates and validation
- [x] 5.1 Update `board-ui` spec to reflect the new route-based expansion flow
- [x] 5.2 Update `board-generation-progress` spec to cover sub-board SSE streaming
- [x] 5.3 Run `openspec validate` to confirm specs are consistent
