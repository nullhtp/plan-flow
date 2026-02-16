# board-ui Specification

## Purpose
Frontend DAG visualization and task interaction. Renders the task dependency graph using React Flow with dagre auto-layout, custom task/goal nodes, status toggling with lock enforcement, task detail editing via slide-in panel, subtask checklists, board list with progress cards, and goal completion celebration.
## Requirements
### Requirement: Task Card Display
The system SHALL render each task as a custom React Flow node within the DAG graph. Each node SHALL have very rounded corners (20-24px border radius) and a refined soft shadow for depth. The node SHALL NOT display connection handles (top/bottom dots) since nodes are not user-connectable. The node SHALL display the task title using refined typography: a semibold 14px title with adequate line height and spacing. If the task has a priority set, a muted pastel color palette SHALL be used for the border and background tint: rose tones for high priority, amber tones for medium priority, and sky/blue tones for low priority. Tasks without priority SHALL use a neutral card background with a subtle border. If the task has a due date, it SHALL be displayed on the node. If the task has subtasks, a progress indicator SHALL show the count of completed vs total subtasks (e.g., "2/5"). The node SHALL display the current status as a visual indicator (icon or color: gray for not_started, blue for in_progress, green for done). Completed tasks SHALL have an enhanced green treatment with a subtle green-tinted background gradient or soft glow in addition to the green border. Locked tasks SHALL appear muted but retain their priority color tinting (reduced opacity without full grayscale). All status-related visual changes (color, opacity, border) SHALL use smooth CSS transitions (200-300ms ease) so changes feel fluid rather than instant.

#### Scenario: Task node with all metadata unlocked
- **WHEN** a task has title, priority "high", due date, 3 subtasks (1 completed), and status `in_progress` with all dependencies `done`
- **THEN** the node shows the title in semibold typography, a muted rose-toned border and background tint, the due date, "1/3" subtask progress, a blue in-progress indicator, no lock icon, very rounded corners, a soft shadow, and no visible connection handles

#### Scenario: Task node locked by dependency
- **WHEN** a task has 2 dependencies and 1 is not `done`
- **THEN** the node appears muted with reduced opacity but retains its priority color tinting, shows a lock icon, and hovering shows "Blocked by: [prerequisite task name]"

#### Scenario: Task node with no metadata
- **WHEN** a task has only a title and status `not_started` with no dependencies
- **THEN** the node shows only the title and a gray not-started indicator with neutral styling, very rounded corners, and a soft shadow

#### Scenario: Completed task enhanced green treatment
- **WHEN** a task has status `done`
- **THEN** the node displays a green border with a subtle green-tinted background and the transition from previous state is smooth (200-300ms)

#### Scenario: Status change uses smooth transition
- **WHEN** a task status changes from `not_started` to `in_progress`
- **THEN** the border color, background color, and status icon change with a smooth CSS transition rather than an instant swap

### Requirement: Task Detail Side Panel
The system SHALL display a slide-out side panel on the right when a user clicks a task node in the DAG. The panel SHALL contain editable fields for: title (text input), description (textarea), due date (date picker), priority (select: low/medium/high/none), estimated minutes (number input), status (select: not_started/in_progress/done with lock enforcement), and a subtask checklist. The panel SHALL show a "Dependencies" section listing prerequisite tasks (read-only, linking to those tasks). The panel SHALL show a "Unlocks" section listing dependent tasks (read-only). The panel SHALL have a close button. The graph SHALL remain visible behind the panel. The panel state SHALL be reflected in the URL via a `task` search parameter (`?task=<taskId>`) so that direct linking and browser navigation work.

#### Scenario: Open task detail panel
- **WHEN** a user clicks a task node in the DAG
- **THEN** a side panel slides in from the right showing all task fields and the URL updates to include `?task=<taskId>`

#### Scenario: Close task detail panel
- **WHEN** a user clicks the close button or presses Escape
- **THEN** the panel closes and the `task` search parameter is removed from the URL

#### Scenario: Direct link to task detail
- **WHEN** a user navigates to `/boards/:boardId?task=<taskId>`
- **THEN** the board loads and the task detail panel opens for the specified task

#### Scenario: Edit task fields in panel
- **WHEN** a user edits the task title in the side panel and the field loses focus
- **THEN** a PATCH request is sent with the updated title and the UI reflects the change optimistically

#### Scenario: Status change blocked for locked task
- **WHEN** a user opens the detail panel for a locked task
- **THEN** the status selector is disabled with a tooltip explaining which dependencies must be completed first

### Requirement: Subtask Checklist in Detail Panel
The system SHALL render subtasks as a checklist within the task detail side panel. Each subtask SHALL display a checkbox (toggle completed) and the subtask title. Users SHALL be able to add new subtasks via an inline text input at the bottom of the list, toggle completion, edit subtask titles inline, and delete subtasks. All operations SHALL use optimistic updates.

#### Scenario: Toggle subtask completion
- **WHEN** a user clicks the checkbox on a subtask
- **THEN** the checkbox toggles immediately (optimistic) and a PATCH request updates the `completed` field

