# Change: Improve template DAG preview and editing

## Why
Templates currently display as flat task lists on the detail page and are not editable after creation. Since the entire product is built around DAG visualization, templates should also be previewed as interactive DAGs — and owned templates should be editable in DAG mode so users can refine their saved templates over time.

## What Changes
- **Template detail page (`/templates/:id`) switches from flat task list to DAG view** — all templates (public and owned) render as a React Flow DAG graph with dagre auto-layout. Clicking a task node opens a slide-over panel showing task details (title, description, subtasks, priority, time estimate).
- **Own templates are always editable in DAG mode** — when the authenticated user owns the template, the DAG is interactive: nodes are draggable, edges can be created/deleted, tasks can be added/removed, and task details can be edited via the panel. A "Save" button persists structural changes. Non-owners see a read-only DAG.
- **New backend endpoint for structural updates** — `PUT /api/templates/:id/structure` accepts the full task/edge/subtask structure and replaces the existing one in a single transaction with DAG validation.
- **Template browse page (`/templates`) keeps the card grid** — clicking a card navigates to the detail page which now shows the DAG instead of a flat list.

## Impact
- Affected specs: `board-templates` (Template Detail Page, Update Template Endpoint)
- Affected code:
  - `frontend/src/routes/templates.$templateId.tsx` — replace flat task list with DAG view + edit mode
  - `frontend/src/features/templates/components/TemplateDagView.tsx` — reuse for detail page (currently only used in generation preview)
  - `frontend/src/features/templates/components/TemplateTaskNode.tsx` / `TemplateGoalNode.tsx` — reuse existing
  - New: `TemplateTaskDetailPanel` component for slide-over on node click
  - `backend/app/domains/templates/router.py` — new PUT endpoint
  - `backend/app/domains/templates/service.py` — new `update_template_structure` function
  - `backend/app/domains/templates/schemas.py` — new request/response schemas
