# Change: Add Board Templates

## Why
Currently boards are generated exclusively via the AI pipeline, requiring users to go through goal creation, adaptive questioning, and AI generation every time. Users who want to create boards for common goals (e.g., "Move to a new city", "Plan a wedding") must repeat the full flow. Board templates let users save their own board structures as reusable templates, browse/use templates shared by others, and create boards instantly from a template — providing an alternative path alongside AI generation.

## What Changes
- New `board-templates` capability: template data model, CRUD API, "create board from template" endpoint, visibility (public/private), and category-based browsing
- **BREAKING**: Updates `board-management` business rule — board creation is no longer purely AI-generated; templates provide an alternative creation path
- New frontend feature: dedicated `/templates` page for browsing, searching, and selecting templates
- New frontend feature: "Save as template" action from existing boards

## Impact
- Affected specs: `board-management` (new creation path), new `board-templates` capability
- Affected code:
  - Backend: new `app/domains/templates/` domain (models, schemas, repository, service, router)
  - Backend: new Alembic migration for `board_template`, `template_task`, `template_task_dependency`, `template_subtask`, `template_category` tables
  - Frontend: new `features/templates/` feature module (components, hooks)
  - Frontend: new `/templates` route and template detail route
  - Frontend: "Save as template" UI on board view
