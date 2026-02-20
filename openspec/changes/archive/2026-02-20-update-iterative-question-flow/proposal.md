# Change: Iterative Question Flow with Progressive Deepening

## Why
The current pregeneration flow is limited to a fixed 2-round question cycle (3-7 initial questions + optionally 1 follow-up round). This constrains the AI's ability to gather comprehensive context, especially for complex goals. Users should be able to iterate with the AI as long as they want — the more information the AI harvests, the better the generated board will be. The user should feel in control by deciding when they have provided enough context to generate.

## What Changes
- **Unlimited question rounds**: Remove the 1-round follow-up cap. After each answer submission, the AI automatically generates 2-4 progressively deeper follow-up questions. This repeats indefinitely until the user clicks "Generate Board".
- **Progressive deepening**: Each round's questions become more specific and detailed, leveraging the full history of previous Q&A. The AI avoids repeating covered topics and drills into knowledge gaps.
- **Readiness score**: The AI returns a dimension coverage analysis and confidence score with each question batch. The UI displays a visual readiness indicator (progress ring) showing how well-prepared the board generation will be based on the information collected so far.
- **Always-visible Generate Board button**: After answering the first round, a "Generate Board" button is persistently visible (sticky footer). The user can generate at any time — even with partial information.
- **Growing form UI**: Previous answers are displayed as read-only above each new question batch. The form grows downward with each round. No separate summary page — the form itself serves as the summary.
- **Editable previous answers**: Users can edit answers from any previous round. Editing a round discards all subsequent rounds and triggers re-generation of follow-up questions from that point.
- **Multi-round persistence**: All rounds (questions + answers) are stored as an ordered list in `ai_context`, preserving the full conversation history for board generation.
- **Remove summary step**: The separate post-answer summary view is removed. The growing form with the sticky "Generate Board" button replaces it.

## Impact
- Affected specs: `ai-pipeline`, `goal-management`, `goal-input-ui`
- Affected code:
  - Backend: `app/domains/ai/nodes/questions.py`, `app/domains/ai/prompts/questions.py`, `app/domains/ai/service.py`, `app/domains/ai/schemas.py`, `app/domains/goals/service.py`, `app/domains/goals/router.py`, `app/domains/goals/schemas.py`
  - Frontend: `src/routes/goals.new.tsx`, `src/features/goals/components/dynamic-question-form.tsx`, `src/features/goals/components/goal-summary.tsx` (removed or repurposed), `src/features/goals/hooks/use-goals.ts`
- **BREAKING**: The `POST /api/goals/:id/answers` response schema changes to always include `readiness` data and removes the `is_complete` flag (the questioning phase is never "complete" — the user decides when to generate). Existing goals with round 1/2 data in `ai_context` remain backward compatible.
