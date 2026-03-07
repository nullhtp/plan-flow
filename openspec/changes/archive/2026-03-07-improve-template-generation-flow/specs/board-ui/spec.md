## ADDED Requirements

### Requirement: DagView Template Preview Mode
The DagView component SHALL accept a `mode` prop with values `"board"` (default) or `"template-preview"`. In `template-preview` mode: (1) task and edge data SHALL be sourced from props/local state instead of API queries (React Query hooks), (2) React Flow connection handles SHALL be visible on all nodes to allow creating new edges by dragging, (3) edge deletion SHALL be enabled (click edge to select, then delete key or context menu), (4) an "Add Task" button SHALL be rendered above the graph that creates a new unconnected task node with a default title "New Task", (5) real-time DAG validation SHALL run after each structural change (add/remove task, add/remove edge) and display a toast error if the change creates a cycle or leaves the graph without a goal node, (6) the minimap, pan, and zoom behaviors SHALL remain identical to board mode, (7) task nodes in template-preview mode SHALL NOT show status controls (no status toggle) since template tasks have no status. An `onGraphChange` callback prop SHALL notify the parent component of any structural changes (task added/removed, edge added/removed, task fields updated).

#### Scenario: DagView renders in template-preview mode from local state
- **WHEN** DagView is rendered with `mode="template-preview"` and task/edge data passed as props
- **THEN** the graph renders without making any API calls for board data

#### Scenario: Connection handles visible for edge creation
- **WHEN** DagView is in template-preview mode
- **THEN** each task node displays source (bottom) and target (top) connection handles that the user can drag to create new edges

#### Scenario: Edge deletion in template-preview mode
- **WHEN** the user clicks an edge in template-preview mode and presses Delete
- **THEN** the edge is removed and the `onGraphChange` callback fires

#### Scenario: Add task button creates unconnected node
- **WHEN** the user clicks "Add Task" in template-preview mode
- **THEN** a new task node with title "New Task" appears in the graph, unconnected to any other node

#### Scenario: Cycle detected on edge creation
- **WHEN** the user drags an edge from task A to task B but B already has a path to A
- **THEN** the edge is not created and a toast error "Cannot create dependency: would create a cycle" appears

#### Scenario: No status controls in template-preview mode
- **WHEN** DagView is in template-preview mode
- **THEN** task nodes do not show status toggles or lock indicators

### Requirement: TaskDetailPanel Template Preview Mode
The TaskDetailPanel component SHALL accept a `mode` prop with values `"board"` (default) or `"template-preview"`. In `template-preview` mode: (1) editable fields SHALL include title, description, subtasks (add/remove/edit), priority, and estimated_minutes, (2) the Status field SHALL NOT be shown, (3) the Dependencies and Unlocks sections SHALL be shown as read-only lists (derived from the edge data in local state), (4) the AI Actions, Artifacts, and Chat sections SHALL NOT be shown, (5) the "Delete Task" button SHALL be available with confirmation (except for the goal node), (6) a "Set as Goal" toggle SHALL be available to designate a task as the goal node (removing the flag from any other task), (7) all edits SHALL update local state via an `onTaskChange` callback (no API calls), (8) the "Expand to Board" and "Sub-Board" sections SHALL NOT be shown. An `onDeleteTask` callback prop SHALL notify the parent when a task is deleted.

#### Scenario: Template-preview panel shows editable fields
- **WHEN** a user clicks a task node in template-preview mode
- **THEN** the panel shows title, description, subtasks, priority, and estimated_minutes as editable fields

#### Scenario: No status or AI sections in template-preview mode
- **WHEN** the TaskDetailPanel is in template-preview mode
- **THEN** Status, AI Actions, Artifacts, Chat, Expand to Board, and Sub-Board sections are hidden

#### Scenario: Delete task from panel
- **WHEN** the user clicks "Delete Task" on a non-goal task in template-preview mode
- **THEN** a confirmation dialog appears, and on confirm the `onDeleteTask` callback fires

#### Scenario: Set as Goal toggle
- **WHEN** the user toggles "Set as Goal" on a regular task in template-preview mode
- **THEN** that task becomes the goal node and the previous goal node is demoted to a regular task

#### Scenario: Cannot delete goal node
- **WHEN** the user opens the panel for the goal node in template-preview mode
- **THEN** the "Delete Task" button is disabled with a tooltip "Designate another task as the goal first"
