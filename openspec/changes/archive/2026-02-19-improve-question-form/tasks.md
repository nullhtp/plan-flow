## 1. Backend Schema Updates
- [ ] 1.1 Update `QuestionSchema` in `backend/app/domains/goals/schemas.py`: change `options` from `list[str] | None` to `list[str]` (required, min 3 items), add `allow_other: bool = True`
- [ ] 1.2 Update `QuestionItem` in `backend/app/domains/ai/schemas.py`: mirror the same changes (options required, allow_other field)
- [ ] 1.3 Verify Pydantic validation rejects questions with null/empty options

## 2. AI Prompt Updates
- [ ] 2.1 Update `QUESTIONS_SYSTEM_PROMPT` in `backend/app/domains/ai/prompts/questions.py`: instruct AI to always generate 3-6 options for every question type, including range-based options for number questions
- [ ] 2.2 Update `FOLLOW_UP_SYSTEM_PROMPT` in the same file: same option generation instructions
- [ ] 2.3 Update `SUB_BOARD_QUESTIONS_SYSTEM_PROMPT` in `backend/app/domains/ai/prompts/sub_board_questions.py`: same instructions for sub-board questions

## 3. Shared Frontend Field Components
- [ ] 3.1 Create `frontend/src/shared/components/question-fields/` directory with shared field components: `OptionField` (single-select with chips + other), `MultiselectOptionField` (multi-select with chips + other), `QuestionFieldWrapper` (label + rationale + required indicator)
- [ ] 3.2 Each component accepts a `compact` prop for sub-board variant styling
- [ ] 3.3 Add `index.ts` barrel export

## 4. Goal Question Form Update
- [ ] 4.1 Refactor `frontend/src/features/goals/components/dynamic-question-form.tsx` to use shared field components
- [ ] 4.2 Remove inline `TextField`, `NumberField`, `SelectField`, `MultiselectField` components
- [ ] 4.3 Implement unified rendering: all question types render as option chips + "Other" text field
- [ ] 4.4 Implement select mutual exclusion: picking option clears "Other", typing in "Other" clears option selection
- [ ] 4.5 Implement multiselect additive behavior: options + "Other" text combined in answer array
- [ ] 4.6 Implement answer serialization: prefix custom text with "other: " to distinguish from preset options

## 5. Sub-Board Question Form Update
- [ ] 5.1 Refactor `frontend/src/features/board/components/SubBoardCreationFlow.tsx` to use the same shared field components with `compact` prop
- [ ] 5.2 Remove inline `CompactTextField`, `CompactNumberField`, `CompactSelectField`, `CompactMultiselectField` components

## 6. Backward Compatibility
- [ ] 6.1 Add frontend fallback: if `options` is null/undefined (existing goals in DB), render a plain text input instead of option chips
- [ ] 6.2 Verify existing goals with null options still render correctly on the goal detail page

## 7. API Regeneration & Testing
- [ ] 7.1 Regenerate Orval types from updated OpenAPI spec (`pnpm run generate:api`)
- [ ] 7.2 Add/update backend tests for QuestionSchema validation (options required, allow_other field)
- [ ] 7.3 Add frontend component tests for the new shared field components
- [ ] 7.4 Manual E2E test: create a new goal and verify all questions show options + "Other" field
