## ADDED Requirements

### Requirement: Interface Mode Selection

The system SHALL provide two top-level board interface modes: **Simple** (a guided
stepper) and **Advanced** (the DAG graph). A segmented control in the board header SHALL
let the user switch between them, with labels "Simple" and "Advanced". The selected mode
SHALL be persisted as a single global preference in browser local storage (key
`planflow:board-interface-mode`, value `simple` or `advanced`) so it applies to every board
and survives across sessions. When no preference is stored, the mode SHALL default to
**Simple**. Switching mode SHALL re-render the board in place at the same route
(`/boards/:boardId`) without a full navigation. The Simple/Advanced choice SHALL NOT be
encoded in the URL; the existing `view` and `task` search parameters SHALL continue to
function within Advanced mode.

#### Scenario: Default mode is Simple for a new user

- **WHEN** a user with no stored interface-mode preference opens `/boards/:boardId`
- **THEN** the board renders in Simple mode (the guided stepper) and the header switch shows "Simple" as active

#### Scenario: Switch to Advanced

- **WHEN** a user in Simple mode clicks "Advanced" in the header switch
- **THEN** the board re-renders as the DAG graph, the Focus/Full toggle becomes visible, and `simple`→`advanced` is written to local storage

#### Scenario: Preference persists across boards and sessions

- **WHEN** a user selects "Advanced" on one board, then opens a different board (or reloads)
- **THEN** the other board also opens in Advanced mode because the preference is global and persisted

#### Scenario: Switch back to Simple

- **WHEN** a user in Advanced mode clicks "Simple"
- **THEN** the board re-renders as the guided stepper and `advanced`→`simple` is written to local storage

### Requirement: Simple Stepper Navigation

In Simple mode, the system SHALL present the board as a guided stepper that walks **every
task as a single linear sequence** in dependency (topological) order, serializing parallel
branches into one ordered list — the stepper SHALL NOT show parallel paths. The sequence
SHALL include all tasks regardless of status or lock state (done, in-progress, not-started,
and locked tasks all appear as steps), with ready nodes tie-broken by `created_at` so
prerequisites always precede their dependents. Because the goal node depends on all leaf
tasks, it SHALL be the last step. On entry the current step SHALL be the first `in_progress`
task if one exists, otherwise the first task that is not `done` (where the user resumes),
otherwise the first task. The system SHALL provide **Previous** and **Next** controls to move
within the sequence, and a progress indicator showing both the sequence position (e.g.
"Step 2 of 12") and an overall board completion bar (count of `done` tasks over total tasks).
The **Next** control SHALL be enabled only when the current step's task is `done`; while the
current task is not `done`, Next SHALL be disabled (with a "complete this task to continue"
hint) so the user must finish the current task before advancing. **Previous** SHALL remain
available (except on the first step) so completed steps can be revisited. When the user marks
the current step's task `done`, the system SHALL advance to the next task in the sequence.

#### Scenario: Stepper shows every task as one serialized sequence

- **WHEN** a board has 3 `done`, 2 `in_progress`, 2 unlocked `not_started`, 3 locked `not_started` tasks, and a goal node (12 total)
- **THEN** the stepper sequence contains all 12 tasks in dependency order, including the done and locked tasks, with the goal node last and no parallel paths shown

#### Scenario: Parallel branches are serialized into one sequence

- **WHEN** a board has two independent tasks A and B that both depend on a shared root and both feed a shared goal node
- **THEN** the stepper presents root, then A and B as consecutive steps (in either order), then the goal node — a single line rather than two parallel paths

#### Scenario: Entry lands on an in-progress task

- **WHEN** a user opens a board in Simple mode and at least one task is `in_progress`
- **THEN** the first `in_progress` task (in sequence order) is shown as the current step

#### Scenario: Next is disabled until the current task is done

- **WHEN** the current step's task is `in_progress` or `not_started` (not `done`)
- **THEN** the Next control is disabled with a "complete this task to continue" hint, while Previous remains available

