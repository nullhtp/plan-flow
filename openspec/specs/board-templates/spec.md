# board-templates Specification

## Purpose
Reusable board templates that users can save from existing boards or generate from text/documents/URLs via AI, browse by category, and use to create new boards instantly — an alternative creation path alongside AI generation. Supports public/private visibility, system-managed categories, full board structure snapshots (tasks, dependencies, subtasks), and AI-powered template generation with content extraction and preview/edit flow.
## Requirements
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
The system SHALL expose `PATCH /api/templates/:id` as an authenticated endpoint that updates template metadata. Updatable fields: `title`, `description`, `category_id`, `visibility`. Only the template creator SHALL be allowed to update. The endpoint SHALL NOT allow updating the template's task structure — structural updates are handled by `PUT /api/templates/:id/structure`.

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

### Requirement: Save Board as Template Action
The system SHALL add a "Save as Template" action to the board view page. The action SHALL open a dialog/modal that collects: title (pre-filled with board title), description (optional), category (dropdown from categories list), and visibility (private/public toggle, default private). Upon submission, the template is created via the API and the user receives a success confirmation with a link to the template.

#### Scenario: User saves board as template
- **WHEN** a user clicks "Save as Template" on a board with 12 tasks
- **THEN** a dialog appears pre-filled with the board title
- **AND** upon submission, a template is created with 12 tasks and the user sees a success message

#### Scenario: Save as template shows error for empty board
- **WHEN** a user tries to save a board with no tasks as a template
- **THEN** the action is disabled or shows an error message

### Requirement: Content Extraction Endpoint
The system SHALL expose `POST /api/templates/extract-content` as an authenticated endpoint that extracts text content from uploaded documents or URLs. The request SHALL accept either a file upload (multipart form data, supported formats: PDF, DOCX, TXT, Markdown) or a `url` field (string). The endpoint SHALL return `{"content": "<extracted text>", "source_type": "file" | "url", "source_name": "<filename or URL>", "char_count": <number>}`. File size limit SHALL be 10 MB. The endpoint SHALL return 422 for unsupported file types or URLs that cannot be fetched.

#### Scenario: Extract content from PDF upload
- **WHEN** an authenticated user uploads a PDF file via `POST /api/templates/extract-content`
- **THEN** the response contains the extracted text content, `source_type: "file"`, the original filename, and the character count

#### Scenario: Extract content from URL
- **WHEN** an authenticated user sends `POST /api/templates/extract-content` with `{"url": "https://example.com/guide"}`
- **THEN** the response contains the fetched and cleaned page content, `source_type: "url"`, the URL as source_name, and the character count

#### Scenario: Unsupported file type rejected
- **WHEN** a user uploads a `.exe` file
- **THEN** the response status is 422 with an error indicating the file type is not supported

#### Scenario: File exceeds size limit
- **WHEN** a user uploads a file larger than 10 MB
- **THEN** the response status is 422 with an error indicating the file is too large

#### Scenario: URL fetch fails
- **WHEN** the provided URL cannot be fetched (timeout, 404, invalid URL)
- **THEN** the response status is 422 with an error describing the fetch failure

### Requirement: Generate Template Endpoint
The system SHALL expose `POST /api/templates/generate` as an authenticated endpoint that uses AI to generate a draft template structure from provided content. This endpoint is **deprecated** in favor of the streaming `POST /api/templates/generate/stream` endpoint but SHALL remain functional for backward compatibility. The request body SHALL include `content` (required, string — the raw text or extracted document content, max 50,000 characters), `title` (optional, string — a user-provided title hint), and `source_description` (optional, string — describes where the content came from). The endpoint SHALL return a draft template object containing: `suggested_title` (string), `suggested_description` (string), `suggested_category_slug` (string, one of the existing category slugs), `tasks` (array of task objects with `title`, `description`, `is_goal_node`, `subtasks` array, and `depends_on` array of task indices), and `task_count` (integer). The generated structure SHALL form a valid DAG with exactly one goal node. The endpoint SHALL return 422 if the content is empty or too short to generate a meaningful template (minimum 20 characters).

#### Scenario: Generate template from plain text (deprecated path)
- **WHEN** an authenticated user sends `POST /api/templates/generate` with `{"content": "Steps to plan a wedding..."}`
- **THEN** the response contains a draft template with tasks forming a valid DAG (single LLM call, no streaming)

#### Scenario: Content too short
- **WHEN** a user sends `POST /api/templates/generate` with `{"content": "hello"}`
- **THEN** the response status is 422 with an error indicating the content is too short

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

