## MODIFIED Requirements

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

## ADDED Requirements

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
