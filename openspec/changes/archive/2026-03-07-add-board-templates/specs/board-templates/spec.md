## ADDED Requirements

### Requirement: Template Category Data Model
The system SHALL store template categories in a `template_category` table with fields: `id` (UUID primary key), `name` (string, unique), `slug` (string, unique, kebab-case), `description` (string, nullable), `icon` (string, nullable, semantic icon category), `display_order` (integer, for sorting), `created_at` (timestamptz). Categories SHALL be system-managed — only seeded or added via migrations, not user-created.

#### Scenario: Category exists after seeding
- **WHEN** the database is seeded with initial categories
- **THEN** categories like "Career", "Travel", "Health & Fitness", "Education", "Finance", "Home & Living", "Projects", "Events", "Personal Development", and "Other" exist with unique slugs and display_order values

#### Scenario: Categories returned in display order
- **WHEN** the system retrieves all categories
- **THEN** they are returned sorted by `display_order` ascending

### Requirement: Board Template Data Model
The system SHALL store board templates in a `board_template` table with fields: `id` (UUID primary key), `user_id` (FK to user, indexed — the creator), `category_id` (FK to template_category, nullable, indexed), `title` (string, max 200), `description` (text, nullable, max 1000), `visibility` (string, default `private`, one of `private` | `public`), `source_board_id` (UUID, nullable — the board it was created from, not a FK to allow source deletion), `task_count` (integer, computed at creation time), `created_at` (timestamptz), `updated_at` (timestamptz). Indexes SHALL exist on `user_id`, `category_id`, and `visibility`.

#### Scenario: Template created from a board
- **WHEN** a user saves their board as a template with title "Relocation Plan" and visibility "private"
- **THEN** a BoardTemplate record is created with the user's ID, the provided title, `visibility: "private"`, `source_board_id` set to the board's ID, and `task_count` reflecting the number of tasks in the source board

#### Scenario: Template exists after source board deleted
- **WHEN** the source board of a template is deleted
- **THEN** the template record remains unchanged (source_board_id is not a FK)

### Requirement: Template Task Data Model
The system SHALL store template tasks in a `template_task` table with fields: `id` (UUID primary key), `template_id` (FK to board_template, on-delete cascade, indexed), `title` (string), `description` (text, default empty), `is_goal_node` (boolean, default false), `priority` (string, nullable), `estimated_minutes` (integer, nullable), `created_at` (timestamptz). Each template SHALL have exactly one task with `is_goal_node: true`.

#### Scenario: Template tasks created from board
- **WHEN** a board with 10 tasks is saved as a template
- **THEN** 10 TemplateTask records are created, each mirroring the source task's title, description, is_goal_node, priority, and estimated_minutes

#### Scenario: Template cascade-deletes tasks
- **WHEN** a template is deleted
- **THEN** all its TemplateTask records are cascade-deleted

### Requirement: Template Task Dependency Data Model
The system SHALL store template task dependencies in a `template_task_dependency` table with fields: `id` (UUID primary key), `template_id` (FK to board_template, on-delete cascade, indexed), `dependent_task_id` (FK to template_task, on-delete cascade), `dependency_task_id` (FK to template_task, on-delete cascade), `created_at` (timestamptz). A unique constraint SHALL exist on (`dependent_task_id`, `dependency_task_id`).

#### Scenario: Template dependencies created from board
- **WHEN** a board with 15 dependency edges is saved as a template
- **THEN** 15 TemplateTaskDependency records are created mirroring the board's dependency structure

### Requirement: Template Subtask Data Model
The system SHALL store template subtasks in a `template_subtask` table with fields: `id` (UUID primary key), `template_task_id` (FK to template_task, on-delete cascade, indexed), `title` (string), `position` (varchar(50), fractional index), `created_at` (timestamptz). Template subtasks capture the structure of the original subtasks but do not copy action fields (action_label, action_icon, action_prompt) as those are AI-generated and context-specific.

#### Scenario: Template subtasks created from board
- **WHEN** a task with 3 subtasks is part of a board saved as a template
- **THEN** 3 TemplateSubtask records are created with the subtasks' titles and positions

### Requirement: Template Alembic Migration
The system SHALL include an Alembic migration that creates the `template_category`, `board_template`, `template_task`, `template_task_dependency`, and `template_subtask` tables with all specified columns, foreign keys, indexes, and constraints. The migration SHALL seed the `template_category` table with the initial set of categories.

#### Scenario: Migration creates all template tables
- **WHEN** `alembic upgrade head` is run
- **THEN** the `template_category`, `board_template`, `template_task`, `template_task_dependency`, and `template_subtask` tables exist with all specified columns, foreign keys, and indexes
- **AND** the `template_category` table contains the seeded categories

