## MODIFIED Requirements

### Requirement: Save Board as Template Action
The system SHALL add a "Save as Template" button to the board view page. Clicking the button SHALL immediately create a template via the API using default values: the board's title as template title, no description, no category, and `private` visibility. No modal or dialog SHALL be shown. Upon successful creation, the user SHALL be automatically navigated to the template detail page (`/templates/:id`) where all metadata and structure can be edited inline. A loading/disabled state SHALL be shown on the button while the API call is in progress. If the button is clicked on a board with no tasks, it SHALL be disabled. If the API call fails, a toast error SHALL be displayed and the user SHALL remain on the board page.

#### Scenario: User saves board as template
- **WHEN** a user clicks "Save as Template" on a board with 12 tasks
- **THEN** a template is created immediately with the board's title, private visibility, no description, and no category
- **AND** the user is automatically navigated to `/templates/:id` for the new template

#### Scenario: Save as template shows loading state
- **WHEN** a user clicks "Save as Template" and the API call is in progress
- **THEN** the button shows a loading/disabled state until the call completes

#### Scenario: Save as template fails
- **WHEN** the API call to create a template fails
- **THEN** a toast error is displayed and the user remains on the board page

#### Scenario: Save as template disabled for empty board
- **WHEN** a user views a board with no tasks
- **THEN** the "Save as Template" button is disabled

### Requirement: Template Detail Page
The system SHALL provide a `/templates/:id` page that shows the full template structure as a DAG (directed acyclic graph) visualization. The page SHALL display: template metadata (title, description, category, creator, task count, visibility) in a header section, and the template's task graph rendered via the `TemplateDagView` component with dagre auto-layout. Clicking a task node SHALL open a `TemplateTaskDetailPanel` slide-over showing task details. When the authenticated user is the template owner, the DAG SHALL be interactive: nodes are draggable, edges can be created by dragging between node handles, edges can be deleted by clicking them, and tasks can be added via an "Add Task" button. A "Save Changes" button SHALL appear when the graph has unsaved modifications. When the user is not the owner, the DAG SHALL be read-only (no dragging, no edge creation/deletion, no structural editing). The page SHALL include a "Use Template" button that navigates to a confirmation step and then creates a board from the template.

When the authenticated user is the template owner, the metadata row SHALL include an interactive visibility toggle (private/public dropdown or select) that updates the template visibility immediately via the `PATCH /api/templates/:id` endpoint. When the user is not the owner, the visibility SHALL be displayed as read-only text. This allows owners to change visibility directly on the detail page without needing a separate dialog.

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

#### Scenario: Owner changes template visibility
- **WHEN** the template owner selects "Public" from the visibility dropdown on the template detail page
- **THEN** the template visibility is updated to public via `PATCH /api/templates/:id`
- **AND** the change is reflected immediately in the UI

#### Scenario: Non-owner sees read-only visibility
- **WHEN** a non-owner user views a public template detail page
- **THEN** the visibility is displayed as read-only text (e.g., "Public")