#### Scenario: Add subtask
- **WHEN** a user types a subtask title in the input and presses Enter
- **THEN** the subtask appears in the list immediately (optimistic) and a POST request creates it on the server

#### Scenario: Delete subtask
- **WHEN** a user clicks the delete button on a subtask
- **THEN** the subtask is removed from the list immediately (optimistic) and a DELETE request removes it on the server

### Requirement: Delete Task
The system SHALL provide a delete option for tasks via a delete button in the task detail panel. Deleting a task SHALL show a confirmation dialog that warns about dependent tasks that will become unblocked. Upon confirmation, the task is removed optimistically, sending a `DELETE /api/tasks/:id` request.

#### Scenario: Delete task from detail panel
- **WHEN** a user clicks "Delete" in the task detail panel and confirms
- **THEN** the panel closes, the task node and all its edges are removed from the graph immediately, and a DELETE request is sent

#### Scenario: Delete task with dependents shows warning
- **WHEN** a user attempts to delete a task that has 3 dependent tasks
- **THEN** the confirmation dialog warns "This task is a prerequisite for 3 other tasks. Deleting it will unblock them."

### Requirement: Board List on Home Page
The system SHALL display a list of the authenticated user's boards on the index page (`/`). Each board SHALL be rendered as a card showing the board title, goal summary (goal title or input), task progress (e.g., "5/12 tasks done"), and creation date. Clicking a board card SHALL navigate to `/boards/:boardId`. The board list SHALL be fetched via `GET /api/boards`. If the user has no boards, the page SHALL display a message encouraging them to create a goal.

#### Scenario: Home page shows board list
- **WHEN** an authenticated user with 3 boards visits `/`
- **THEN** the page displays 3 board cards with title, progress, and creation date, plus a "New Goal" button

#### Scenario: Home page with no boards
- **WHEN** an authenticated user with no boards visits `/`
- **THEN** the page displays a message like "No boards yet. Create a goal to get started!" with a "New Goal" button

#### Scenario: Navigate to board from home
- **WHEN** a user clicks a board card on the home page
- **THEN** the browser navigates to `/boards/:boardId`

### Requirement: Board Loading State
The system SHALL display a loading state while the board data is being fetched. The loading state SHALL show a centered spinner or placeholder indicating the graph is loading.

#### Scenario: Board loading state
- **WHEN** a user navigates to `/boards/:boardId` and the data is loading
- **THEN** a loading indicator is displayed

#### Scenario: Board loaded successfully
- **WHEN** the board data finishes loading
- **THEN** the loading indicator is replaced with the actual DAG graph

### Requirement: Optimistic Update Error Handling
The system SHALL display a toast notification when an optimistic update fails (server rejects the mutation). The toast SHALL include a brief error message. The UI SHALL revert to the state before the failed mutation. The board query SHALL be invalidated to re-sync with the server.

#### Scenario: Mutation failure toast and rollback
- **WHEN** a task status update PATCH request fails with a server error
- **THEN** the task reverts to its original status, a toast displays "Failed to update task", and the board data is refetched

#### Scenario: Network error during mutation
- **WHEN** a mutation request fails due to network error
- **THEN** the UI reverts, a toast displays "Network error. Please try again.", and the board data is refetched

### Requirement: DAG Graph Layout
The system SHALL render a board as an interactive directed acyclic graph using React Flow (`@xyflow/react`). Tasks SHALL be displayed as custom nodes. Dependencies SHALL be displayed as smooth bezier curve edges (arrows) from prerequisite tasks to dependent tasks. The graph SHALL use the dagre layout algorithm to automatically position nodes in a top-to-bottom hierarchy. The graph SHALL support pan (drag background) and zoom (scroll wheel). The graph background SHALL be a clean plain canvas with no dot grid or pattern. A minimap SHALL be displayed in the bottom-right corner, styled to match the overall visual theme (matching background color and node color representation). The board title SHALL be displayed above the graph.

#### Scenario: Board renders as DAG with styled nodes and bezier edges
- **WHEN** an authenticated user navigates to `/boards/:boardId`
- **THEN** the page displays the board title and a React Flow graph with polished task nodes connected by smooth bezier curve edges, on a clean background with no grid pattern

#### Scenario: Graph supports pan and zoom
- **WHEN** a user scrolls to zoom or drags the background
- **THEN** the graph viewport adjusts accordingly and the styled minimap reflects the current viewport

#### Scenario: Root tasks appear at top
- **WHEN** the DAG has 3 tasks with no dependencies (root tasks)
- **THEN** those tasks appear at the top of the graph layout with their dependents below

#### Scenario: Parallel paths rendered side by side
- **WHEN** two tasks have no dependency relationship but share a common dependent
- **THEN** dagre positions them side by side with bezier curve edges converging to the shared dependent

#### Scenario: Convergence nodes merge parallel paths
- **WHEN** a milestone task depends on 3 tasks from different parallel paths
- **THEN** dagre positions the 3 upstream tasks in the same row and draws 3 smooth bezier edges converging into the milestone node below them

