## ADDED Requirements

### Requirement: Update Template Structure Endpoint
The system SHALL expose `PUT /api/templates/:id/structure` as an authenticated endpoint that replaces the entire task structure (tasks, dependencies, subtasks) of a template. Only the template creator SHALL be allowed to update the structure. The request body SHALL include `tasks` (required, array of task objects with `id` or `temp_id`, `title`, `description`, `is_goal_node`, `subtasks` array, `depends_on` array of task IDs or temp_ids, and optional `priority` and `estimated_minutes`). The endpoint SHALL validate the DAG structure (no cycles, exactly one goal node, connected graph) before persisting. On success, the endpoint SHALL delete all existing template tasks, dependencies, and subtasks and insert the new structure in a single transaction. The endpoint SHALL also update the template's `task_count` field. The response SHALL return the updated template detail (status 200).

#### Scenario: Update template structure successfully
- **WHEN** the template creator sends `PUT /api/templates/:id/structure` with a valid task array forming a DAG
- **THEN** all existing tasks, dependencies, and subtasks are replaced with the new structure
- **AND** the response status is 200 with the updated template detail including new tasks and edges

#### Scenario: Update template structure by non-creator rejected
- **WHEN** user A sends `PUT /api/templates/:id/structure` for user B's template
- **THEN** the response status is 404

#### Scenario: Update template structure with cycle rejected
- **WHEN** the submitted tasks contain a dependency cycle
- **THEN** the response status is 422 with an error indicating the DAG is invalid

#### Scenario: Update template structure with no goal node rejected
- **WHEN** the submitted tasks have no task with `is_goal_node: true`
- **THEN** the response status is 422 with an error indicating a goal node is required

#### Scenario: Update template structure with disconnected graph rejected
- **WHEN** the submitted tasks have a disconnected subgraph
- **THEN** the response status is 422 with an error indicating the graph is disconnected

### Requirement: Template Task Detail Panel
The system SHALL provide a `TemplateTaskDetailPanel` slide-over component that displays template task details when a user clicks a task node in the DAG view on the template detail page. The panel SHALL display: task title, description, subtasks list, priority, and estimated minutes. When the authenticated user is the template owner, all displayed fields SHALL be editable inline. When the user is not the owner (read-only mode), the fields SHALL be displayed as non-editable text. The panel SHALL include a "Delete Task" action (owner only) that removes the task and its related edges from the local graph state. The panel SHALL close when the user clicks outside it or presses Escape.

#### Scenario: View task details in read-only mode
- **WHEN** a non-owner user clicks a task node in the template DAG
- **THEN** a slide-over panel opens showing the task's title, description, subtasks, priority, and estimated minutes as read-only text

#### Scenario: Edit task details as owner
- **WHEN** the template owner clicks a task node in the template DAG
- **THEN** a slide-over panel opens with editable fields for title, description, subtasks, priority, and estimated minutes
- **AND** changes update the local graph state immediately

#### Scenario: Delete task from panel
- **WHEN** the template owner clicks "Delete Task" in the panel for a non-goal task
- **THEN** the task and all its related dependency edges are removed from the DAG
- **AND** the panel closes

#### Scenario: Delete goal task prevented
- **WHEN** the template owner clicks "Delete Task" for the goal node
- **THEN** the deletion is prevented with a message "Cannot delete the goal node. Designate another task as the goal first."

## MODIFIED Requirements

### Requirement: Update Template Endpoint
The system SHALL expose `PATCH /api/templates/:id` as an authenticated endpoint that updates template metadata. Updatable fields: `title`, `description`, `category_id`, `visibility`. Only the template creator SHALL be allowed to update. The endpoint SHALL NOT allow updating the template's task structure — structural updates are handled by `PUT /api/templates/:id/structure`.

#### Scenario: Update template visibility to public
- **WHEN** the creator sends `PATCH /api/templates/:id` with `{"visibility": "public"}`
- **THEN** the template visibility is updated to public

#### Scenario: Update template by non-creator rejected
- **WHEN** user A sends `PATCH /api/templates/:id` for user B's template
- **THEN** the response status is 404

### Requirement: Template Detail Page
The system SHALL provide a `/templates/:id` page that shows the full template structure as a DAG (directed acyclic graph) visualization. The page SHALL display: template metadata (title, description, category, creator, task count) in a header section, and the template's task graph rendered via the `TemplateDagView` component with dagre auto-layout. Clicking a task node SHALL open a `TemplateTaskDetailPanel` slide-over showing task details. When the authenticated user is the template owner, the DAG SHALL be interactive: nodes are draggable, edges can be created by dragging between node handles, edges can be deleted by clicking them, and tasks can be added via an "Add Task" button. A "Save Changes" button SHALL appear when the graph has unsaved modifications. When the user is not the owner, the DAG SHALL be read-only (no dragging, no edge creation/deletion, no structural editing). The page SHALL include a "Use Template" button that navigates to a confirmation step and then creates a board from the template.

#### Scenario: User views template detail as DAG
- **WHEN** a user navigates to `/templates/:id` for a public template
- **THEN** the page displays the template's metadata in a header and the task graph as an interactive DAG with dagre auto-layout, showing task nodes connected by dependency edges

#### Scenario: User clicks task node to view details
- **WHEN** a user clicks a task node in the DAG
- **THEN** a `TemplateTaskDetailPanel` slide-over opens showing the task's title, description, subtasks, priority, and estimated minutes

#### Scenario: Owner edits template structure in DAG
- **WHEN** the template owner views their template detail page
- **THEN** the DAG is interactive: nodes are draggable, edges can be created and deleted, tasks can be added and removed
- **AND** a "Save Changes" button appears when modifications are made

#### Scenario: Owner saves structural changes
- **WHEN** the template owner makes structural edits (add/remove tasks, add/remove edges, edit task details) and clicks "Save Changes"
- **THEN** the full graph structure is sent to `PUT /api/templates/:id/structure` and persisted
- **AND** the "Save Changes" button disappears after successful save

#### Scenario: Non-owner sees read-only DAG
- **WHEN** a non-owner user navigates to `/templates/:id` for a public template
- **THEN** the DAG is read-only: nodes are not draggable, edges cannot be created or deleted, no "Add Task" or "Save Changes" buttons are shown

#### Scenario: Cycle prevention during editing
- **WHEN** the owner tries to create an edge that would form a cycle
- **THEN** the edge creation is rejected with a toast error "Cannot create dependency: would create a cycle"

#### Scenario: User creates board from template
- **WHEN** a user clicks "Use Template" on the template detail page
- **THEN** a confirmation dialog appears with an optional title override field
- **AND** upon confirmation, a board is created and the user is navigated to the new board
