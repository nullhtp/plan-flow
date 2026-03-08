## MODIFIED Requirements

### Requirement: Create Board from Template Endpoint
The system SHALL expose `POST /api/templates/:id/create-board` as an authenticated endpoint that creates a new board (and its parent goal) from a template. The request body SHALL optionally include `title` (override for the board/goal title). The endpoint SHALL: (1) validate the template is accessible (public or owned by user), (2) create a new Goal with `title` set to the provided title or template title, `status` set to `active`, and `ai_context` containing `{"source": "template", "template_id": "<id>"}`, (3) create a new Board linked to the goal, (4) copy all template tasks, dependencies, and subtasks to the new board in a single transaction, (5) return the created board summary immediately, (6) trigger background AI action generation for all subtasks on the new board. All new tasks SHALL have `status: not_started` and `completed: false` for subtasks. After the board is returned to the user, the system SHALL asynchronously generate AI actions (`action_label`, `action_icon`, `action_prompt`) for each subtask by calling `generate_subtask_actions` per task in parallel. If action generation fails for any task, the board SHALL remain fully usable — subtasks simply will not have action buttons.

#### Scenario: Create board from public template
- **WHEN** an authenticated user sends `POST /api/templates/:id/create-board` for a public template
- **THEN** a new goal (status `active`) and board are created with tasks, dependencies, and subtasks copied from the template
- **AND** the response status is 201 with the board ID, goal ID, and title
- **AND** background AI action generation is triggered for all subtasks

#### Scenario: Create board from own private template
- **WHEN** the template creator sends `POST /api/templates/:id/create-board` for their private template
- **THEN** a new board is created from the template
- **AND** background AI action generation is triggered for all subtasks

#### Scenario: Create board from another user's private template rejected
- **WHEN** user A sends `POST /api/templates/:id/create-board` for user B's private template
- **THEN** the response status is 404

#### Scenario: Create board with custom title
- **WHEN** a user sends `POST /api/templates/:id/create-board` with `{"title": "My Berlin Move"}`
- **THEN** the created goal and board have title "My Berlin Move"

#### Scenario: AI action generation failure does not affect board creation
- **WHEN** a board is created from a template and the AI action generation LLM call fails
- **THEN** the board is still fully functional with all tasks, dependencies, and subtasks intact
- **AND** subtasks have null action fields (no action buttons shown)

#### Scenario: Subtask actions generated per task in parallel
- **WHEN** a board with 8 tasks (each having 3 subtasks) is created from a template
- **THEN** the system makes up to 8 parallel LLM calls (one per task) to generate subtask actions
- **AND** each subtask's `action_label`, `action_icon`, and `action_prompt` fields are populated based on the LLM response

### Requirement: Save Generated Template Endpoint
The system SHALL expose `POST /api/templates/save-generated` as an authenticated endpoint that saves a previously generated (and optionally user-edited) draft template. The request body SHALL include `title` (required), `description` (optional), `category_id` (optional), `visibility` (optional, default `private`), `tasks` (required, array of task objects with `title`, `description`, `is_goal_node`, `subtasks` array, `depends_on` array of task IDs or indices, and optional `priority` and `estimated_minutes`), and `create_board` (optional, boolean, default `false`). The endpoint SHALL validate the DAG structure (no cycles, exactly one goal node, connected graph), create a BoardTemplate record, and persist all tasks, dependencies, and subtasks. When `create_board` is `true`, the endpoint SHALL additionally create a Goal and Board from the saved template in the same transaction, returning the board ID in the response, and trigger background AI action generation for all subtasks on the new board. The response SHALL include the template details (status 201) and optionally `board_id` and `goal_id` when a board was created.

#### Scenario: Save generated template after DAG preview edits
- **WHEN** a user reviews a generated template in the DAG preview, adds a task, modifies dependencies, and sends `POST /api/templates/save-generated`
- **THEN** a BoardTemplate is created with the edited tasks, dependencies, and subtasks
- **AND** the response status is 201

#### Scenario: Save generated template and create board
- **WHEN** a user sends `POST /api/templates/save-generated` with `create_board: true`
- **THEN** a BoardTemplate is created AND a Goal + Board are created from it in the same transaction
- **AND** the response includes `board_id` and `goal_id`
- **AND** background AI action generation is triggered for all subtasks on the new board

#### Scenario: Save generated template with invalid DAG rejected
- **WHEN** the submitted tasks contain a dependency cycle
- **THEN** the response status is 422 with an error indicating the DAG is invalid

#### Scenario: Save generated template with no goal node rejected
- **WHEN** the submitted tasks have no task with `is_goal_node: true`
- **THEN** the response status is 422 with an error indicating a goal node is required

#### Scenario: Save generated template with disconnected subgraph rejected
- **WHEN** the submitted tasks have a disconnected subgraph (tasks not reachable from or leading to the goal node)
- **THEN** the response status is 422 with an error indicating the graph is disconnected