### Requirement: List Categories Endpoint
The system SHALL expose `GET /api/templates/categories` as a public endpoint (no authentication required) that returns all template categories ordered by `display_order`. Each category SHALL include `id`, `name`, `slug`, `description`, `icon`, and `template_count` (number of public templates in the category).

#### Scenario: Retrieve categories with template counts
- **WHEN** any user sends `GET /api/templates/categories`
- **THEN** the response contains all categories ordered by display_order, each with a `template_count` of public templates

### Requirement: Create Template Endpoint
The system SHALL expose `POST /api/templates` as an authenticated endpoint that creates a template from an existing board. The request body SHALL include `board_id` (required), `title` (required, max 200), `description` (optional, max 1000), `category_id` (optional), and `visibility` (optional, default `private`). The endpoint SHALL validate that: the board exists and belongs to the authenticated user, the board has at least one task. The endpoint SHALL snapshot the board's tasks, dependencies, and subtasks into template tables in a single transaction.

#### Scenario: Create template from own board
- **WHEN** an authenticated user sends `POST /api/templates` with `{"board_id": "...", "title": "My Relocation Plan", "visibility": "private"}`
- **THEN** a template is created with all tasks, dependencies, and subtasks from the board
- **AND** the response status is 201 with the template details

#### Scenario: Create template from another user's board rejected
- **WHEN** user A sends `POST /api/templates` with board_id belonging to user B
- **THEN** the response status is 404

#### Scenario: Create template from empty board rejected
- **WHEN** a user sends `POST /api/templates` for a board with no tasks
- **THEN** the response status is 422 with an error indicating the board has no tasks

### Requirement: List Templates Endpoint
The system SHALL expose `GET /api/templates` as an authenticated endpoint that returns templates based on query parameters. Query parameters: `visibility` (optional, `public` | `mine`, default `public`), `category` (optional, category slug), `search` (optional, keyword search on title and description), `page` (optional, default 1), `per_page` (optional, default 20, max 50). When `visibility=public`, returns all public templates. When `visibility=mine`, returns all templates owned by the authenticated user (both public and private). Results SHALL be ordered by `created_at` descending. Each template in the response SHALL include: `id`, `title`, `description`, `visibility`, `category` (object with `id`, `name`, `slug`), `task_count`, `creator` (object with `id`, `username`), `created_at`.

#### Scenario: Browse public templates
- **WHEN** an authenticated user sends `GET /api/templates?visibility=public`
- **THEN** the response contains public templates from all users, ordered by newest first

#### Scenario: Browse public templates by category
- **WHEN** a user sends `GET /api/templates?visibility=public&category=travel`
- **THEN** the response contains only public templates in the "Travel" category

#### Scenario: Search templates by keyword
- **WHEN** a user sends `GET /api/templates?search=relocation`
- **THEN** the response contains templates whose title or description contains "relocation" (case-insensitive)

#### Scenario: List own templates
- **WHEN** a user sends `GET /api/templates?visibility=mine`
- **THEN** the response contains all templates created by the user, including private ones

#### Scenario: Pagination
- **WHEN** there are 30 public templates and a user sends `GET /api/templates?page=2&per_page=10`
- **THEN** the response contains templates 11-20 and includes pagination metadata (total, page, per_page, total_pages)

### Requirement: Get Template Detail Endpoint
The system SHALL expose `GET /api/templates/:id` as an authenticated endpoint that returns the full template with its tasks, dependencies, and subtasks. Public templates SHALL be accessible by any authenticated user. Private templates SHALL only be accessible by their creator. The response SHALL include the template metadata plus nested `tasks` (with subtasks) and `edges` (dependency pairs).

#### Scenario: View public template detail
- **WHEN** any authenticated user sends `GET /api/templates/:id` for a public template
- **THEN** the response contains the template with all tasks, subtasks, and dependency edges

#### Scenario: View own private template detail
- **WHEN** the creator sends `GET /api/templates/:id` for their private template
- **THEN** the response contains the full template details

#### Scenario: View another user's private template rejected
- **WHEN** user A sends `GET /api/templates/:id` for user B's private template
- **THEN** the response status is 404

### Requirement: Update Template Endpoint
The system SHALL expose `PATCH /api/templates/:id` as an authenticated endpoint that updates template metadata. Updatable fields: `title`, `description`, `category_id`, `visibility`. Only the template creator SHALL be allowed to update. The endpoint SHALL NOT allow updating the template's task structure (tasks, dependencies, subtasks are immutable after creation).

#### Scenario: Update template visibility to public
- **WHEN** the creator sends `PATCH /api/templates/:id` with `{"visibility": "public"}`
- **THEN** the template visibility is updated to public

