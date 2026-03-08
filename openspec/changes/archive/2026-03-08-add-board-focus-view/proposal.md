# Change: Add focused view toggle for board DAG

## Why
Boards with many tasks display the entire DAG at once, which can be overwhelming. Users need a way to focus on actionable tasks -- the work they can do right now -- without the visual noise of locked future tasks they cannot yet start.

## What Changes
- Add a "Focus / Full" toggle in the board header toolbar
- When in Focus mode, hide locked `not_started` tasks (tasks whose dependencies are not all `done`), keeping all `done` tasks, all `in_progress` tasks, all unlocked `not_started` tasks, and the goal node visible
- Edges between hidden tasks are also hidden; edges connecting visible tasks remain
- The toggle state is persisted in the URL via a `view` search parameter (`?view=focus` or `?view=full`), defaulting to `focus` when absent
- The dagre layout recomputes with only the visible nodes/edges, so the focused graph is properly laid out (not just hidden nodes with gaps)

## Impact
- Affected specs: `board-ui`
- Affected code:
  - `frontend/src/routes/boards.$boardId.tsx` (add `view` search param)
  - `frontend/src/features/board/components/DagView.tsx` (filtering logic + toggle UI)
  - `frontend/src/features/board/utils/dagre-layout.ts` (accept filtered task/edge lists)
