## 1. Frontend Implementation

- [x] 1.1 Add `view` search param to `BoardSearchParams` in `boards.$boardId.tsx` route definition (validate as `"focus" | "full"`, default `"focus"`)
- [x] 1.2 Create `filterBoardForFocusView(board: BoardResponse): { tasks: TaskResponse[], edges: EdgeResponse[] }` utility in `dagre-layout.ts` (or a new `board-filters.ts`) that returns only visible tasks and their connecting edges
- [x] 1.3 Update `DagView` to accept `viewMode` prop (`"focus" | "full"`) and apply the filter before passing data to `getLayoutedElements`
- [x] 1.4 Add toggle switch UI (Focus / Full) in the board header bar next to existing toolbar buttons
- [x] 1.5 Wire toggle to update the `view` search param via router navigation
- [x] 1.6 Ensure `TaskDetailPanel` still works when a focused-view-visible task is clicked (panel should use `board.tasks` for dependency/dependent lists, not filtered list)
- [x] 1.7 Handle edge case: if selected task (from `?task=` param) is hidden in focus mode, auto-switch to full view or deselect

## 2. Testing

- [x] 2.1 Add unit tests for `filterBoardForFocusView` covering: all-done board, all-locked board, mixed states, goal node always included
- [ ] 2.2 Manual verification: toggle between focus/full on a board with mixed task statuses, verify layout recomputes cleanly
- [ ] 2.3 Verify URL persistence: navigate away and back, confirm view mode is preserved
