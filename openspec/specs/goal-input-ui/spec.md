# goal-input-ui Specification

## Purpose
TBD - created by archiving change add-goal-understanding. Update Purpose after archive.
## Requirements
### Requirement: New Goal Page
The system SHALL provide a "New Goal" page accessible to authenticated users at route `/goals/new`. The page SHALL display a free-text input field for entering a goal description and a submit button. Below the input, the page SHALL display 4-6 clickable example goal suggestions (e.g., "Move from Berlin to Lisbon", "Learn conversational Japanese in 6 months", "Launch an MVP for my SaaS"). Clicking an example SHALL populate the input field with that text. The page SHALL use the application's existing Shadcn/ui components and Tailwind styling.

#### Scenario: User navigates to new goal page
- **WHEN** an authenticated user navigates to `/goals/new`
- **THEN** the page displays a text input, a submit button, and example goal suggestions

#### Scenario: User clicks an example goal
- **WHEN** the user clicks an example goal suggestion
- **THEN** the input field is populated with the example text and the user can edit it before submitting

#### Scenario: Unauthenticated user redirected
- **WHEN** an unauthenticated user navigates to `/goals/new`
- **THEN** the user is redirected to the login page

### Requirement: Goal Submission Loading State
The system SHALL display a loading state after the user submits a goal, while the AI classification and question generation pipeline runs. The loading state SHALL disable the submit button and show a visual indicator (e.g., spinner or skeleton) to communicate that AI processing is in progress. The loading state SHALL have clear messaging (e.g., "Understanding your goal...").

#### Scenario: Loading displayed during AI processing
- **WHEN** the user submits a goal and the API call is in progress
- **THEN** the submit button is disabled, a loading indicator is visible, and a message indicates AI processing

#### Scenario: Loading state ends on success
- **WHEN** the API returns successfully with questions
- **THEN** the loading state is removed and the dynamic form is displayed

#### Scenario: Loading state ends on error
- **WHEN** the API returns an error
- **THEN** the loading state is removed and an error message is displayed

### Requirement: Vague Goal Rejection Display
The system SHALL display a user-friendly rejection message when the AI determines a goal is too vague. The rejection display SHALL include the AI's explanation of why the goal is too vague and a list of 2-3 clickable refinement suggestions. Clicking a suggestion SHALL populate the goal input field with that suggestion, allowing the user to submit the refined goal.

#### Scenario: Rejection with refinement suggestions displayed
- **WHEN** the API returns a 422 response indicating the goal is too vague
- **THEN** the page displays the rejection reason and 2-3 clickable refinement suggestions

#### Scenario: User clicks a refinement suggestion
- **WHEN** the user clicks a refinement suggestion
- **THEN** the input field is populated with the suggestion text and the user can edit and resubmit

### Requirement: Dynamic Question Form Renderer
The system SHALL render AI-generated questions as a dynamic form supporting four field types: `text` (single-line text input), `select` (dropdown with predefined options), `multiselect` (checkbox group or multi-select with predefined options), and `number` (numeric input). Each question SHALL display its `text` as the field label and its `rationale` as helper text below the field. Required questions SHALL be marked with a visual indicator. The form SHALL include a submit button that is disabled until all required fields have values.

#### Scenario: Text field rendered
- **WHEN** a question has type "text"
- **THEN** a single-line text input is rendered with the question text as label and rationale as helper text

#### Scenario: Select field rendered
- **WHEN** a question has type "select" with options ["Low", "Medium", "High"]
- **THEN** a dropdown or radio group is rendered with the provided options

#### Scenario: Multiselect field rendered
- **WHEN** a question has type "multiselect" with options ["Budget", "Timeline", "Quality"]
- **THEN** a checkbox group or multi-select is rendered allowing multiple selections

#### Scenario: Number field rendered
- **WHEN** a question has type "number"
- **THEN** a numeric input is rendered that accepts only numeric values

#### Scenario: Required field validation
- **WHEN** a required question has no value
- **THEN** the submit button is disabled and the field is visually marked as required

