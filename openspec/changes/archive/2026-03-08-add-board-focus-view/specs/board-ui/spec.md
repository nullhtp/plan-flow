## ADDED Requirements

### Requirement: Board View Mode Toggle
The system SHALL provide a toggle control in the board header toolbar that switches the DAG between two view modes: **Focus** and **Full**. The toggle SHALL be rendered as a segmented control or switch with labels "Focus" and "Full DAG", placed alongside existing toolbar buttons (Share, Save as Template, Memories). The default view mode SHALL be Focus when no `view` search parameter is present in the URL. The active view mode SHALL be persisted in the URL via a `view` search parameter (`?view=focus` or `?view=full`) so that direct linking and browser back/forward navigation preserve the selected mode.

#### Scenario: Default view mode is Focus
- **WHEN** a user navigates to `/boards/:boardId` without a `view` search parameter
- **THEN** the board renders in Focus mode and the toggle shows "Focus" as active

#### Scenario: Toggle to Full DAG view
- **WHEN** a user clicks "Full DAG" on the toggle
- **THEN** the URL updates to include `?view=full`, the DAG re-renders showing all tasks and edges, and the toggle shows "Full DAG" as active

#### Scenario: Toggle back to Focus view
- **WHEN** a user clicks "Focus" on the toggle while in Full DAG mode
- **THEN** the URL updates to `?view=focus` (or removes the parameter), locked not_started tasks are hidden, and the layout recomputes

#### Scenario: Direct link to full view
- **WHEN** a user navigates to `/boards/:boardId?view=full`
- **THEN** the board renders in Full DAG mode showing all tasks

#### Scenario: View mode preserved with other search params
- **WHEN** a user is in Focus mode with a task panel open (`?view=focus&task=abc`)
- **THEN** both the view mode and the task panel state are preserved in the URL

### Requirement: Focus View Task Filtering
The system SHALL filter the DAG in Focus mode to show only actionable and completed work. In Focus mode, the following tasks SHALL be visible: (1) all tasks with status `done`, (2) all tasks with status `in_progress`, (3) all tasks with status `not_started` that are NOT locked (all dependencies are `done`), (4) the goal node regardless of its status or lock state. Tasks with status `not_started` that are locked (at least one dependency is not `done`) SHALL be hidden, except the goal node. Edges SHALL be filtered to include only edges where BOTH the source and target tasks are visible. The dagre layout SHALL recompute positions using only the visible tasks and edges, producing a clean layout without gaps from hidden nodes.

#### Scenario: Focus view hides locked not_started tasks
- **WHEN** a board has 10 tasks: 3 done, 2 in_progress, 2 unlocked not_started, 2 locked not_started, and 1 goal node (locked)
- **THEN** Focus mode shows 8 tasks (3 done + 2 in_progress + 2 unlocked not_started + 1 goal node) and hides the 2 locked not_started tasks

#### Scenario: Focus view shows all done tasks
- **WHEN** a board has 15 tasks and 10 have status `done`
- **THEN** all 10 done tasks are visible in Focus mode

#### Scenario: Focus view shows unlocked not_started tasks
- **WHEN** a task has status `not_started` and `is_locked` is `false` (all dependencies are done)
- **THEN** the task is visible in Focus mode

#### Scenario: Goal node always visible in Focus mode
- **WHEN** the goal node has status `not_started` and is locked (prerequisites incomplete)
- **THEN** the goal node is still visible in Focus mode

#### Scenario: Edges filtered to visible tasks only
- **WHEN** task A (done) has an edge to task B (locked not_started, hidden) and task B has an edge to task C (also hidden)
- **THEN** both edges are hidden in Focus mode

#### Scenario: Layout recomputes for focused subset
- **WHEN** switching from Full to Focus mode hides 5 out of 15 tasks
- **THEN** the remaining 10 tasks are repositioned by dagre to fill the available space without gaps

#### Scenario: Full DAG mode shows everything
- **WHEN** the board is in Full DAG mode
- **THEN** all tasks and all edges are visible regardless of status or lock state (current behavior)

#### Scenario: All tasks actionable shows same graph
- **WHEN** all tasks on the board are either done, in_progress, or unlocked not_started
- **THEN** Focus mode and Full DAG mode show identical graphs

### Requirement: Focus View Task Panel Interaction
The system SHALL ensure that the task detail panel works correctly when the board is in Focus mode. When a visible task is clicked in Focus mode, the task detail panel SHALL open and display the full dependency and dependent lists (including references to hidden tasks). If a user navigates to a URL with a `task` search parameter referencing a task that is hidden in Focus mode, the system SHALL automatically switch to Full DAG mode to reveal the task.

#### Scenario: Open visible task panel in Focus mode
- **WHEN** a user clicks a visible task in Focus mode
- **THEN** the task detail panel opens showing all dependencies and dependents (some may reference hidden tasks by name)

#### Scenario: Deep link to hidden task auto-switches to Full view
- **WHEN** a user navigates to `/boards/:boardId?view=focus&task=<hiddenTaskId>` where the task is locked and not_started
- **THEN** the view automatically switches to Full DAG mode so the task is visible and the panel opens
