# Change: Refactor sub-board generation to full-screen page with SSE progress

## Why
The current sub-board creation flow is crammed into the task detail side panel with compact question fields and a static spinner during generation. This provides a poor user experience compared to the main board generation flow which has a dedicated full-screen question form and real-time SSE-powered generation progress. Users deserve the same polished experience when expanding a task into a sub-board.

## What Changes
- **New route**: Add `/boards/$boardId/expand/$taskId` as a dedicated full-screen page for sub-board creation
- **Full-screen questions**: Render sub-board questions as a full-screen centered form with full-size question fields (same styling as the goal creation form), showing task title and parent board context
- **SSE generation progress**: Show real-time generation log with task stack, progress bar, and phase indicator (identical to main board generation progress view)
- **New backend SSE endpoint**: Add `POST /api/tasks/:id/generate-sub-board/stream` that returns SSE events to the client, mirroring the main board SSE pattern
- **Auto-navigation**: After generation completes, auto-navigate to the new sub-board page (`/boards/:subBoardId`)
- **Guard routes**: Redirect to existing sub-board if the task already has one; validate task ownership and nesting depth
- **Remove inline flow**: The `SubBoardCreationFlow` component and its inline panel rendering are replaced by navigation to the new route. The "Expand to Board" button in `TaskDetailPanel` navigates to the new route instead of toggling inline state
- Keep the existing `POST /api/tasks/:id/generate-sub-board` JSON endpoint unchanged for backward compatibility

## Impact
- Affected specs: `board-ui`, `board-generation-progress`
- Affected code:
  - **Frontend**: New route `boards.$boardId.expand.$taskId.tsx`, new/adapted generation progress component and SSE hook, `TaskDetailPanel.tsx` (navigation change), `SubBoardCreationFlow.tsx` (remove or repurpose)
  - **Backend**: New SSE endpoint in `boards/router.py`, reuses existing `generate_sub_board_stream()` from AI service
