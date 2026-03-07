## MODIFIED Requirements

### Requirement: Generalized Generation Progress Component
The system SHALL provide a generalized `BoardGenerationProgress` component and `useBoardGenerationStream` hook that can be used for main board generation, sub-board generation, and template generation. The hook SHALL accept a configurable SSE URL parameter instead of being hardcoded to the goal-based endpoint. The component SHALL accept an optional `onComplete(boardId: string, data?: GenerationCompleteData)` callback for custom behavior upon generation completion. The `onComplete` callback SHALL receive the full generation result data (including tasks, edges, and subtasks) when available, enabling callers like the template generation page to capture the generated structure for local editing. Both the main board generation page, the sub-board expansion page, and the template generation page SHALL use the same component and hook, ensuring identical visual treatment (progress bar, task stack, phase text, staggered animation, error handling).

#### Scenario: Hook used for main board generation
- **WHEN** the main board generation page initializes the hook
- **THEN** the hook connects to `/api/goals/{goalId}/generate-board/stream` and processes SSE events identically to the current behavior

#### Scenario: Hook used for sub-board generation
- **WHEN** the sub-board expansion page initializes the hook
- **THEN** the hook connects to `/api/tasks/{taskId}/generate-sub-board/stream` and processes SSE events identically to main board generation (same event types, same state transitions)

#### Scenario: Hook used for template generation
- **WHEN** the template generation page initializes the hook
- **THEN** the hook connects to `/api/templates/generate/stream` and processes SSE events identically to main board generation (same event types, same state transitions)

#### Scenario: Identical visual treatment for all three flows
- **WHEN** any flow is in the `enriching` phase with 5 of 10 tasks enriched
- **THEN** all display the same progress bar at 50%, the same task stack with staggered animation, and the same phase text "5 / 10 tasks enriched"

#### Scenario: onComplete receives generation data for templates
- **WHEN** template generation completes and `onComplete` is called
- **THEN** the callback receives the full template structure data (tasks with enriched details, edges, subtasks) for the preview step
