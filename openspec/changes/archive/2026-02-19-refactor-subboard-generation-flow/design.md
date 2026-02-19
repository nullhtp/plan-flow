## Context
The sub-board creation flow currently lives inline within the task detail side panel. It uses compact question fields and a static spinner during generation, with no real-time progress feedback. The main board generation flow, by contrast, has a full-screen question form and a polished SSE-powered generation progress view. This change unifies the two experiences.

## Goals / Non-Goals
- Goals:
  - Full-screen question page for sub-board creation at `/boards/$boardId/expand/$taskId`
  - Real-time SSE generation progress identical to main board generation
  - Auto-navigation to the newly created sub-board on completion
  - Backend SSE endpoint for sub-board generation streaming
- Non-Goals:
  - Changing the AI question generation logic or prompt content
  - Changing the sub-board skeleton/enrichment AI pipeline
  - Adding follow-up question rounds for sub-boards (currently single round, stays single round)
  - Removing the existing JSON generation endpoint

## Decisions

### 1. Dedicated route vs modal overlay
- **Decision**: Use a dedicated route (`/boards/$boardId/expand/$taskId`) rather than a full-screen modal overlay
- **Rationale**: Matches the main board creation pattern (`/goals/new`), supports direct linking/bookmarking, cleaner navigation history, and avoids complex overlay z-index/scroll issues over the React Flow canvas
- **Alternatives considered**: Full-screen modal overlay (rejected: no URL state, complex DOM layering over React Flow)

### 2. Separate SSE endpoint vs modifying existing
- **Decision**: Add new `POST /api/tasks/:id/generate-sub-board/stream` endpoint; keep existing JSON endpoint
- **Rationale**: Non-breaking change. The existing JSON endpoint may still be useful for programmatic/test scenarios. Mirrors the main board pattern which has both `/generate-board` (JSON) and `/generate-board/stream` (SSE)
- **Alternatives considered**: Converting existing endpoint to SSE (rejected: breaking change)

### 3. Reuse generation progress component
- **Decision**: Reuse the existing `BoardGenerationProgress` component and `useBoardGenerationStream` hook by making them accept a generic SSE URL rather than being hardcoded to the goal-based endpoint
- **Rationale**: Both flows produce identical SSE events (`skeleton_ready`, `task_enriched`, `generation_complete`, `generation_error`). A single parameterized component avoids code duplication
- **Alternatives considered**: Duplicate components (rejected: maintenance burden); wrap in a factory (over-engineered for two use cases)

### 4. Page state machine
- **Decision**: The expansion page uses a linear state machine: `loading-questions` -> `questions` -> `generating` -> (auto-navigates to sub-board). No summary step (sub-boards have only 2-4 questions). Error states at each step allow retry or back-navigation
- **Rationale**: Keeps the flow fast and focused. The main board flow has 5+ questions and follow-ups, justifying a summary step; sub-boards don't need that overhead

### 5. Full-size question fields
- **Decision**: Use the same full-size `QuestionFieldWrapper`, `OptionField`, `MultiselectOptionField` components (without `compact` prop) as the goal creation form
- **Rationale**: With a dedicated full-screen page, there's no space constraint. Full-size fields are easier to interact with

## Risks / Trade-offs
- **Extra navigation step**: User leaves the board page to expand a task, adding a navigation hop. Mitigated by auto-navigation to sub-board on completion and breadcrumb navigation back
- **Two SSE endpoints**: Slight increase in backend surface area. Both follow identical patterns, so maintenance is minimal
- **Stale `SubBoardCreationFlow` component**: Must be removed or clearly deprecated to avoid confusion

## Open Questions
- None at this time; all clarifications resolved during proposal drafting