### Requirement: Growing Form with Follow-up Questions
The system SHALL support a growing form pattern for adaptive follow-up questions. After the user submits initial answers, if the API returns follow-up questions, they SHALL appear below the already-answered questions. Previously answered questions SHALL become read-only with an "Edit" option. Clicking "Edit" SHALL make the initial answers editable again and remove any follow-up questions (resetting the follow-up state). The second submission of answers (round 2) SHALL always complete the questioning phase.

#### Scenario: Follow-up questions appear below initial answers
- **WHEN** the user submits round 1 answers and the API returns follow-up questions
- **THEN** the initial answers are displayed as read-only above the new follow-up question fields

#### Scenario: User edits initial answers
- **WHEN** the user clicks "Edit" on the read-only initial answers section
- **THEN** the initial answers become editable again, follow-up questions are removed, and the form resets to round 1

#### Scenario: Round 2 submission completes questioning
- **WHEN** the user submits round 2 answers (follow-up answers)
- **THEN** the form transitions to the post-answer summary view

### Requirement: Answer Submission Loading State
The system SHALL display a loading state after the user submits answers, while the API processes the answers and optionally generates follow-up questions. The loading indicator SHALL appear below the submitted answers section.

#### Scenario: Loading during answer processing
- **WHEN** the user submits answers and the API call is in progress
- **THEN** a loading indicator is displayed and the submit button is disabled

### Requirement: Post-Answer Summary View
After the questioning phase is complete (all answers submitted, goal status is `answered`), the system SHALL display a summary view showing the goal title, original input, and all questions with their answers. The summary SHALL include a "Generate Board" button that is visually present but disabled with a tooltip or message indicating board generation is coming soon (M3). The summary view SHALL be accessible by navigating to the goal's page when it is in `answered` status.

#### Scenario: Summary displayed after questioning complete
- **WHEN** the user completes all answer rounds and the goal status transitions to `answered`
- **THEN** the page displays a summary of the goal, all questions, and all answers

#### Scenario: Generate Board button present but disabled
- **WHEN** the summary view is displayed
- **THEN** a "Generate Board" button is visible but disabled with a message like "Board generation coming soon"

#### Scenario: Summary accessible on return visit
- **WHEN** a user navigates to a goal that is in `answered` status
- **THEN** the summary view is displayed with all previously submitted data

### Requirement: AI Error Handling
The system SHALL handle AI pipeline errors gracefully in the UI. When the API returns an error due to AI failure (timeout, malformed output after retries, provider error), the page SHALL display a user-friendly error message with a "Try Again" button that re-submits the last request. The error message SHALL NOT expose technical details (no stack traces, no raw error messages from the LLM provider).

#### Scenario: AI timeout error displayed
- **WHEN** the API returns a 503 or 504 error due to AI timeout
- **THEN** the page displays a message like "Our AI is taking longer than expected. Please try again." with a retry button

#### Scenario: Generic AI error displayed
- **WHEN** the API returns a 500 error due to AI processing failure
- **THEN** the page displays a message like "Something went wrong while processing your goal. Please try again." with a retry button

#### Scenario: Retry re-submits the request
- **WHEN** the user clicks the "Try Again" button after an error
- **THEN** the previous request (goal creation or answer submission) is re-sent to the API

### Requirement: Goal Routes and Navigation
The system SHALL add frontend routes for the goal creation flow: `/goals/new` (new goal page) and `/goals/:id` (goal detail page that renders the appropriate view based on goal status). The authenticated home page (`/`) SHALL include a navigation element (e.g., button or card) to access `/goals/new`. All goal routes SHALL be protected by the existing auth route wrapper.

#### Scenario: Navigation from home to new goal
- **WHEN** an authenticated user is on the home page
- **THEN** a visible element links to `/goals/new`

#### Scenario: Goal detail route renders based on status
- **WHEN** a user navigates to `/goals/:id`
- **AND** the goal is in `questioning` status
- **THEN** the dynamic question form is rendered with current questions

#### Scenario: Goal detail route renders summary for answered goal
- **WHEN** a user navigates to `/goals/:id`
- **AND** the goal is in `answered` status
- **THEN** the post-answer summary view is rendered