### Requirement: Template Generation UI
The system SHALL provide a "Generate Template" button on the `/templates` page that navigates to `/templates/generate` — a full-page multi-step wizard for template generation. The wizard SHALL have four steps: Step 1 (Input): A form with four input tabs — "Describe" (textarea for typing what template the user wants, with clickable example suggestions), "Text" (textarea for pasting content), "Document" (file upload for PDF, DOCX, TXT, MD), and "URL" (text input for a webpage URL). An optional title field is shown above the tabs. Step 2 (Questions): An adaptive question form using shared question field components, supporting an initial round of 3-7 questions and one optional follow-up round of 2-4 questions, with a readiness indicator and sticky "Generate Template" footer. Step 3 (Generating): A streaming progress view reusing the BoardGenerationProgress component, showing real-time research, skeleton, and enrichment phases. Step 4 (Preview & Edit): The generated template is displayed as a React Flow DAG (reusing DagView and TaskDetailPanel) with full structural editing: users can edit task titles, descriptions, subtasks, priority, and estimated_minutes; add and remove tasks; create and delete dependency edges. Template metadata fields (title, description, category, visibility) are shown in a save footer with a "Save Template" button and an "Also create a board" checkbox. The flow SHALL show appropriate error states for extraction failures, classification failures, generation failures, and DAG validation errors.

#### Scenario: User generates template from description
- **WHEN** a user navigates to `/templates/generate`, selects "Describe", types a description, clicks "Continue", answers questions, and clicks "Generate Template"
- **THEN** the streaming progress view shows generation phases, then the DAG preview displays the template for editing

#### Scenario: User generates template from uploaded document
- **WHEN** a user selects "Document", uploads a PDF, clicks "Continue", answers questions, and clicks "Generate Template"
- **THEN** the document content is extracted, questions are generated, and the full streaming generation pipeline runs

#### Scenario: User generates template from URL
- **WHEN** a user selects "URL", enters a URL, clicks "Continue", answers questions, and clicks "Generate Template"
- **THEN** the URL content is fetched, questions are generated, and the full streaming generation pipeline runs

#### Scenario: User edits DAG and saves template
- **WHEN** a user adds a task, modifies a dependency edge, edits task descriptions in the DAG preview, and clicks "Save Template"
- **THEN** the template is saved with all structural and content modifications

#### Scenario: User saves template and creates board
- **WHEN** a user checks "Also create a board" and clicks "Save Template"
- **THEN** the template is saved, a board is created, and the user is navigated to the board

#### Scenario: Generation error shown to user
- **WHEN** the AI generation fails during streaming
- **THEN** an error message is shown with "Try Again" and "Back" options