#### Scenario: Final goal node rendered at bottom of graph
- **WHEN** a board has a goal node (the final task with `is_goal_node: true`)
- **THEN** the goal node appears at the very bottom of the DAG layout as the single sink node, with all remaining leaf edges flowing into it

#### Scenario: Minimap matches visual theme
- **WHEN** the minimap is rendered in the bottom-right corner
- **THEN** the minimap background and node colors match the overall graph theme rather than using default React Flow minimap styling

### Requirement: Goal Node Visual Treatment
The system SHALL render the final goal node with a distinct visual style that differentiates it from regular task nodes. The goal node SHALL be larger, have a highlighted border (e.g., gold or accent color), and display the goal title prominently. When the goal node is locked (prerequisites incomplete), it SHALL show a lock icon and a progress summary (e.g., "8/15 tasks done"). When the goal node is completed (status `done`), it SHALL trigger the celebration animation.

#### Scenario: Goal node rendered with distinct style
- **WHEN** the DAG contains a task with `is_goal_node: true`
- **THEN** that node is rendered larger than regular task nodes, with a gold/accent border and the title displayed prominently

#### Scenario: Locked goal node shows progress
- **WHEN** the goal node has 15 prerequisite tasks and 8 are `done`
- **THEN** the goal node displays a progress indicator "8/15 tasks completed" and a lock icon

#### Scenario: Completing goal node triggers celebration
- **WHEN** a user marks the goal node as `done` (after all its prerequisites are `done`)
- **THEN** the confetti celebration animation plays and the "Goal Complete!" overlay appears

### Requirement: Task Status Toggle on Node
The system SHALL display a clickable status control on each task node that allows the user to cycle the task status. Clicking the control SHALL send a `PATCH /api/tasks/:id` request with the new status. For unlocked tasks: clicking toggles `not_started` to `in_progress` to `done`. For locked tasks: the control is disabled and shows a lock icon. The status change SHALL update optimistically. When a task transitions to `done`, all dependent tasks that now have all dependencies `done` SHALL visually unlock (remove muted overlay and lock icon) with a smooth CSS transition. The cursor SHALL change to pointer when hovering over clickable nodes.

#### Scenario: Start an unlocked task
- **WHEN** a user clicks the status control on a task with status `not_started` and no unmet dependencies
- **THEN** the task status changes to `in_progress` optimistically with a smooth visual transition and a PATCH request is sent

#### Scenario: Complete a task and unlock dependent
- **WHEN** a user clicks the status control on a task with status `in_progress` and task B depends only on this task
- **THEN** the task status changes to `done` with a smooth transition to green styling, and task B's node smoothly transitions from muted to full color (lock icon removed)

#### Scenario: Cannot start locked task
- **WHEN** a user clicks the status control on a locked task
- **THEN** nothing happens and a tooltip shows "Complete prerequisites first"

### Requirement: Goal Completion Celebration
The system SHALL detect when the goal node (the task with `is_goal_node: true`) transitions to status `done` and trigger a celebration animation. The celebration SHALL include a confetti effect and a congratulatory message overlay (e.g., "Goal Complete!"). The celebration SHALL auto-dismiss after 5 seconds or on user click. The goal node can only be completed after all its prerequisite tasks are `done`, making it the final action in the DAG.

#### Scenario: Goal node completed triggers celebration
- **WHEN** a user marks the goal node as `done` (all its prerequisites are already `done`)
- **THEN** a confetti animation plays across the viewport and a "Goal Complete!" message appears

#### Scenario: Celebration dismisses on click
- **WHEN** the celebration animation is playing and the user clicks anywhere
- **THEN** the celebration animation stops and the message disappears

#### Scenario: Celebration does not trigger on regular task completion
- **WHEN** a user completes a regular task (not the goal node) but the goal node is still not `done`
- **THEN** no celebration animation plays

### Requirement: Edge Visual Styling
The system SHALL render dependency edges as smooth bezier curves with visual differentiation between unlocked and locked paths. Unlocked edges (where the target task has all dependencies met) SHALL be rendered with a thicker stroke (3px) and a colored appearance (e.g., indigo or accent color) with a closed arrowhead marker. Locked edges (where the target task has unmet dependencies) SHALL be rendered with a thinner stroke (1.5px) and a muted gray appearance. All edges SHALL use the `smoothstep` or `bezier` edge type for curved connections instead of straight lines.

#### Scenario: Unlocked edge rendered thick and colored
- **WHEN** a dependency edge connects task A (done) to task B (all dependencies met)
- **THEN** the edge is rendered as a smooth bezier curve with a 3px stroke in indigo/accent color with a closed arrowhead

#### Scenario: Locked edge rendered thin and muted
- **WHEN** a dependency edge connects task A (not done) to task B (locked)
- **THEN** the edge is rendered as a smooth bezier curve with a 1.5px stroke in muted gray with a closed arrowhead

#### Scenario: Edge styling updates on status change
- **WHEN** task A transitions from `in_progress` to `done` and task B's only dependency is task A
- **THEN** the edge from A to B transitions from thin/muted to thick/colored appearance