#### Scenario: Update template by non-creator rejected
- **WHEN** user A sends `PATCH /api/templates/:id` for user B's template
- **THEN** the response status is 404

### Requirement: Delete Template Endpoint
The system SHALL expose `DELETE /api/templates/:id` as an authenticated endpoint that deletes a template and all its tasks, dependencies, and subtasks (via cascade). Only the template creator SHALL be allowed to delete.

#### Scenario: Delete own template
- **WHEN** the creator sends `DELETE /api/templates/:id`
- **THEN** the template and all associated records are deleted
- **AND** the response status is 204

#### Scenario: Delete another user's template rejected
- **WHEN** user A sends `DELETE /api/templates/:id` for user B's template
- **THEN** the response status is 404

### Requirement: Create Board from Template Endpoint
The system SHALL expose `POST /api/templates/:id/create-board` as an authenticated endpoint that creates a new board (and its parent goal) from a template. The request body SHALL optionally include `title` (override for the board/goal title). The endpoint SHALL: (1) validate the template is accessible (public or owned by user), (2) create a new Goal with `title` set to the provided title or template title, `status` set to `active`, and `ai_context` containing `{"source": "template", "template_id": "<id>"}`, (3) create a new Board linked to the goal, (4) copy all template tasks, dependencies, and subtasks to the new board in a single transaction, (5) return the created board summary. All new tasks SHALL have `status: not_started` and `completed: false` for subtasks.

#### Scenario: Create board from public template
- **WHEN** an authenticated user sends `POST /api/templates/:id/create-board` for a public template
- **THEN** a new goal (status `active`) and board are created with tasks, dependencies, and subtasks copied from the template
- **AND** the response status is 201 with the board ID, goal ID, and title

#### Scenario: Create board from own private template
- **WHEN** the template creator sends `POST /api/templates/:id/create-board` for their private template
- **THEN** a new board is created from the template

#### Scenario: Create board from another user's private template rejected
- **WHEN** user A sends `POST /api/templates/:id/create-board` for user B's private template
- **THEN** the response status is 404

#### Scenario: Create board with custom title
- **WHEN** a user sends `POST /api/templates/:id/create-board` with `{"title": "My Berlin Move"}`
- **THEN** the created goal and board have title "My Berlin Move"

### Requirement: Templates Browse Page
The system SHALL provide a dedicated `/templates` page in the frontend where users can browse, search, and filter templates. The page SHALL display template cards in a grid layout, each showing: title, description (truncated), category badge, task count, and creator name. The page SHALL include: a category filter (sidebar or top bar), a search input for keyword filtering, pagination controls, and a toggle between "Public Templates" and "My Templates" views.

#### Scenario: User browses public templates
- **WHEN** a user navigates to `/templates`
- **THEN** the page displays public templates in a grid, with category filters and a search bar

#### Scenario: User filters by category
- **WHEN** a user selects the "Travel" category filter
- **THEN** the template grid updates to show only templates in the Travel category

#### Scenario: User searches templates
- **WHEN** a user types "relocation" in the search bar
- **THEN** the template grid updates to show matching templates

#### Scenario: User views own templates
- **WHEN** a user toggles to "My Templates" view
- **THEN** the grid shows all templates created by the user, including private ones

### Requirement: Template Detail Page
The system SHALL provide a `/templates/:id` page that shows the full template structure. The page SHALL display: template title, description, category, creator, task count, and a visual preview of the task structure (list or simplified DAG view). The page SHALL include a "Use Template" button that navigates to a confirmation step and then creates a board from the template.

#### Scenario: User views template detail
- **WHEN** a user navigates to `/templates/:id` for a public template
- **THEN** the page displays the template's title, description, category, creator name, and a list of tasks with their subtasks and dependency relationships

#### Scenario: User creates board from template
- **WHEN** a user clicks "Use Template" on the template detail page
- **THEN** a confirmation dialog appears with an optional title override field
- **AND** upon confirmation, a board is created and the user is navigated to the new board

### Requirement: Save Board as Template Action
The system SHALL add a "Save as Template" action to the board view page. The action SHALL open a dialog/modal that collects: title (pre-filled with board title), description (optional), category (dropdown from categories list), and visibility (private/public toggle, default private). Upon submission, the template is created via the API and the user receives a success confirmation with a link to the template.

#### Scenario: User saves board as template
- **WHEN** a user clicks "Save as Template" on a board with 12 tasks
- **THEN** a dialog appears pre-filled with the board title
- **AND** upon submission, a template is created with 12 tasks and the user sees a success message

#### Scenario: Save as template shows error for empty board
- **WHEN** a user tries to save a board with no tasks as a template
- **THEN** the action is disabled or shows an error message