#### Scenario: Previous revisits a completed step where Next is enabled

- **WHEN** the user clicks Previous to a step whose task is already `done`
- **THEN** the stepper moves to that completed step and the Next control is enabled there

#### Scenario: Completing the current task advances and unlocks Next

- **WHEN** the user marks the current step's task `done`
- **THEN** the status update is sent and the stepper advances to the next task in the sequence (unless the current step is the last)

#### Scenario: Goal node is the final step

- **WHEN** the stepper sequence is built for a board with a goal node
- **THEN** the goal node is the last step in the sequence because it depends on all leaf tasks

#### Scenario: Progress indicator reflects sequence position and overall completion

- **WHEN** a board has 10 tasks with 4 `done` and the current step is the 5th in the sequence
- **THEN** the stepper shows a sequence position of "Step 5 of 10" and an overall completion bar at 4/10

### Requirement: Simple Stepper Step Screen

In Simple mode, each step SHALL render a minimal, focused card for the current task containing
only: (1) the task **title** as read-only text, (2) the task **description** as read-only text,
(3) the **subtask checklist**, where the user may toggle a subtask's completion but SHALL NOT
be able to add, delete, or rename subtasks, (4) the task **AI chat**, and (5) **status
buttons** that set the task's status. The card SHALL NOT render editable title/description
inputs, task metadata (priority, due date, estimate), artifacts, an expand-to-board control,
or a delete control. The status buttons SHALL reflect the task lifecycle: a locked task shows
a disabled locked indicator naming the unmet prerequisites; a `not_started` task shows a
"Start task" button (→ `in_progress`); an `in_progress` task shows a "Mark as done" button
(→ `done`) and a "Reset" button (→ `not_started`); a `done` task shows a completed indicator
and a "Reopen" button (→ `in_progress`). Marking the task **done** SHALL advance the stepper to
the next step. Additionally, when the user checks the **final remaining subtask** of an
`in_progress` task (so all of its subtasks are complete), the system SHALL automatically mark
the task `done` and advance to the next step. When the current task has a non-null
`sub_board_id`, the subtask checklist SHALL be replaced by an "Open Sub-Board" action that
navigates to `/boards/:subBoardId`.

#### Scenario: Step screen shows only the minimal fields

- **WHEN** the current step's task has a title, description, priority, a due date, 3 subtasks, and a chat history
- **THEN** the card shows the read-only title, read-only description, the subtask checklist, status buttons, and the AI chat — and does NOT show editable title/description inputs, the priority/due-date/estimate metadata, artifacts, expand-to-board, or a delete control

#### Scenario: Title and description are read-only

- **WHEN** a user views a step
- **THEN** the title and description are displayed as text with no editable input or textarea

#### Scenario: Subtasks can be toggled but not added or deleted

- **WHEN** a user views the subtask checklist on a step
- **THEN** each subtask has a completion checkbox that issues a PATCH on toggle, and there is no "add subtask" input and no per-subtask delete control

#### Scenario: Status buttons drive the lifecycle

- **WHEN** the current step's task is `not_started`
- **THEN** a "Start task" button is shown that moves it to `in_progress`; once `in_progress`, a "Mark as done" button moves it to `done`; once `done`, a "Reopen" button returns it to `in_progress`

#### Scenario: Marking done advances to the next step

- **WHEN** a user clicks "Mark as done" on the current step
- **THEN** the task's status is set to `done` and the stepper advances to the next step

#### Scenario: Completing all subtasks auto-advances

- **WHEN** the current step's task is `in_progress` with subtasks and the user checks the last remaining subtask
- **THEN** the task is automatically marked `done` and the stepper advances to the next step

#### Scenario: Completing a subtask while others remain does not advance

- **WHEN** the current step's task has multiple unfinished subtasks and the user checks one of them
- **THEN** only the subtask is updated; the task is not auto-completed and the stepper stays on the current step

#### Scenario: Locked task shows a disabled status indicator

