## 1. Backend: Update Template Structure Endpoint

- [x] 1.1 Add `UpdateTemplateStructureRequest` schema to `backend/app/domains/templates/schemas.py` — accepts `tasks` array (each with `id`/`temp_id`, `title`, `description`, `is_goal_node`, `subtasks`, `depends_on`, optional `priority` and `estimated_minutes`)
- [x] 1.2 Add `update_template_structure` function to `backend/app/domains/templates/service.py` — validates DAG (reuse `validate_dag` and `validate_goal_node` from `boards/dag_utils.py`), deletes existing tasks/deps/subtasks, inserts new structure, updates `task_count`, returns updated template detail. Single transaction.
- [x] 1.3 Add `PUT /api/templates/:id/structure` route to `backend/app/domains/templates/router.py` — ownership check, call service, return 200 with `TemplateDetailResponse`
- [x] 1.4 Write integration tests in `backend/tests/domains/templates/` — test success case, non-creator 404, cycle rejection 422, no goal node 422, disconnected graph 422
- [x] 1.5 Add `UpdateTemplateStructureRequest` type to frontend `types.ts` (Orval not needed — templates use hand-written types)

## 2. Frontend: Add readOnly prop to TemplateDagView

- [x] 2.1 Add `readOnly?: boolean` prop to `TemplateDagView` component (`frontend/src/features/templates/components/TemplateDagView.tsx`). When `readOnly=true`: disable `nodesDraggable`, `nodesConnectable`, `edgesUpdatable`; suppress edge click deletion handler; hide validation warnings overlay. Default `false` (preserves current generation preview behavior).
- [x] 2.2 Verify generation preview step (`templates.generate.tsx` TemplatePreviewStep) still works correctly with default `readOnly=false`

## 3. Frontend: TemplateTaskDetailPanel Component

- [x] 3.1 Create `TemplateTaskDetailPanel` component in `frontend/src/features/templates/components/` — slide-over panel opened on task node click. Props: `task` data, `readOnly` boolean, `onUpdate` callback, `onDelete` callback, `onClose` callback.
- [x] 3.2 Read-only mode: display task title, description, subtasks list, priority badge, estimated minutes as static text
- [x] 3.3 Edit mode (owner): editable fields for title (input), description (textarea), subtasks (add/remove/edit titles), priority (select), estimated_minutes (number input). Changes fire `onUpdate` callback immediately.
- [x] 3.4 "Delete Task" button in edit mode — calls `onDelete`, with goal node protection message

## 4. Frontend: Rewrite Template Detail Page

- [x] 4.1 Add `useUpdateTemplateStructure` mutation hook in `frontend/src/features/templates/hooks/use-template-mutations.ts` — calls `PUT /api/templates/:id/structure`
- [x] 4.2 Rewrite `frontend/src/routes/templates.$templateId.tsx` — replace flat task list with:
  - Header section: template metadata (title, description, category badge, creator, task count), "Use Template" button, metadata edit fields for owner
  - Main area: `TemplateDagView` component. Pass `readOnly={!isOwner}` based on `template.creator.id === currentUser.id`
  - Node click: open `TemplateTaskDetailPanel` with task data
  - Owner mode: "Save Changes" button (visible when dirty)
- [x] 4.3 Implement dirty state tracking — compare current graph state vs. last-saved state. Show "Save Changes" button only when dirty. Warn on navigation away with unsaved changes (beforeunload).
- [x] 4.4 Wire "Save Changes" to `useUpdateTemplateStructure` mutation — serialize current nodes/edges into the request format, call PUT endpoint, on success refresh template query and reset dirty state

## 5. Validation & Polish

- [ ] 5.1 Test full flow: navigate to own template detail page, verify DAG renders, edit a task title, add a new task, create an edge, delete an edge, save changes, reload page and verify persistence
- [ ] 5.2 Test read-only flow: navigate to another user's public template, verify DAG renders as read-only, verify task detail panel shows info, verify no edit controls
- [x] 5.3 Run backend tests: `pytest backend/tests/domains/templates/` — all 40 tests pass
- [x] 5.4 Run frontend lint + type check — all changed files pass Biome lint; TypeScript errors are pre-existing (ReactFlowInstance typing, unused `_data`)
- [x] 5.5 Run Biome format check — all changed files pass formatting
