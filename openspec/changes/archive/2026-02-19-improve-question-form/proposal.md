# Change: Improve question form with always-on options and free-text fallback

## Why
The current question form has bare text/number inputs that provide no guidance to users. Users often stare at open-ended fields without knowing what kind of answer is expected. By requiring the AI to always generate selectable options for every question type and adding a persistent "Other" free-text field, we make the form faster to complete, reduce cognitive load, and still preserve full flexibility for custom answers.

## What Changes
- **AI pipeline**: All question types (`text`, `select`, `multiselect`, `number`) MUST always include a non-empty `options` array. Number questions become select-with-ranges (e.g., "$1k-5k", "$5k-10k"). Text questions get AI-suggested answers as selectable options.
- **Question schema**: `options` field changes from nullable to always-required (non-null, non-empty list). A new `allow_other` boolean field (default `true`) signals that the UI should render a free-text "Other" input alongside the options.
- **Frontend form renderer**: Unified rendering — every question shows clickable option chips/cards plus an always-visible "Other" text field below. Select = one option OR custom text (mutually exclusive). Multiselect = multiple options AND/OR custom text (additive).
- **Sub-board question form**: Same improvements applied. Shared field components extracted to eliminate duplication between goal form and sub-board form.
- **Prompts**: Updated to instruct AI to always generate 3-6 options per question, including range-based options for numeric questions.

## Impact
- Affected specs: `ai-pipeline`, `goal-input-ui`, `goal-management`
- Affected code:
  - `backend/app/domains/goals/schemas.py` (QuestionSchema)
  - `backend/app/domains/ai/schemas.py` (QuestionItem, QuestionsOutput)
  - `backend/app/domains/ai/prompts/questions.py` (question generation prompts)
  - `backend/app/domains/ai/prompts/sub_board_questions.py` (sub-board question prompts)
  - `frontend/src/features/goals/components/dynamic-question-form.tsx` (field renderers)
  - `frontend/src/features/board/components/SubBoardCreationFlow.tsx` (compact field renderers)
  - `frontend/src/api/generated/` (regenerated from updated OpenAPI spec)
- **BREAKING**: `options` field changes from `list[str] | None` to `list[str]` (always non-null). Existing goals with null options in `ai_context` need graceful handling (fallback to empty array in UI).
