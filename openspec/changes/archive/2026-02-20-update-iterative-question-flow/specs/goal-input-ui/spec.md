## MODIFIED Requirements
### Requirement: Dynamic Question Form Renderer
The system SHALL render AI-generated questions as a growing, multi-round form with a unified options-based layout. The form SHALL support unlimited question-answer rounds. Each completed round SHALL be displayed as a collapsible read-only section above the current round's editable questions. The current round's questions SHALL use the same options-based layout as before: every question, regardless of type (`text`, `select`, `multiselect`, `number`), SHALL display its `options` as clickable chips or cards, followed by an always-visible "Other" text input field below the options. Each question SHALL display its `text` as the field label and its `rationale` as helper text below the field. Required questions SHALL be marked with a visual indicator. The form SHALL include a "Continue" submit button for the current round that is disabled until all required fields have values. After submitting a round, the AI generates new follow-up questions which appear below the now read-only previous round.

For `select` and `text` type questions (single-choice): selecting an option SHALL deselect the "Other" text input, and typing in "Other" SHALL deselect any selected option. The submitted value SHALL be either the selected option string or `"other: <user text>"`.

For `multiselect` type questions (multi-choice): options and "Other" text SHALL be additive. The user MAY select multiple options AND type additional text in "Other". The submitted value SHALL be an array of selected option strings, with `"other: <user text>"` appended if the user typed in the "Other" field.

For `number` type questions: the options SHALL display AI-generated ranges as chips (same behavior as `select`). Selecting a range option SHALL deselect "Other", and typing in "Other" SHALL deselect the range. The submitted value SHALL be either the selected range string or `"other: <user text>"`.

When a question has `allow_other` set to `false`, the "Other" text field SHALL NOT be rendered (only the option chips are shown).

When a question has null or empty `options` (backward compatibility with existing goals), the field SHALL fall back to rendering a plain text input without option chips.

The question field components SHALL be extracted into shared components under `frontend/src/shared/components/question-fields/` so both the goal question form and sub-board question form can reuse them. The shared components SHALL accept a `compact` prop for smaller sub-board variant styling.

#### Scenario: Growing form with multiple rounds
- **WHEN** the user has completed rounds 1 and 2 and is viewing round 3 questions
- **THEN** rounds 1 and 2 are displayed as collapsible read-only sections above the round 3 editable question fields

#### Scenario: Read-only round section collapsed by default
- **WHEN** a round's answers have been submitted
- **THEN** the round section shows a collapsed header with the round number and number of questions answered, expandable to see full Q&A details

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
The system SHALL support a growing form pattern for unlimited iterative follow-up questions. After the user submits answers for any round, the AI automatically generates 2-4 new follow-up questions that appear below the submitted round. Previously answered rounds SHALL become read-only collapsible sections with an "Edit" button. Clicking "Edit" on round N SHALL make that round's answers editable and remove all subsequent rounds (N+1, N+2, etc.) from both the UI and the backend. Re-submitting the edited round SHALL trigger re-generation of follow-up questions from that point. The form SHALL auto-scroll to the newly generated questions after each round submission. A loading indicator SHALL appear below the submitted answers while the AI generates the next batch of questions.

#### Scenario: Follow-up questions appear below submitted round
- **WHEN** the user submits round 1 answers
- **THEN** round 1 becomes a read-only collapsible section, a loading indicator appears, and then 2-4 new follow-up questions appear below as round 2

#### Scenario: Multiple rounds displayed as growing form
- **WHEN** the user has completed 5 rounds
- **THEN** rounds 1-4 are read-only collapsible sections and round 5 questions are the active editable form

#### Scenario: User edits earlier round discards later rounds
- **WHEN** the user clicks "Edit" on round 2 while rounds 3-5 exist
- **THEN** rounds 3-5 are removed from the UI and from `ai_context` on the backend, and round 2 becomes editable

#### Scenario: Re-submitting edited round generates fresh follow-ups
- **WHEN** the user edits round 2 answers and re-submits
- **THEN** the AI generates new follow-up questions as round 3, potentially different from the previous round 3

#### Scenario: Auto-scroll to new questions
- **WHEN** new follow-up questions are generated after a round submission
- **THEN** the page smoothly scrolls down to bring the new questions into view

