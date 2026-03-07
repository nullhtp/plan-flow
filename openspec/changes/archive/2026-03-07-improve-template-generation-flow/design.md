## Context

Template generation is currently a shallow flow: paste content in a dialog -> single LLM call -> edit flat list -> save. Board creation has a rich pipeline: goal input -> classification -> adaptive questions -> SSE streaming generation (research -> skeleton -> enrichment) -> auto-navigate to board. This change unifies template generation with the board creation experience.

Key stakeholders: solo developer, end users who generate templates from content or descriptions.

## Goals / Non-Goals

### Goals
- Unify template generation UX with board creation (adaptive questions, streaming progress, board-mode preview)
- Improve template quality by adding classification, adaptive questions, research, skeleton review, and per-task enrichment
- Enable full structural editing in a React Flow DAG preview before saving
- Support a "Describe" input mode alongside existing Text/Document/URL inputs
- Reuse existing shared components (question fields, DagView, TaskDetailPanel, BoardGenerationProgress)

### Non-Goals
- Adding AI chat to the template preview (manual editing only for MVP)
- Changing the board creation flow itself (no modifications to the goal wizard)
- Changing the template data model (TemplateTask, TemplateTaskDependency, etc. remain unchanged)
- Adding collaboration features to template editing

## Decisions

### 1. Full-page flow replaces dialog
- **Decision**: Remove `GenerateTemplateDialog` and create a new `/templates/generate` page
- **Why**: The adaptive question form, streaming progress view, and React Flow DAG preview cannot fit in a dialog. The full-page flow matches the goal creation pattern.
- **Alternatives**: Keep dialog for quick flow + page for full flow (rejected: two flows to maintain, confusing UX)

### 2. Template classification reuses goal classification pipeline
- **Decision**: Reuse the same classification node (`classify_goal`) adapted for template context. For content-based inputs, classification runs on extracted content. For "Describe" input, it runs on the description text.
- **Why**: Same pipeline = same question quality. The classification output (domain, complexity, dimensions, language) drives the question generation identically.
- **Alternatives**: Template-specific lightweight classification (rejected: more code, lower quality)

### 3. Max 2 question rounds with readiness indicator
- **Decision**: Limit template questions to initial round + 1 follow-up round. Show readiness indicator after round 1.
- **Why**: Templates are more generic than personal goals. 2 rounds provides enough context without fatiguing the user. Readiness indicator still helps communicate information completeness.
- **Alternatives**: Full unlimited rounds (rejected: overkill for templates), 1 round only (rejected: insufficient for complex templates)

### 4. Content analysis before questions
- **Decision**: For text/document/URL inputs, AI first analyzes the content and uses it as context for classification + question generation. The content is NOT discarded — it's carried through the pipeline as additional context alongside Q&A.
- **Why**: The content provides the base structure; questions refine it (team size, scope, customization preferences).

### 5. Full React Flow DAG preview with structural editing
- **Decision**: Reuse `DagView` component and `TaskDetailPanel` in a "template preview mode" that allows full structural editing (add/remove tasks, edit edges, edit all task fields).
- **Why**: Users need to see and understand the template structure before saving. The existing components are proven and familiar.
- **Implementation approach**: DagView already renders the graph. Add a "template mode" prop that:
  - Makes nodes directly editable (click to open TaskDetailPanel in edit mode)
  - Adds an "Add Task" button that creates a new unconnected node
  - Allows deleting tasks via the panel or right-click context menu
  - Enables edge creation/deletion via React Flow's connection handles
  - The data source is local state (not API-backed board data) since the template hasn't been saved yet

### 6. SSE streaming with full pipeline
- **Decision**: New endpoint `POST /api/templates/generate/stream` that uses the same research -> skeleton -> review -> parallel enrichment pipeline as board generation.
- **Why**: Same quality, consistent UX, reusable backend code. Template-specific prompts ensure the output is template-appropriate.

### 7. Dual save action
- **Decision**: Primary "Save Template" button saves to template tables. An optional "Also create board" checkbox creates a board immediately from the saved template.
- **Why**: Users who generate templates from a specific need often want to use it immediately.

## Risks / Trade-offs

- **Increased complexity**: The template generation flow goes from ~3 steps to ~6 steps. Mitigated by reusing existing components and patterns.
- **Longer generation time**: Full pipeline (research + enrichment) takes 20-60s vs current ~5s single call. Mitigated by streaming progress that keeps users engaged.
- **API cost increase**: Research + per-task enrichment uses more LLM calls per template. Acceptable given templates are generated less frequently than boards.
- **DagView in template mode**: The DagView currently reads from API-backed board data. Template preview needs a local-state-backed version. This requires abstracting the data source.

## Open Questions

- None remaining after clarification round.
