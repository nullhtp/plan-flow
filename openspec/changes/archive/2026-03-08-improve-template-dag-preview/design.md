## Context

The template detail page (`/templates/:id`) currently renders tasks as a flat scrollable list with text-based dependency references. Meanwhile, the template generation wizard already has a fully interactive DAG editor (`TemplateDagView`) used only in the preview step. The board detail page uses its own `DagView` component for read-only DAG visualization.

This change needs to:
1. Replace the flat task list on the template detail page with a DAG view
2. Make the DAG always-editable for template owners, read-only for others
3. Add a backend endpoint to persist structural edits to saved templates
4. Add a task detail slide-over panel for viewing/editing task details on node click

The change spans frontend (route page, reuse of existing DAG components, new panel component) and backend (new endpoint, service function, schema).

## Goals / Non-Goals

- Goals:
  - Reuse existing `TemplateDagView` component for both generation preview and detail page
  - Consistent DAG visualization across the product (templates match boards in visual style)
  - Minimal new backend code — single PUT endpoint for full structure replacement
  - Owner always sees editable DAG; non-owner sees read-only DAG with clickable detail panel

- Non-Goals:
  - Changing the template browse page layout (card grid stays as-is)
  - Adding real-time collaboration or auto-save
  - Changing the generation wizard preview step (it already works correctly)
  - Adding DAG thumbnails to template cards in the browse grid

## Decisions

### 1. Reuse TemplateDagView with a `readOnly` prop

**Decision**: Add a `readOnly` boolean prop to `TemplateDagView`. When `true`, nodes are not draggable, edges cannot be created/deleted, and no structural editing is possible. When `false` (default, current behavior), full interactivity is enabled.

**Why**: The component already handles all the interactive DAG logic (dagre layout, edge creation, cycle detection, validation). Adding a read-only mode is trivial (disable `nodesDraggable`, `nodesConnectable`, `edgesUpdatable`, suppress edge click handler). This avoids duplicating DAG rendering logic or creating a separate read-only component.

**Alternative considered**: Create a new `TemplateReadOnlyDagView` component. Rejected — too much duplication of layout and rendering logic.

### 2. New TemplateTaskDetailPanel component

**Decision**: Create a `TemplateTaskDetailPanel` slide-over component similar to the board's `TaskDetailPanel` but adapted for template tasks. In read-only mode, it displays task info. In edit mode, it shows editable fields (title, description, subtasks, priority, estimated_minutes).

**Why**: The board's `TaskDetailPanel` is tightly coupled to board API hooks (mutations, status transitions, chat, subtask completion). Template tasks have no status, no chat, no AI actions. A separate component is simpler than adding template-mode branching to the existing panel.

**Alternative considered**: Reuse the board `TaskDetailPanel` with a `mode` prop. Rejected — the board panel has too many board-specific features (status badges, lock indicators, chat tab, subtask completion, AI actions) that would need conditional hiding.

### 3. PUT /api/templates/:id/structure for full replacement

**Decision**: A single `PUT /api/templates/:id/structure` endpoint that accepts the complete task/edge/subtask arrays and replaces the existing structure in one transaction (delete all existing tasks/deps/subtasks, insert new ones).

**Why**: This is consistent with how `save-generated` works — the frontend sends the full graph state. Full replacement avoids complex diffing logic and ensures DAG validation runs on the complete structure. The existing `PATCH /api/templates/:id` continues to handle metadata-only updates.

**Alternative considered**: Granular CRUD endpoints (POST/PATCH/DELETE for individual tasks and edges). Rejected — requires many endpoints, complex frontend state management, and makes atomic DAG validation harder.

### 4. Owner always sees editable DAG (no toggle button)

**Decision**: When the authenticated user is the template owner, the DAG is always interactive. A persistent "Save Changes" button appears when there are unsaved modifications (dirty state tracking). Non-owners always see read-only mode.

**Why**: User preference from requirements discussion. Eliminates an extra click to enter edit mode. Dirty state tracking via simple deep comparison of the current graph vs. the last-saved graph state prevents accidental navigation away with unsaved changes.

## Risks / Trade-offs

- **Full replacement on save**: Deleting and re-inserting all tasks/deps/subtasks on every save is slightly more expensive than incremental updates, but template graphs are small (typically 5-30 tasks) so this is negligible. Simplicity wins.
- **No undo/redo**: The DAG editor doesn't support undo. If a user accidentally deletes a task and saves, it's gone. Mitigation: the "Save Changes" button only appears on dirty state, and users must explicitly click it. Future enhancement could add undo.
- **React Flow performance**: Rendering an interactive React Flow graph on every template detail page load is heavier than a flat list. For templates with <50 nodes this is not a concern. Templates are unlikely to exceed this.

## Open Questions

- None remaining — all decisions were clarified through user Q&A.