#### Scenario: Loading indicator during follow-up generation
- **WHEN** the user submits a round and the AI is generating follow-up questions
- **THEN** a loading indicator (e.g., skeleton or spinner) is displayed below the submitted answers section

## ADDED Requirements

### Requirement: Persistent Generate Board Footer
The system SHALL display a sticky footer bar containing a "Generate Board" button and a readiness indicator after the user has answered at least the first round of questions. The footer SHALL be fixed to the bottom of the viewport and visible at all times during the iterative questioning flow. The "Generate Board" button SHALL trigger board generation using all collected Q&A data. The footer SHALL NOT appear before the first round is answered (during the initial question display). When the user clicks "Generate Board", the wizard SHALL transition to the `generating` step that displays the full-screen board generation progress view (see `board-generation-progress` spec).

#### Scenario: Footer appears after first round answered
- **WHEN** the user submits answers for round 1
- **THEN** a sticky footer bar appears at the bottom of the viewport with the readiness indicator and "Generate Board" button

#### Scenario: Footer not visible before first round answered
- **WHEN** the user is viewing the initial questions (round 1) but has not submitted yet
- **THEN** no sticky footer is visible

#### Scenario: Generate Board triggers generation from any round
- **WHEN** the user clicks "Generate Board" after completing round 3
- **THEN** the wizard transitions to the `generating` step, using all Q&A data from rounds 1-3 for board generation

#### Scenario: Footer persists across rounds
- **WHEN** the user is on round 5 of questioning
- **THEN** the sticky footer is still visible with the updated readiness score

### Requirement: Readiness Indicator Display
The system SHALL display a visual readiness indicator in the sticky footer that communicates how well-prepared the board generation will be based on the information collected so far. The indicator SHALL show: a circular progress ring displaying the readiness score as a percentage (0-100%), the list of covered dimensions as small tags or chips inside or near the ring, and the readiness summary text below the ring. The readiness data SHALL be updated after each round of answers, using the `readiness` field from the latest answer submission response. The visual styling SHALL use color coding: red/orange for scores below 0.4, yellow for 0.4-0.7, and green for 0.7+. The indicator SHALL be compact enough to fit in the sticky footer alongside the "Generate Board" button.

#### Scenario: Low readiness displayed after round 1
- **WHEN** the readiness score is 0.25 after round 1
- **THEN** the indicator shows a 25% progress ring in red/orange color with uncovered dimension tags

#### Scenario: Medium readiness displayed after round 3
- **WHEN** the readiness score is 0.6 after round 3
- **THEN** the indicator shows a 60% progress ring in yellow color with covered dimension tags

#### Scenario: High readiness displayed after round 5
- **WHEN** the readiness score is 0.9 after round 5
- **THEN** the indicator shows a 90% progress ring in green color with most dimensions covered

#### Scenario: Readiness updates after each round
- **WHEN** the user submits round 4 answers and receives a readiness score of 0.75
- **THEN** the indicator updates from its previous value to show 75% with the new covered/uncovered dimensions

### Requirement: Removed Summary Step
The system SHALL NOT display a separate post-answer summary page. The growing question form with its read-only previous rounds serves as the summary. The "Generate Board" button in the sticky footer replaces the summary page's generate button. The `GoalSummary` component is no longer used in the goal creation wizard flow. When a user navigates to a goal in `questioning` status that has answered rounds, the growing form SHALL display all previous rounds as read-only collapsible sections with the next batch of questions ready to answer, plus the sticky generate footer.

#### Scenario: No summary page after answering
- **WHEN** the user answers all current questions
- **THEN** new follow-up questions appear below (no separate summary page is shown)

#### Scenario: Returning to a goal with answered rounds
- **WHEN** a user navigates to a goal in `questioning` status that has 3 completed rounds and a 4th round of unanswered questions
- **THEN** rounds 1-3 are displayed as read-only collapsible sections, round 4 questions are editable, and the sticky footer shows the readiness indicator

## REMOVED Requirements
### Requirement: Post-Answer Summary View
**Reason**: The separate summary step is replaced by the growing question form with its read-only previous rounds and the sticky Generate Board footer. The growing form serves as both the question input and the summary.
**Migration**: Remove the `GoalSummary` component usage from the goal creation wizard. The component file may be kept for potential use in other contexts (e.g., goal detail page read-only view) but is no longer part of the creation flow.
