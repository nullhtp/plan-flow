# Change: Add full-screen board generation progress view

## Why
When a user clicks "Generate Board", they currently see only a spinning button with "Generating your board..." text for 15-60 seconds while the AI generates and enriches ~15 tasks. There is zero incremental feedback, making the experience feel slow and opaque. The backend already has an internal streaming pipeline (skeleton_ready → task_enriched × N → generation_complete) that can be exposed to the client.

## What Changes
- **Backend**: Expose the existing internal SSE async generator (`generate_board_stream`) as an actual `text/event-stream` HTTP endpoint so the frontend can receive real-time progress events
- **Frontend**: Replace the spinner button on the goal summary page with a full-screen generation progress view that:
  - Shows the board title once the skeleton is ready
  - Displays phase text ("Creating board structure...", "Adding details 3/15...")
  - Shows a stack list of tasks (newest on top) with a gradient fade at the bottom
  - Limits the visible stack to 5-6 items
  - Auto-navigates to the board after a brief 1.5s delay once complete
- **New capability**: `board-generation-progress` — the full-screen progress UI and its SSE data source
- **Modified capabilities**: `goal-input-ui` (generation trigger transitions to progress view), `board-ui` (board loading state after generation)

## Impact
- Affected specs: `board-generation-progress` (new), `goal-input-ui`, `board-ui`
- Affected code:
  - Backend: `boards/router.py` (new SSE endpoint), `boards/task_service.py` (minor — expose stream instead of consuming it)
  - Frontend: `goals/components/goal-summary.tsx` (trigger + transition), new `BoardGenerationProgress` component, SSE client hook, `routes/boards.$boardId.tsx` (post-generation navigation)
