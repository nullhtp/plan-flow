## 1. Backend — SSE Streaming Endpoint

- [x] 1.1 Add `POST /api/goals/{goal_id}/generate-board/stream` SSE endpoint to `boards/router.py` using FastAPI `StreamingResponse` with `media_type="text/event-stream"`. Reuse existing goal validation logic from the JSON endpoint. Pipe `generate_board_stream()` events directly to the response.
- [x] 1.2 Ensure each SSE event has proper `event:` and `data:` formatting (the internal `_format_sse_event` already does this — verify compatibility with browser SSE parsing).
- [x] 1.3 Add error handling: if the generator raises before yielding, return a proper HTTP error response (not SSE). If it raises mid-stream, yield a `generation_error` event.
- [x] 1.4 Add CORS headers for SSE if needed (verify existing CORS config covers `text/event-stream`).
- [ ] 1.5 Write integration test: verify SSE endpoint returns correct event sequence for a mocked generation.

## 2. Frontend — SSE Client Hook

- [x] 2.1 Add `@microsoft/fetch-event-source` (or implement a minimal fetch-based SSE utility) to support POST-based SSE with auth headers.
- [x] 2.2 Create `useBoardGenerationStream` hook in `frontend/src/features/goals/hooks/`. Hook manages connection lifecycle, parses SSE events, tracks phase/tasks/progress, and cleans up on unmount via `AbortController`.
- [ ] 2.3 Unit test the hook: verify state transitions for skeleton_ready, task_enriched, generation_complete, generation_error, and connection drop.

## 3. Frontend — Generation Progress Component

- [x] 3.1 Create `BoardGenerationProgress` component in `frontend/src/features/goals/components/`. Full-screen layout with vertically centered content.
- [x] 3.2 Implement header area showing board title (blank/loading until skeleton_ready).
- [x] 3.3 Implement phase text indicator that updates through generation stages ("Creating board structure..." → "Adding details (X/N)..." → "Board ready!" / "Generation failed").
- [x] 3.4 Implement task stack list: reverse-chronological, newest on top, limited to 5-6 visible items with gradient fade at bottom (CSS `mask-image` or overlay gradient).
- [x] 3.5 Implement staggered reveal animation for skeleton tasks (50-100ms between each, total under 2 seconds).
- [x] 3.6 Implement task status indicator: skeleton-only vs enriched visual state (e.g., muted → full opacity, or empty dot → filled dot).
- [x] 3.7 Implement auto-navigation: 1.5s delay after `generation_complete`, then navigate to `/boards/{boardId}`. Cancel if component unmounts.
- [x] 3.8 Implement error state: error message, "Try Again" button, and "Check your boards" link for mid-stream connection loss.

## 4. Frontend — Integration into Goal Wizard

- [x] 4.1 Add `generating` step to the goal creation wizard in `routes/goals.new.tsx`. Transition to this step when user clicks "Generate Board".
- [x] 4.2 Update `GoalSummary` component to trigger the wizard step transition instead of the old mutation-based flow.
- [x] 4.3 Pass `goalId` to the `BoardGenerationProgress` component from the wizard state.
- [x] 4.4 Handle edge case: if user navigates back from `generating` step, abort the SSE connection.

## 5. Validation & Polish

- [x] 5.1 End-to-end manual test: full flow from goal summary → generation progress → auto-navigate to board.
- [x] 5.2 Test error scenarios: connection drop, generation_error, retry flow.
- [x] 5.3 Test responsive behavior: verify full-screen layout and stack list work on mobile viewport widths.
- [x] 5.4 Verify the existing JSON endpoint (`POST /api/goals/{goal_id}/generate-board`) still works unchanged.