- **WHEN** the user navigates to a step whose task is locked (a dependency is not yet `done`)
- **THEN** the card shows the task's title, description, and chat, but in place of status buttons shows a locked indicator naming the unmet prerequisites

#### Scenario: Sub-board task step offers Open Sub-Board

- **WHEN** the current step's task has a `sub_board_id`
- **THEN** the card replaces the subtask checklist with an "Open Sub-Board" action that navigates to `/boards/:subBoardId`

### Requirement: Simple Stepper Completion and Edge States

In Simple mode, the system SHALL display a completion screen and trigger the existing
goal-completion celebration when the board is complete (every task is `done`, including the
goal node). The completion screen SHALL offer a link back to the dashboard and an option to
view the full DAG (switch to Advanced). Because the stepper sequence includes every task, a
deep link to a task via `?task=<id>` SHALL land on that task as the current step regardless of
its status or lock state (no mode switch is required). If the board has no tasks at all, the
system SHALL display a graceful fallback prompting the user to open the full DAG rather than a
blank screen.

#### Scenario: Board completion shows completion screen and celebration

- **WHEN** the user marks the goal node `done` in Simple mode and the board becomes complete
- **THEN** a completion screen appears, the celebration animation plays, and the screen offers "Back to dashboard" and "View full DAG"

#### Scenario: Deep link lands on the task in-sequence

- **WHEN** a user opens `/boards/:boardId?task=<id>` in Simple mode
- **THEN** the stepper opens with that task as the current step, whether it is `done`, `in_progress`, unlocked, or locked

#### Scenario: Empty board shows fallback

- **WHEN** the board has no tasks
- **THEN** the stepper shows a fallback message prompting the user to open the full DAG instead of a blank screen

## MODIFIED Requirements

### Requirement: Board View Mode Toggle

The system SHALL provide, **while the Advanced interface mode is active**, a toggle control
in the board header toolbar that switches the DAG between two view modes: **Focus** and
**Full**. The toggle SHALL be rendered as a segmented control or switch with labels "Focus"
and "Full DAG", placed alongside existing toolbar buttons (Share, Save as Template,
Memories). The default DAG view mode SHALL be Focus when no `view` search parameter is
present in the URL. The active view mode SHALL be persisted in the URL via a `view` search
parameter (`?view=focus` or `?view=full`) so that direct linking and browser back/forward
navigation preserve the selected mode. While the **Simple** interface mode is active, the
Focus/Full toggle SHALL NOT be rendered and the `view` parameter SHALL have no visible
effect until Advanced mode is active.

#### Scenario: Default DAG view mode is Focus in Advanced

- **WHEN** a user is in Advanced mode and navigates to `/boards/:boardId` without a `view` search parameter
- **THEN** the DAG renders in Focus mode and the toggle shows "Focus" as active

#### Scenario: Focus/Full toggle hidden in Simple mode

- **WHEN** a user is in Simple mode
- **THEN** the Focus/Full toggle is not rendered in the header (only the Simple/Advanced switch is shown)

#### Scenario: Toggle to Full DAG view

- **WHEN** a user in Advanced mode clicks "Full DAG" on the toggle
- **THEN** the URL updates to include `?view=full`, the DAG re-renders showing all tasks and edges, and the toggle shows "Full DAG" as active

#### Scenario: Toggle back to Focus view

- **WHEN** a user clicks "Focus" on the toggle while in Full DAG mode
- **THEN** the URL updates to `?view=focus` (or removes the parameter), locked not_started tasks are hidden, and the layout recomputes

#### Scenario: Direct link to full view

- **WHEN** a user navigates to `/boards/:boardId?view=full` and is in Advanced mode
- **THEN** the DAG renders in Full DAG mode showing all tasks

#### Scenario: View mode preserved with other search params

- **WHEN** a user is in Advanced Focus mode with a task panel open (`?view=focus&task=abc`)
- **THEN** both the view mode and the task panel state are preserved in the URL
