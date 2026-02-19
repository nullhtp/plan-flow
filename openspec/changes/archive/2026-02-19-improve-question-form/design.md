## Context
The question form currently supports four field types (text, select, multiselect, number) with options only required for select/multiselect. Text and number fields render as bare inputs with no guidance. The user wants every question to provide selectable options plus a free-text "Other" fallback, making the form faster and more useful while preserving flexibility.

## Goals / Non-Goals
- Goals:
  - Every question renders with clickable options the user can select
  - Every question has a visible free-text "Other" field for custom answers
  - Number questions become range-based selects (e.g., "$1k-5k") instead of bare number inputs
  - Shared question field components between goal form and sub-board form (eliminate duplication)
  - Backward compatibility with existing goals that have null options in `ai_context`
- Non-Goals:
  - Adding new question types (date picker, slider, etc.)
  - Changing the number of questions generated (still 3-7 for goals, 2-4 for sub-boards)
  - Changing the follow-up question flow
  - Changing the answer submission API contract (answers remain `{ [question_id]: value }`)

## Decisions

### Decision: Unified rendering model — all questions are "options + other"
Every question type renders the same way: a set of clickable option chips/cards followed by an always-visible "Other" text input. The `type` field still exists for semantic purposes (the AI knows whether it's generating range options for a number question vs. suggestions for a text question), but the frontend renders them uniformly.

- Alternatives considered:
  - Keep distinct renderers per type (text input, number input, select, multiselect) and just add "Other" to select/multiselect — rejected because the user explicitly wants ALL questions to have options.
  - Remove the `type` field entirely — rejected because `type` is useful as a hint to the AI for generating appropriate options, and for answer value serialization.

### Decision: `options` becomes required (non-null, min length 3)
The `QuestionSchema.options` field changes from `list[str] | None` to `list[str]` with a minimum of 3 items. This is enforced in the Pydantic schema. The AI prompts are updated to always generate options.

- Alternatives considered:
  - Keep `options` nullable and have the frontend generate placeholder options — rejected because the AI generates much better, context-aware options.

### Decision: Select = mutually exclusive with "Other"; Multiselect = additive
For `select` questions: picking an option deselects "Other" text, and typing in "Other" deselects the option. Only one value is submitted.
For `multiselect` questions: options and "Other" text are additive. The submitted value is an array of selected options plus the "Other" text appended if present.

### Decision: Answer value serialization
- `select` with option chosen: `value = "the option string"`
- `select` with other: `value = "other: user typed text"`
- `multiselect` with options: `value = ["Option A", "Option C"]`
- `multiselect` with options + other: `value = ["Option A", "Option C", "other: user typed text"]`
- `text` (now rendered as options): same as `select` — either the option string or `"other: user typed text"`
- `number` (now rendered as range select): same as `select` — either the range string or `"other: user typed text"`

The `"other: "` prefix allows the AI to distinguish user-typed answers from pre-defined options when generating the board.

### Decision: Shared field components in `frontend/src/shared/components/question-fields/`
Extract the four field renderers into shared components so both `DynamicQuestionForm` and `SubBoardCreationFlow` use the same code. The shared components accept a `compact` prop for the sub-board variant.

## Risks / Trade-offs
- **Risk**: Existing goals in the database have `options: null` for text/number questions. **Mitigation**: Frontend treats null/undefined options as empty array and falls back to a plain text input (graceful degradation). No data migration needed.
- **Risk**: AI may generate low-quality options for very open-ended text questions. **Mitigation**: The "Other" field is always visible, so users are never stuck. Prompt engineering can improve option quality over time.
- **Risk**: Slightly larger AI response payload (options for every question). **Mitigation**: 3-6 short strings per question is negligible.

## Open Questions
- None — all design questions resolved via user input.
