# Change: Add Simple Stepper View (default) alongside the existing DAG

## Why

The board today renders as an interactive DAG graph (React Flow). It is powerful but
visually dense — for many users, "what should I do next?" is buried in a graph they
have to read and pan. We want a beginner-friendly **Simple** interface that shows one
actionable task per screen, guiding the user step by step, while keeping the full DAG
available for power users who want the whole picture.

## What Changes

- Add a top-level **interface mode** with two options: **Simple** (new, default) and
  **Advanced** (today's DAG). A switch in the board header toggles between them.
- The chosen mode is a **saved global preference** (localStorage), so it persists across
  boards and sessions. Brand-new users start in Simple.
- **Simple mode** renders a **guided stepper**: one full-detail task screen at a time,
  walking **every task as a single linear sequence** in dependency (topological) order.
  Parallel branches are serialized into one ordered list — the stepper never shows parallel
  paths. All tasks appear (done, in-progress, not-started, and locked), prerequisites always
  before their dependents, so the user can step through the whole plan start to finish.
  Locked steps are read-only until their prerequisites are done; completing a task advances
  to the next step; the goal node is the final step, and completing it triggers the existing
  celebration.
- Each step is a **minimal** card showing only: read-only title, read-only description, a
  subtask checklist (toggle completion only — no add/delete/rename), the task AI chat, and
  **status buttons** (Start / Mark as done / Reopen). Marking a task done advances to the next
  step. Metadata, artifacts, expand-to-board, delete, and editable title/description inputs are
  intentionally omitted from Simple mode. Prev/Next controls and a progress indicator frame the
  card. (The full task-detail panel remains available in Advanced mode.)
- **Advanced mode** is unchanged: it is today's DAG and keeps its own **Focus / Full**
  toggle, which now renders only while Advanced is active. **BREAKING (UX default):** the
  default board experience changes from the Focus DAG to the Simple stepper.
- Sub-board tasks, deep links (`?task=`), and board completion are handled consistently
  in Simple mode (open sub-board CTA, auto-switch to Advanced for a non-actionable
  deep-linked task, completion screen + celebration).

This is a **frontend-only** change: all ordering data (tasks, edges, `dependency_ids`,
`is_locked`) is already available client-side, so no backend or API change is required.

## Impact

- Affected specs: `board-ui` (ADDED: interface mode selection, stepper navigation, stepper
  step screen, stepper completion; MODIFIED: Board View Mode Toggle — Focus/Full now nests
  inside Advanced mode)
- Affected code:
  - `frontend/src/routes/boards.$boardId.tsx` — header switch + conditional render
  - `frontend/src/features/board/components/` — new `StepperView`, extracted
    `TaskDetailContent` shared by the panel and the stepper
  - `frontend/src/features/board/utils/` — new actionable-queue ordering util
  - `frontend/src/features/board/hooks/` — new interface-mode preference hook
- No backend, database, or API contract changes.
