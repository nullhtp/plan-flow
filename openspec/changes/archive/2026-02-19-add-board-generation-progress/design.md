## Context

Board generation takes 15-60 seconds while the AI creates a skeleton of ~15 tasks and then enriches each one with descriptions, metadata, and subtasks. The backend already has an internal async generator streaming pipeline (`generate_board_stream`) that yields SSE-formatted events (`skeleton_ready`, `task_enriched`, `generation_complete`, `generation_error`). However, the HTTP endpoint consumes the entire stream server-side and returns a single JSON response. The frontend shows only a spinning button during this time.

This change exposes the internal stream to the client via a real SSE endpoint and builds a full-screen progress UI that consumes it.

## Goals / Non-Goals

- **Goals:**
  - Expose the existing internal SSE stream as an HTTP `text/event-stream` endpoint
  - Build a full-screen progress view replacing the current spinner button
  - Show incremental task generation progress as a reverse-chronological stack list
  - Auto-navigate to the board when generation completes

- **Non-Goals:**
  - Changing the AI pipeline itself (skeleton + enrichment logic stays the same)
  - Adding WebSocket support (SSE is sufficient for server→client push)
  - Showing real-time DAG visualization during generation (just a task list)
  - Supporting sub-board generation progress (can be added later using the same pattern)

## Decisions

### Decision: SSE over WebSocket
Use Server-Sent Events (SSE) via FastAPI's `StreamingResponse` with `media_type="text/event-stream"`.

**Why:** The data flow is unidirectional (server → client). SSE is simpler than WebSocket, natively supported by browsers via `EventSource`, works through proxies, and auto-reconnects. The backend already formats events as SSE strings internally.

**Alternatives considered:**
- WebSocket: Overkill for unidirectional streaming. Requires more infrastructure.
- Polling: Would work but adds latency and unnecessary requests. The backend stream completes in one shot — polling would miss the natural event flow.

### Decision: New SSE endpoint alongside existing JSON endpoint
Add `POST /api/goals/{goal_id}/generate-board/stream` as a new SSE endpoint. Keep the existing `POST /api/goals/{goal_id}/generate-board` JSON endpoint for backward compatibility and potential non-browser clients.

**Why:** Avoids breaking existing behavior. The SSE endpoint reuses the same `generate_board_stream()` function — it just pipes the events to the client instead of consuming them internally.

### Decision: Frontend uses native EventSource or fetch-based SSE
Use a fetch-based SSE approach (since EventSource only supports GET and this is a POST endpoint). A small utility or the `@microsoft/fetch-event-source` library can handle POST-based SSE.

**Why:** `EventSource` only supports GET requests. Our endpoint is POST (needs auth token in headers). The fetch-based approach gives full control over headers and method.

### Decision: Progress view replaces goal summary in-place
The goal summary page (`/goals/new` at the `summary` step) transitions to a full-screen progress view when the user clicks "Generate Board". No new route — this is a new step (`generating`) in the existing multi-step wizard.

**Why:** Seamless transition. The user stays on the same page. The wizard already has multiple steps (input → loading → questions → summary). Adding `generating` as another step is natural.

### Decision: Two-phase visual display
Phase 1 (skeleton): All task titles appear at once in the stack (can be staggered with small animation delays for visual effect). Phase text: "Creating board structure...".
Phase 2 (enrichment): Each task gets a "filled in" indicator as enrichment completes. Phase text: "Adding details (3/15)...". A counter tracks progress.

**Why:** This accurately reflects the backend pipeline. The skeleton arrives as one event, and enrichments trickle in one-by-one. Showing both phases gives the user a sense of continuous progress.

## Risks / Trade-offs

- **SSE connection dropped mid-generation** → The backend still completes the generation and persists the board. The frontend can detect the lost connection and fall back to polling the board endpoint or showing a "Generation may have completed — check your boards" message with a retry/refresh option.
- **Browser SSE support** → All modern browsers support SSE natively. For POST-based SSE, the fetch approach works everywhere that fetch works.
- **Two endpoints for the same operation** → Minor maintenance cost. The JSON endpoint can eventually be deprecated once all clients use SSE.

## Open Questions

- None — all key decisions resolved through user Q&A.
