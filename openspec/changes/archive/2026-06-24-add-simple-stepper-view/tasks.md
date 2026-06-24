## 1. Interface mode preference + header switch

- [x] 1.1 Add a `useInterfaceMode` hook (`frontend/src/features/board/hooks/`) backed by localStorage key `planflow:board-interface-mode`, returning `mode` (`"simple" | "advanced"`) and a setter; default `"simple"` when unset
- [x] 1.2 Add a top-level Simple/Advanced segmented control to the board header in `frontend/src/routes/boards.$boardId.tsx`
- [x] 1.3 Render the existing Focus/Full toggle only when mode is Advanced; hide it in Simple
- [x] 1.4 Conditionally render `StepperView` (Simple) vs `DagView` (Advanced) in the board route

## 2. Actionable-queue ordering

- [x] 2.1 Add `getStepSequence(tasks, edges)` util (`frontend/src/features/board/utils/`): topological sort (Kahn) over **all** tasks, tie-broken by `created_at`, serializing parallel branches into one linear sequence (no filtering)
- [x] 2.2 Add a helper to pick the default current step (first `in_progress`, else first not-done, else first) and to clamp the step when a task is deleted
- [x] 2.3 Unit tests for ordering, dependency precedence, goal-node-last, and empty-queue cases

## 3. Stepper UI

- [x] 3.1 Build a minimal `StepCard` component: read-only title, read-only description, subtask checklist (toggle only — no add/delete/rename), AI chat, and status buttons (Start / Mark as done + Reset / Reopen). (The shared `TaskDetailContent` extracted from `TaskDetailPanel` is retained for the Advanced panel only.)
- [x] 3.2 Build `StepperView` component: full-screen `StepCard`, Previous/Next controls, sequence-position indicator, and overall completion progress bar
- [x] 3.3 Wire `use-task-mutations` (status) and `use-subtask-mutations` (toggle) into the step; `TaskChat` provides the AI chat
- [x] 3.4 Gate **Next** so it is enabled only when the current task is `done` (with a "complete this task to continue" hint); Previous stays available; marking a task `done` via the status button advances to the next step; checking the **last remaining subtask** of an `in_progress` task auto-marks it `done` and advances; recompute the sequence on board changes and clamp the step when a task is deleted; locked steps show a disabled status indicator
- [x] 3.5 Sub-board task step replaces the subtask checklist with an "Open Sub-Board" action navigating to `/boards/:subBoardId`

## 4. Completion and edge states

- [x] 4.1 Completion screen when the board is complete; reuse the `Celebration` component; add "Back to dashboard" and "View full DAG" actions
- [x] 4.2 Deep link `?task=<id>` lands on that task as the current step in the sequence regardless of status/lock (no mode switch needed)
- [x] 4.3 Graceful fallback when the board has no tasks (prompt to open the full DAG)

## 5. Tests and validation

- [x] 5.1 Component tests for `StepperView` (walks every task as one sequence incl. done & locked, Next gated until done, advance-on-done, completion screen, empty-board fallback, deep-link landing) and for `StepCard` (read-only title/description, status buttons per lifecycle, subtasks toggle-only with no add/delete, sub-board CTA)
- [x] 5.2 Existing suite still green after the changes (the Advanced `TaskDetailPanel`/`TaskDetailContent` behavior is unchanged)
- [x] 5.3 Test the interface-mode preference (default Simple, persistence, unknown-value fallback); toggle visibility wiring is covered by type-check
- [x] 5.4 Run Biome lint/format, TypeScript typecheck, and Vitest; all green (changed files lint-clean)
