## MODIFIED Requirements

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

## ADDED Requirements

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
