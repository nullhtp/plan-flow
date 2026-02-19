# goal-input-ui Specification

## Purpose
Frontend goal creation flow. Covers the new goal page (free-text input with examples), adaptive question form rendering, answer submission with follow-up support, and board generation trigger with loading/error states.
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
The system SHALL render AI-generated questions as a dynamic form with a unified options-based layout. Every question, regardless of type (`text`, `select`, `multiselect`, `number`), SHALL display its `options` as clickable chips or cards, followed by an always-visible "Other" text input field below the options. Each question SHALL display its `text` as the field label and its `rationale` as helper text below the field. Required questions SHALL be marked with a visual indicator. The form SHALL include a submit button that is disabled until all required fields have values (either an option selected or "Other" text entered).

For `select` and `text` type questions (single-choice): selecting an option SHALL deselect the "Other" text input, and typing in "Other" SHALL deselect any selected option. The submitted value SHALL be either the selected option string or `"other: <user text>"`.

For `multiselect` type questions (multi-choice): options and "Other" text SHALL be additive. The user MAY select multiple options AND type additional text in "Other". The submitted value SHALL be an array of selected option strings, with `"other: <user text>"` appended if the user typed in the "Other" field.

For `number` type questions: the options SHALL display AI-generated ranges as chips (same behavior as `select`). Selecting a range option SHALL deselect "Other", and typing in "Other" SHALL deselect the range. The submitted value SHALL be either the selected range string or `"other: <user text>"`.

When a question has `allow_other` set to `false`, the "Other" text field SHALL NOT be rendered (only the option chips are shown).

When a question has null or empty `options` (backward compatibility with existing goals), the field SHALL fall back to rendering a plain text input without option chips.

The question field components SHALL be extracted into shared components under `frontend/src/shared/components/question-fields/` so both the goal question form and sub-board question form can reuse them. The shared components SHALL accept a `compact` prop for smaller sub-board variant styling.

#### Scenario: Text question rendered with suggested options and Other field
- **WHEN** a question has type "text" with options ["Career opportunity", "Better quality of life", "Family reasons", "Adventure"]
- **THEN** four clickable chips are rendered, plus an always-visible "Other" text input below. Selecting a chip deselects the "Other" field. Typing in "Other" deselects any chip.

#### Scenario: Select question rendered with options and Other field
- **WHEN** a question has type "select" with options ["Low", "Medium", "High"]
- **THEN** three clickable chips are rendered, plus an always-visible "Other" text input. Only one selection at a time (chip OR other text).

#### Scenario: Multiselect question rendered with options and additive Other field
- **WHEN** a question has type "multiselect" with options ["Budget", "Timeline", "Quality"]
- **THEN** three clickable chips are rendered (multiple selectable), plus an always-visible "Other" text input. Chips and "Other" text are additive (both contribute to the answer).

#### Scenario: Number question rendered as range chips with Other field
- **WHEN** a question has type "number" with options ["Under $1,000", "$1,000-$2,000", "$2,000-$3,000", "$3,000+"]
- **THEN** four clickable range chips are rendered, plus an always-visible "Other" text input. Selecting a range deselects "Other". Typing in "Other" deselects the range.

#### Scenario: Required field validation with new layout
- **WHEN** a required question has no option selected and no "Other" text entered
- **THEN** the submit button is disabled and the field is visually marked as required

#### Scenario: Question with allow_other false
- **WHEN** a question has `allow_other` set to false
- **THEN** only the option chips are rendered, without the "Other" text field

#### Scenario: Backward compatibility with null options
- **WHEN** a question has null or empty options (from an existing goal in the database)
- **THEN** the field falls back to rendering a plain text input (no chips) to maintain backward compatibility

#### Scenario: Shared components used by both forms
- **WHEN** the goal question form and sub-board question form render questions
- **THEN** both use the same shared question field components from `frontend/src/shared/components/question-fields/`, with the sub-board form passing `compact={true}`

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
After the questioning phase is complete (all answers submitted, goal status is `answered`), the system SHALL display a summary view showing the goal title, original input, and all questions with their answers. The summary SHALL include a "Generate Board" button. When the user clicks "Generate Board", the wizard SHALL transition to a new `generating` step that displays the full-screen board generation progress view (see `board-generation-progress` spec). The summary view SHALL be accessible by navigating to the goal's page when it is in `answered` status.

#### Scenario: Summary displayed after questioning complete
- **WHEN** the user completes all answer rounds and the goal status transitions to `answered`
- **THEN** the page displays a summary of the goal, all questions, and all answers

#### Scenario: Generate Board transitions to generation progress
- **WHEN** the user clicks "Generate Board" on the summary view
- **THEN** the wizard transitions to the `generating` step and the full-screen generation progress view appears with an SSE connection to the board generation stream endpoint

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

### Requirement: Answer Value Serialization for Options-Based Questions
The frontend SHALL serialize answer values with a consistent convention that distinguishes AI-preset options from user-typed custom answers. When the user selects a preset option, the answer value SHALL be the option string exactly as displayed. When the user types a custom answer in the "Other" field, the answer value SHALL be prefixed with `"other: "` (e.g., `"other: My custom answer"`). For multiselect questions, the answer SHALL be an array where preset selections are bare strings and custom text is prefixed (e.g., `["Budget", "Timeline", "other: Personal preference"]`). This convention enables the AI to distinguish between structured selections and free-form input when generating boards.

#### Scenario: Select answer with preset option
- **WHEN** the user selects "Medium" from a select question's options
- **THEN** the submitted answer value is `"Medium"`

#### Scenario: Select answer with custom Other text
- **WHEN** the user types "Very specific requirement" in the "Other" field of a select question
- **THEN** the submitted answer value is `"other: Very specific requirement"`

#### Scenario: Multiselect answer with mixed selections
- **WHEN** the user selects "Budget" and "Timeline" chips and types "Personal preference" in Other
- **THEN** the submitted answer value is `["Budget", "Timeline", "other: Personal preference"]`

#### Scenario: Multiselect answer with only preset options
- **WHEN** the user selects "Budget" and "Quality" without typing in Other
- **THEN** the submitted answer value is `["Budget", "Quality"]`

