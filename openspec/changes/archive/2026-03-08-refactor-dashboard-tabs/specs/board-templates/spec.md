## MODIFIED Requirements

### Requirement: Templates Browse Page
The system SHALL embed the templates gallery within the **Templates** tab on the dashboard page (`/`) instead of a standalone `/templates` route. The `/templates` route SHALL be removed. The template detail page (`/templates/:id`) and generation wizard (`/templates/generate`) SHALL remain as separate routes.

The Templates tab content SHALL include: a "+" creation card as the first item in the template grid (clicking navigates to `/templates/generate`), a secondary toggle between "Public Templates" and "My Templates" views, a category filter (horizontal pill buttons), a search input for keyword filtering, pagination controls, and template cards in a responsive grid. The "+" creation card SHALL appear in both "Public Templates" and "My Templates" sub-views.

The "Generate Template" button that previously appeared in the `/templates` page header is replaced by the "+" creation card in the grid. The "Back to Boards" button that previously appeared in the `/templates` page header is no longer needed since templates are now a tab on the same page as boards.

#### Scenario: User browses public templates in dashboard tab
- **WHEN** a user clicks the "Templates" tab on the dashboard
- **THEN** the tab content displays a "+" creation card as the first grid item, followed by public templates, with category filters and a search bar

#### Scenario: User filters by category in templates tab
- **WHEN** a user selects the "Travel" category filter in the Templates tab
- **THEN** the template grid updates to show only templates in the Travel category (the "+" creation card remains first)

#### Scenario: User searches templates in tab
- **WHEN** a user types "relocation" in the search bar within the Templates tab
- **THEN** the template grid updates to show matching templates (the "+" creation card remains first)

#### Scenario: User views own templates in tab
- **WHEN** a user toggles to "My Templates" view within the Templates tab
- **THEN** the grid shows a "+" creation card followed by all templates created by the user, including private ones

#### Scenario: Create template card navigates to generation wizard
- **WHEN** a user clicks the "+" creation card in the Templates tab
- **THEN** the browser navigates to `/templates/generate`

### Requirement: Template Generation UI
The system SHALL provide a "+" creation card as the first item in the Templates tab grid on the dashboard page. Clicking this card SHALL navigate to `/templates/generate` -- a full-page multi-step wizard for template generation. The wizard SHALL have four steps: Step 1 (Input): A form with four input tabs -- "Describe" (textarea for typing what template the user wants, with clickable example suggestions), "Text" (textarea for pasting content), "Document" (file upload for PDF, DOCX, TXT, MD), and "URL" (text input for a webpage URL). An optional title field is shown above the tabs. Step 2 (Questions): An adaptive question form using shared question field components, supporting an initial round of 3-7 questions and one optional follow-up round of 2-4 questions, with a readiness indicator and sticky "Generate Template" footer. Step 3 (Generating): A streaming progress view reusing the BoardGenerationProgress component, showing real-time research, skeleton, and enrichment phases. Step 4 (Preview & Edit): The generated template is displayed as a React Flow DAG (reusing DagView and TaskDetailPanel) with full structural editing: users can edit task titles, descriptions, subtasks, priority, and estimated_minutes; add and remove tasks; create and delete dependency edges. Template metadata fields (title, description, category, visibility) are shown in a save footer with a "Save Template" button and an "Also create a board" checkbox. The flow SHALL show appropriate error states for extraction failures, classification failures, generation failures, and DAG validation errors.

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

### Requirement: Template Generation Full Page
The system SHALL provide a `/templates/generate` page in the frontend that implements a multi-step wizard for template generation. The page SHALL be accessible to authenticated users. The wizard SHALL have the following steps: `input` (content/description input), `questions` (adaptive question form), `generating` (streaming progress view), and `preview` (DAG board preview with editing). The "+" creation card in the Templates tab on the dashboard SHALL navigate to `/templates/generate`. The `GenerateTemplateDialog` component SHALL be removed.

#### Scenario: User navigates to template generation page
- **WHEN** an authenticated user clicks the "+" creation card in the Templates tab on the dashboard
- **THEN** the browser navigates to `/templates/generate` showing the input step

#### Scenario: Unauthenticated user redirected
- **WHEN** an unauthenticated user navigates to `/templates/generate`
- **THEN** the user is redirected to the login page
