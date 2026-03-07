## ADDED Requirements

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
The system SHALL expose `POST /api/templates/generate` as an authenticated endpoint that uses AI to generate a draft template structure from provided content. The request body SHALL include `content` (required, string — the raw text or extracted document content, max 50,000 characters), `title` (optional, string — a user-provided title hint), and `source_description` (optional, string — describes where the content came from). The endpoint SHALL return a draft template object containing: `suggested_title` (string), `suggested_description` (string), `suggested_category_slug` (string, one of the existing category slugs), `tasks` (array of task objects with `title`, `description`, `is_goal_node`, `subtasks` array, and `depends_on` array of task indices), and `task_count` (integer). The generated structure SHALL form a valid DAG with exactly one goal node. The endpoint SHALL return 422 if the content is empty or too short to generate a meaningful template (minimum 20 characters).

#### Scenario: Generate template from plain text
- **WHEN** an authenticated user sends `POST /api/templates/generate` with `{"content": "Steps to plan a wedding: book venue, choose catering, send invitations, arrange flowers..."}`
- **THEN** the response contains a draft template with tasks forming a valid DAG, a suggested title, description, and category

#### Scenario: Generate template from extracted document content
- **WHEN** a user sends `POST /api/templates/generate` with content extracted from a PDF project plan
- **THEN** the response contains a structured template reflecting the document's steps and dependencies

#### Scenario: Content too short
- **WHEN** a user sends `POST /api/templates/generate` with `{"content": "hello"}`
- **THEN** the response status is 422 with an error indicating the content is too short

#### Scenario: Generated structure is a valid DAG
- **WHEN** template generation completes
- **THEN** the tasks form a valid directed acyclic graph with exactly one goal node, validated via the same Kahn's algorithm used for board generation

### Requirement: Save Generated Template Endpoint
The system SHALL expose `POST /api/templates/save-generated` as an authenticated endpoint that saves a previously generated (and optionally user-edited) draft template. The request body SHALL include `title` (required), `description` (optional), `category_id` (optional), `visibility` (optional, default `private`), and `tasks` (required, array of task objects with the same structure as the generate endpoint output). The endpoint SHALL validate the DAG structure, create a BoardTemplate record, and persist all tasks, dependencies, and subtasks. The response SHALL be identical to the existing `POST /api/templates` response (status 201 with template details).

#### Scenario: Save generated template after preview
- **WHEN** a user reviews a generated template, edits some task titles, and sends `POST /api/templates/save-generated`
- **THEN** a BoardTemplate is created with the edited tasks, dependencies, and subtasks
- **AND** the response status is 201

#### Scenario: Save generated template with invalid DAG rejected
- **WHEN** the submitted tasks contain a dependency cycle
- **THEN** the response status is 422 with an error indicating the DAG is invalid

#### Scenario: Save generated template with no goal node rejected
- **WHEN** the submitted tasks have no task with `is_goal_node: true`
- **THEN** the response status is 422 with an error indicating a goal node is required

### Requirement: Template Generation UI
The system SHALL add a "Generate Template" button on the `/templates` page that opens a multi-step generation flow. Step 1 (Input): A form with three input tabs — "Text" (textarea for pasting or typing content), "Document" (file upload for PDF, DOCX, TXT, MD), and "URL" (text input for a webpage URL). An optional title field is shown above the tabs. Step 2 (Generating): A loading state shown while the AI generates the template structure. Step 3 (Preview & Edit): The generated template is displayed as an editable task list showing task titles, descriptions, subtasks, and dependency relationships. Users can edit task titles and descriptions, add/remove subtasks, and modify the suggested title, description, category, and visibility. A "Save Template" button persists the template. The flow SHALL show appropriate error states for extraction failures, generation failures, and validation errors.

#### Scenario: User generates template from pasted text
- **WHEN** a user clicks "Generate Template", selects the "Text" tab, pastes a project description, and clicks "Generate"
- **THEN** the AI generates a template and the preview step shows the task structure for editing

#### Scenario: User generates template from uploaded document
- **WHEN** a user clicks "Generate Template", selects the "Document" tab, uploads a PDF, and clicks "Generate"
- **THEN** the document content is extracted, the AI generates a template, and the preview step is shown

#### Scenario: User generates template from URL
- **WHEN** a user clicks "Generate Template", selects the "URL" tab, enters a URL, and clicks "Generate"
- **THEN** the URL content is fetched, the AI generates a template, and the preview step is shown

#### Scenario: User edits and saves generated template
- **WHEN** a user modifies task titles in the preview step and clicks "Save Template"
- **THEN** the template is saved with the user's modifications

#### Scenario: Generation error shown to user
- **WHEN** the AI generation fails (timeout, invalid content)
- **THEN** an error message is shown with a "Try Again" option