### Requirement: Template Classification Endpoint
The system SHALL expose `POST /api/templates/classify` as an authenticated endpoint that classifies template input and generates adaptive questions. The request body SHALL include `input_type` (required, one of `"describe"` | `"text"` | `"file"` | `"url"`), `content` (required, string — the user's description or extracted content), and `title` (optional, string). The endpoint SHALL run the goal classification pipeline adapted for template context: detecting domain, complexity, confidence, dimensions, and language from the input. The endpoint SHALL then generate 3-7 structured questions based on the classification, identical in format to goal questions (type, options, rationale, required, allow_other). The endpoint SHALL return a `TemplateClassifyResponse` containing: `session_id` (UUID — identifies this template generation session), `classification` (object with domain, complexity, confidence, dimensions, language, suggested_title), and `questions` (array of question objects). For content-based inputs (`text`, `file`, `url`), the classification SHALL analyze the extracted content and generate questions that clarify the template scope (e.g., team size, customization preferences, scope adjustments). For `describe` inputs, classification SHALL work identically to goal classification. The endpoint SHALL return 422 if content is empty or too short (minimum 20 characters).

#### Scenario: Classify description input
- **WHEN** an authenticated user sends `POST /api/templates/classify` with `{"input_type": "describe", "content": "Wedding planning template with vendor coordination"}`
- **THEN** the response contains a classification (domain "events", dimensions like ["budget", "timeline", "vendors", "guests"]) and 3-7 questions about the template scope

#### Scenario: Classify extracted document content
- **WHEN** an authenticated user sends `POST /api/templates/classify` with `{"input_type": "text", "content": "<extracted project plan text>"}`
- **THEN** the response contains a classification based on the content analysis and questions clarifying how to structure the template (e.g., "What team size is this template for?", "Should budget tracking tasks be included?")

#### Scenario: Content too short
- **WHEN** a user sends `POST /api/templates/classify` with `{"input_type": "describe", "content": "hi"}`
- **THEN** the response status is 422 with an error indicating the content is too short

### Requirement: Template Answers Endpoint
The system SHALL expose `POST /api/templates/answers` as an authenticated endpoint that accepts answers for a template question round and optionally generates one follow-up round. The request body SHALL include `session_id` (required, UUID), `classification` (required, object — the classification from the classify response), `rounds` (required, array of round objects, each containing `questions` and `answers`), `source_content` (optional, string — the original content for content-based inputs), and `round_number` (required, integer — 1 for initial answers, 2 for follow-up answers). When `round_number` is 1, the endpoint SHALL generate 2-4 follow-up questions and a readiness assessment, returning them in the response. When `round_number` is 2, the endpoint SHALL return only the readiness assessment (no further questions, max 2 rounds enforced). The response SHALL include: `questions` (array, empty for round 2), `readiness` (object with `score` float 0-1, `summary` string, `covered_dimensions` array, `uncovered_dimensions` array), and `is_final_round` (boolean).

#### Scenario: Submit round 1 answers with follow-up
- **WHEN** an authenticated user submits answers for round 1 with `round_number: 1`
- **THEN** the response contains 2-4 follow-up questions, a readiness assessment, and `is_final_round: false`

#### Scenario: Submit round 2 answers (final)
- **WHEN** an authenticated user submits answers for round 2 with `round_number: 2`
- **THEN** the response contains an empty questions array, a readiness assessment, and `is_final_round: true`

#### Scenario: Readiness score reflects information completeness
- **WHEN** the user has answered questions covering 4 of 6 identified dimensions
- **THEN** the readiness score is approximately 0.6-0.7 and the summary indicates which dimensions still lack detail

### Requirement: Template Generation SSE Endpoint
The system SHALL expose `POST /api/templates/generate/stream` as an authenticated SSE endpoint that returns `Content-Type: text/event-stream`. The request body SHALL include `session_id` (required), `classification` (required), `rounds` (required, array of Q&A round objects), `source_content` (optional, string), and `title` (optional, string). The endpoint SHALL orchestrate the same multi-step generation pipeline as board generation: (1) research via Tavily if configured, (2) skeleton generation with template-specific prompts incorporating Q&A context and source content, (3) skeleton review, (4) parallel task enrichment. The endpoint SHALL emit the same SSE event types as the board generation stream: `research_started`, `research_progress`, `research_complete`, `skeleton_ready`, `task_enriched`, `generation_complete`, `generation_error`. The `skeleton_ready` event SHALL contain `tasks` (array with `id`, `title`, `is_goal_node`, `description`, `depends_on`), `suggested_title`, `suggested_description`, and `suggested_category_slug`. The `generation_complete` event SHALL contain the full template structure including enriched tasks with subtasks. The endpoint SHALL keep the connection open until `generation_complete` or `generation_error` is emitted.

#### Scenario: Successful template generation stream with research
- **WHEN** an authenticated user sends POST to `/api/templates/generate/stream` with valid session data and Tavily is configured
- **THEN** the response emits `research_started`, research progress events, `research_complete`, `skeleton_ready` with task structure, `task_enriched` events, and `generation_complete` with the full template data

#### Scenario: Successful template generation stream without research
- **WHEN** Tavily is NOT configured
- **THEN** the response emits `skeleton_ready`, `task_enriched` events, and `generation_complete` (no research events)

#### Scenario: Generation error streamed
- **WHEN** skeleton generation fails after all retries
- **THEN** the endpoint emits a `generation_error` event with a user-friendly error message

### Requirement: Template Generation Full Page
The system SHALL provide a `/templates/generate` page in the frontend that implements a multi-step wizard for template generation. The page SHALL be accessible to authenticated users. The wizard SHALL have the following steps: `input` (content/description input), `questions` (adaptive question form), `generating` (streaming progress view), and `preview` (DAG board preview with editing). The "Generate Template" button on the `/templates` page SHALL navigate to `/templates/generate` instead of opening a dialog. The `GenerateTemplateDialog` component SHALL be removed.

#### Scenario: User navigates to template generation page
- **WHEN** an authenticated user clicks "Generate Template" on the `/templates` page
- **THEN** the browser navigates to `/templates/generate` showing the input step

#### Scenario: Unauthenticated user redirected
- **WHEN** an unauthenticated user navigates to `/templates/generate`
- **THEN** the user is redirected to the login page

### Requirement: Template Input Step
The template generation page input step SHALL display four input tabs: "Describe" (a textarea for typing what template the user wants, with 4-6 clickable example suggestions like "Wedding planning with vendor coordination" or "Software development sprint template"), "Text" (a textarea for pasting raw content), "Document" (a file upload area accepting PDF, DOCX, TXT, MD), and "URL" (a text input for a webpage URL). An optional title field SHALL be displayed above the tabs. A "Continue" button SHALL submit the input: for "Describe" and "Text" tabs, the content is sent directly to the classification endpoint; for "Document" and "URL" tabs, content is first extracted via the existing extraction endpoints, then sent to classification. A loading state SHALL be shown during content extraction and classification.

#### Scenario: User enters a template description
- **WHEN** a user selects the "Describe" tab, types "Project management template for a 5-person team", and clicks "Continue"
- **THEN** the content is sent to `POST /api/templates/classify` with `input_type: "describe"` and the wizard transitions to the questions step

#### Scenario: User clicks an example suggestion
- **WHEN** the user clicks the example "Software development sprint template"
- **THEN** the Describe textarea is populated with that text and the user can edit before clicking "Continue"

#### Scenario: User uploads a document
- **WHEN** a user selects the "Document" tab, uploads a PDF, and clicks "Continue"
- **THEN** the document content is extracted via the content extraction endpoint, then sent to classification, and the wizard transitions to the questions step

#### Scenario: User enters a URL
- **WHEN** a user selects the "URL" tab, enters a URL, and clicks "Continue"
- **THEN** the URL content is fetched and extracted, then sent to classification, and the wizard transitions to the questions step

### Requirement: Template Question Step
The template generation page questions step SHALL render the AI-generated questions using the shared question field components (`shared/components/question-fields/`) in `compact` mode. The form SHALL support a growing form pattern with a maximum of 2 rounds: the initial round (3-7 questions) and one optional follow-up round (2-4 questions). After the user submits round 1 answers, round 1 SHALL become a collapsible read-only section and follow-up questions SHALL appear below. A readiness indicator SHALL be displayed in a sticky footer after round 1 is answered, showing the readiness score as a percentage with color coding (green >= 70%, yellow >= 40%, orange < 40%). A "Generate Template" button SHALL be displayed in the sticky footer alongside the readiness indicator. The user MAY click "Generate Template" after completing round 1 (skipping the optional follow-up round) or after completing round 2. Clicking "Generate Template" SHALL transition the wizard to the generating step.

#### Scenario: Initial questions displayed
- **WHEN** the classification returns 5 questions
- **THEN** the questions step renders 5 question fields using the shared components

#### Scenario: Follow-up round after round 1
- **WHEN** the user submits round 1 answers
- **THEN** round 1 becomes a collapsible read-only section, the sticky footer appears with readiness indicator and "Generate Template" button, and 2-4 follow-up questions appear as round 2

#### Scenario: User generates after round 1
- **WHEN** the user clicks "Generate Template" after answering only round 1
- **THEN** the wizard transitions to the generating step using round 1 Q&A data

#### Scenario: User generates after round 2
- **WHEN** the user completes both rounds and clicks "Generate Template"
- **THEN** the wizard transitions to the generating step using both rounds of Q&A data

#### Scenario: Readiness indicator shown
- **WHEN** the readiness score after round 1 is 0.55
- **THEN** the sticky footer shows a 55% progress ring in yellow

### Requirement: Template Generation Progress Step
The template generation page generating step SHALL reuse the `BoardGenerationProgress` component (or its generalized version) and the `useBoardGenerationStream` hook configured to connect to `POST /api/templates/generate/stream`. The progress view SHALL display the same phase text, progress indicators, and task stack as the board generation flow. On `generation_complete`, instead of auto-navigating to a board page, the wizard SHALL transition to the preview step with the generated template data stored in local state. On `generation_error`, the user SHALL see an error message with "Try Again" and "Back" buttons.

#### Scenario: Template generation progress shows research phase
- **WHEN** template generation starts with Tavily configured
- **THEN** the progress view shows "Researching (X/N)..." with the current search query

#### Scenario: Template generation progress shows enrichment
- **WHEN** `skeleton_ready` arrives with 12 tasks
- **THEN** the progress view shows task stack and "Adding details (X/12)..." counter

#### Scenario: Generation complete transitions to preview
- **WHEN** `generation_complete` event is received
- **THEN** the wizard transitions to the preview step (no auto-navigation to a board)

#### Scenario: Generation error with retry
- **WHEN** a `generation_error` event is received
- **THEN** an error message is shown with "Try Again" (restarts generation) and "Back" (returns to input step) buttons

### Requirement: Template DAG Preview Step
The template generation page preview step SHALL display the generated template as a React Flow DAG using the existing `DagView` component in a `template-preview` mode. The DagView SHALL render task nodes with dagre auto-layout, showing the dependency graph visually. Task data SHALL be sourced from local component state (not API-backed board queries). Clicking a task node SHALL open the `TaskDetailPanel` in template-preview edit mode, allowing the user to edit: title, description, subtasks (add, remove, edit titles), priority, and estimated_minutes. The preview SHALL support full structural editing:
- **Add task**: An "Add Task" button SHALL create a new unconnected task node in the graph
- **Remove task**: Tasks SHALL be deletable via the TaskDetailPanel or a context menu, with automatic cleanup of related dependency edges
- **Add dependency**: Users SHALL be able to create new dependency edges by dragging from a source node's handle to a target node's handle (React Flow connection interaction)
- **Remove dependency**: Users SHALL be able to delete edges by clicking them and confirming deletion, or via a context menu
- **Goal node**: Exactly one task MUST remain marked as `is_goal_node: true`. The UI SHALL prevent deleting the goal node without first designating another task as the goal node.

Real-time DAG validation SHALL run after each structural edit. If the edit creates a cycle, the change SHALL be rejected with a visual error message. If no goal node exists, a warning SHALL be displayed.

#### Scenario: Generated template displayed as DAG
- **WHEN** the preview step loads with 15 generated tasks and 20 edges
- **THEN** the DagView renders all tasks as nodes with dependency edges, auto-laid out by dagre

#### Scenario: User edits task details via panel
- **WHEN** the user clicks a task node and modifies the title in the TaskDetailPanel
- **THEN** the task title is updated in local state and the node label updates in the DAG

#### Scenario: User adds a new task
- **WHEN** the user clicks "Add Task"
- **THEN** a new unconnected task node appears in the DAG with a default title "New Task" and the TaskDetailPanel opens for editing

#### Scenario: User creates a dependency edge
- **WHEN** the user drags from task A's output handle to task B's input handle
- **THEN** a new dependency edge is created (B depends on A) and DAG validation runs

#### Scenario: User removes a task
- **WHEN** the user deletes task C which has 2 incoming and 1 outgoing edge
- **THEN** task C and all 3 related edges are removed from the DAG

#### Scenario: Cycle prevention
- **WHEN** the user tries to create an edge from task D to task E, but E already has a path to D
- **THEN** the edge creation is rejected and a toast error "Cannot create dependency: would create a cycle" is shown

#### Scenario: Goal node protection
- **WHEN** the user tries to delete the goal node
- **THEN** the deletion is prevented with a message "Cannot delete the goal node. Designate another task as the goal first."

### Requirement: Template Save and Create Board Actions
The template generation page preview step SHALL display a footer with save actions. The footer SHALL include: template metadata fields (title input pre-filled from AI suggestion, description textarea pre-filled from AI suggestion, category dropdown pre-matched from AI's suggested_category_slug, visibility radio: private/public default private), a primary "Save Template" button, and a checkbox "Also create a board from this template" (default unchecked). When the user clicks "Save Template", the system SHALL validate the DAG structure (valid DAG, exactly one goal node, no cycles, no disconnected subgraphs), then call `POST /api/templates/save-generated` with the full template structure including any user edits and the optional `create_board: true` flag if the checkbox is checked. On success: if `create_board` was checked, navigate to the new board page; otherwise navigate to the saved template's detail page.

#### Scenario: Save template without creating board
- **WHEN** the user clicks "Save Template" without checking "Also create a board"
- **THEN** the template is saved and the user is navigated to `/templates/:id`

#### Scenario: Save template and create board
- **WHEN** the user clicks "Save Template" with "Also create a board" checked
- **THEN** the template is saved, a board is created from it, and the user is navigated to `/boards/:boardId`

#### Scenario: Save with invalid DAG rejected
- **WHEN** the user has introduced a cycle through manual edits and clicks "Save Template"
- **THEN** an error message is shown: "The task structure contains a cycle. Please fix dependencies before saving."

#### Scenario: Save with no goal node rejected
- **WHEN** no task is marked as the goal node and the user clicks "Save Template"
- **THEN** an error message is shown: "Please designate one task as the goal node."

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

