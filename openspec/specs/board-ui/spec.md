# board-ui Specification

## Purpose
Frontend DAG visualization and task interaction. Renders the task dependency graph using React Flow with dagre auto-layout, custom task/goal nodes, status toggling with lock enforcement, task detail editing via slide-in panel, subtask checklists, board list with progress cards, and goal completion celebration.
## Requirements
### Requirement: Task Card Display
The system SHALL render each task as a custom React Flow node within the DAG graph. Each node SHALL have very rounded corners (20-24px border radius) and a refined soft shadow for depth. The node SHALL NOT display connection handles (top/bottom dots) since nodes are not user-connectable. The node SHALL display the task title using refined typography: a semibold 14px title with adequate line height and spacing. If the task has a priority set, a muted pastel color palette SHALL be used for the border and background tint: rose tones for high priority, amber tones for medium priority, and sky/blue tones for low priority. Tasks without priority SHALL use a neutral card background with a subtle border. If the task has a due date, it SHALL be displayed on the node. If the task has subtasks and no sub-board, a progress indicator SHALL show the count of completed vs total subtasks (e.g., "2/5"). If the task has a sub-board, a sub-board progress indicator SHALL replace the subtask count, showing completed vs total sub-board tasks (e.g., "3/8 tasks") sourced from `sub_board_progress`. The node SHALL display the current status as a visual indicator (icon or color: gray for not_started, blue for in_progress, green for done). Completed tasks SHALL have an enhanced green treatment with a subtle green-tinted background gradient or soft glow in addition to the green border. Locked tasks SHALL appear muted but retain their priority color tinting (reduced opacity without full grayscale). All status-related visual changes (color, opacity, border) SHALL use smooth CSS transitions (200-300ms ease) so changes feel fluid rather than instant. **Sub-board indicator**: When a task has a non-null `sub_board_id`, the node SHALL display a small layers/graph icon in the top-right corner and use a dashed border style instead of solid. The dashed border SHALL use a distinct accent color (e.g., purple/violet) to clearly differentiate sub-board tasks from regular tasks. Clicking a sub-board task node SHALL navigate to the sub-board (`/boards/:subBoardId`) instead of opening the task detail panel.

#### Scenario: Task node with all metadata unlocked
- **WHEN** a task has title, priority "high", due date, 3 subtasks (1 completed), status `in_progress`, no sub-board, and all dependencies `done`
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

#### Scenario: Sub-board task node visual treatment
- **WHEN** a task has `sub_board_id` set and `sub_board_progress` of `{ task_count: 8, completed_task_count: 3 }`
- **THEN** the node displays a layers/graph icon in the top-right corner, uses a dashed purple/violet border, shows "3/8 tasks" as progress, and no subtask count is shown

#### Scenario: Clicking sub-board task navigates to sub-board
- **WHEN** a user clicks a task node that has a `sub_board_id`
- **THEN** the browser navigates to `/boards/:subBoardId` instead of opening the task detail panel

### Requirement: Task Detail Side Panel
The system SHALL display a slide-out side panel on the right when a user clicks a task node in the DAG. The panel SHALL contain editable fields for: title (text input), description (textarea), due date (date picker), priority (select: low/medium/high/none), estimated minutes (number input), status (select: not_started/in_progress/done with lock enforcement), and a subtask checklist. The panel SHALL show a "Dependencies" section listing prerequisite tasks (read-only, linking to those tasks). The panel SHALL show an "Unlocks" section listing dependent tasks (read-only). The panel SHALL show an "AI Actions" section with contextual action buttons generated by the AI (see task-chat-ui spec). The panel SHALL show an "Artifacts" section listing persistent content generated by the AI (see task-artifacts spec). The panel SHALL show a "Chat" section at the bottom for conversing with the AI about this task (see task-chat-ui spec). The panel SHALL have a close button. The graph SHALL remain visible behind the panel. The panel state SHALL be reflected in the URL via a `task` search parameter (`?task=<taskId>`) so that direct linking and browser navigation work. All sections SHALL be in a single scrollable view in the order: Status, Title, Description, Metadata, Dependencies, Unlocks, Subtasks (or Sub-Board), AI Actions, Artifacts, Chat. **Sub-board section**: When a task has a sub-board (`sub_board_id` is non-null), the Subtasks section SHALL be replaced by a "Sub-Board" section showing the sub-board title, progress summary (e.g., "3/8 tasks completed"), and a prominent "Open Sub-Board" button that navigates to `/boards/:subBoardId`. **Sub-board creation**: When a task has no sub-board and belongs to a root-level board, the panel SHALL show an "Expand to Board" button below the subtasks section. Clicking this button starts the inline sub-board creation flow (question generation, answer form, generation with streaming progress). If the task has existing subtasks, a confirmation dialog SHALL warn the user that subtasks will be replaced by the sub-board. **No expand button on sub-board tasks**: Tasks that belong to a sub-board (the board has a `parent_task_id`) SHALL NOT show the "Expand to Board" button (1-level nesting limit).

#### Scenario: Open task detail panel
- **WHEN** a user clicks a task node in the DAG (that does not have a sub-board)
- **THEN** a side panel slides in from the right showing all task fields, AI actions (loading then loaded), artifacts, chat section, and the URL updates to include `?task=<taskId>`

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

#### Scenario: Task with sub-board shows sub-board section
- **WHEN** a user opens the detail panel for a task with a sub-board titled "Housing Plan" with 8 tasks (3 done)
- **THEN** the Subtasks section is replaced by a "Sub-Board" section showing "Housing Plan", "3/8 tasks completed", and an "Open Sub-Board" button

#### Scenario: Open Sub-Board button navigates to sub-board
- **WHEN** a user clicks "Open Sub-Board" in the task detail panel
- **THEN** the browser navigates to `/boards/:subBoardId` and the task detail panel closes

#### Scenario: Expand to Board button on root board task
- **WHEN** a user opens the detail panel for a task on a root board that has no sub-board
- **THEN** an "Expand to Board" button is visible below the subtasks section

#### Scenario: No Expand to Board button on sub-board task
- **WHEN** a user opens the detail panel for a task on a sub-board
- **THEN** no "Expand to Board" button is shown

#### Scenario: Expand to Board with existing subtasks shows confirmation
- **WHEN** a user clicks "Expand to Board" for a task that has 4 existing subtasks
- **THEN** a confirmation dialog warns "This will replace the 4 existing subtasks with a detailed sub-board. Continue?"

### Requirement: Subtask Checklist in Detail Panel
The system SHALL render subtasks as a checklist within the task detail side panel. Each subtask SHALL display a checkbox (toggle completed) and the subtask title. When a subtask has a non-null `action_prompt`, a small action button (sparkle/wand icon) SHALL appear inline next to the subtask title. Clicking the action button SHALL send the subtask's `action_prompt` to the task chat, prefixed with the subtask context (e.g., "Help me with subtask: {subtask_title} -- {action_prompt}"), and scroll to the chat section. A loading indicator SHALL appear on the action button while the subtask's action is being generated (after manual subtask creation). Users SHALL be able to add new subtasks via an inline text input at the bottom of the list, toggle completion, edit subtask titles inline, and delete subtasks. All operations SHALL use optimistic updates. When a user adds a new subtask, the system SHALL call the action generation endpoint in the background and update the subtask's action button once the result is available.

#### Scenario: Toggle subtask completion
- **WHEN** a user clicks the checkbox on a subtask
- **THEN** the checkbox toggles immediately (optimistic) and a PATCH request updates the `completed` field

#### Scenario: Add subtask
- **WHEN** a user types a subtask title in the input and presses Enter
- **THEN** the subtask appears in the list immediately (optimistic), a POST request creates it on the server, and an action generation request is triggered in the background

#### Scenario: Delete subtask
- **WHEN** a user clicks the delete button on a subtask
- **THEN** the subtask is removed from the list immediately (optimistic) and a DELETE request removes it on the server

#### Scenario: Subtask with AI action button
- **WHEN** a subtask has `action_label: "Generate agreement draft"` and `action_icon: "generate"`
- **THEN** a sparkle/wand icon button appears next to the subtask title with a tooltip showing the action label

#### Scenario: Subtask without AI action
- **WHEN** a subtask has null action fields
- **THEN** no action button appears next to the subtask — it displays as a simple checklist item

#### Scenario: Click subtask action button
- **WHEN** a user clicks the action button on a subtask titled "Draft rental agreement" with prompt "Generate a rental agreement draft"
- **THEN** the message "Help me with subtask: Draft rental agreement -- Generate a rental agreement draft" is sent to the task chat and the view scrolls to the chat section

#### Scenario: Action loading after subtask creation
- **WHEN** a user creates a new subtask "Research visa requirements"
- **THEN** a loading spinner appears on the action button position while the action generation endpoint is called, and once complete, either an action button appears or the loading indicator disappears (if non-automatable)

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
The system SHALL display a loading state while the board data is being fetched. The loading state SHALL show a centered spinner or placeholder indicating the graph is loading. When the user arrives at a board page via auto-navigation from the generation progress view, the board data SHALL already be persisted and load quickly without a prolonged loading state.

#### Scenario: Board loading state
- **WHEN** a user navigates to `/boards/:boardId` and the data is loading
- **THEN** a loading indicator is displayed

#### Scenario: Board loaded successfully
- **WHEN** the board data finishes loading
- **THEN** the loading indicator is replaced with the actual DAG graph

#### Scenario: Post-generation board load
- **WHEN** a user arrives at the board page via auto-navigation from generation progress
- **THEN** the board data loads from the server (already persisted during generation) and the DAG graph renders promptly

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

### Requirement: Quick-Reply Buttons in Chat
The system SHALL detect quick-reply options in AI chat responses and render them as clickable buttons below the AI message. When the AI determines it needs clarification before executing a subtask action, it SHALL include quick-reply options in a structured format within its response. Each quick-reply button SHALL display a short label. Clicking a quick-reply button SHALL send the button's value as the next chat message. Quick-reply buttons SHALL disappear after one is clicked (single-use). The system SHALL detect quick-replies via a JSON block with key `quick_replies` containing an array of objects with `label` (display text) and `value` (text to send as message).

#### Scenario: AI asks clarifying question with quick-replies
- **WHEN** the AI responds to a subtask action prompt and needs clarification (e.g., "What tone should the agreement have?")
- **THEN** the AI message includes quick-reply buttons like "Formal", "Informal", "Neutral" below the text

#### Scenario: User clicks a quick-reply button
- **WHEN** a user clicks the "Formal" quick-reply button
- **THEN** "Formal" is sent as the next chat message and the quick-reply buttons disappear from that message

#### Scenario: AI does not need clarification
- **WHEN** the AI receives a straightforward subtask action prompt (e.g., "Research visa requirements for Portugal")
- **THEN** the AI executes the task directly without showing quick-reply buttons

### Requirement: Breadcrumb Navigation Bar
The system SHALL display a breadcrumb navigation bar at the top of the board page, replacing the hardcoded back button. For root boards, the breadcrumb SHALL show: `Home > Board Title`. For sub-boards, the breadcrumb SHALL show: `Home > Parent Board Title > Parent Task Title`. Each segment except the last SHALL be a clickable link: "Home" navigates to `/`, "Parent Board Title" navigates to `/boards/:parentBoardId`. The last segment (current board title) SHALL not be clickable. The breadcrumb SHALL use the `parent_board` data from the BoardResponse to build the chain. The breadcrumb SHALL use a separator character (e.g., `/` or `>`) between segments and truncate long titles with ellipsis to prevent overflow.

#### Scenario: Root board breadcrumb
- **WHEN** a user views a root board titled "Relocation to Lisbon"
- **THEN** the breadcrumb shows "Home > Relocation to Lisbon" where "Home" links to `/`

#### Scenario: Sub-board breadcrumb
- **WHEN** a user views a sub-board titled "Housing Plan" whose parent board is "Relocation to Lisbon"
- **THEN** the breadcrumb shows "Home > Relocation to Lisbon > Housing Plan" where "Home" links to `/` and "Relocation to Lisbon" links to `/boards/:parentBoardId`

#### Scenario: Long title truncation
- **WHEN** a board title exceeds 40 characters in the breadcrumb
- **THEN** the title is truncated with ellipsis to prevent layout overflow

### Requirement: Inline Sub-Board Creation Flow
The system SHALL provide an inline sub-board creation flow within the task detail panel. The flow consists of three states: (1) **Questions loading**: After the user clicks "Expand to Board", a loading indicator appears while `POST /api/tasks/:id/sub-board-questions` is called. (2) **Questions form**: The 2-4 questions are rendered as a mini form within the panel (same field types as the goal question form: text, select, multiselect, number). Each question shows its text as the label and rationale as helper text. A "Generate Sub-Board" submit button is at the bottom. (3) **Generation in progress**: After submitting answers, the panel shows a streaming progress indicator as the sub-board generates via SSE (`POST /api/tasks/:id/generate-sub-board`). The progress shows the number of tasks generated and enriched. Upon completion, the panel transitions to show the sub-board section with an "Open Sub-Board" button. If generation fails, an error message with a "Try Again" button is shown.

#### Scenario: Sub-board creation flow starts
- **WHEN** a user clicks "Expand to Board" (and confirms if subtasks exist)
- **THEN** a loading indicator appears in the panel while questions are being generated

#### Scenario: Questions rendered in panel
- **WHEN** the sub-board questions API returns 3 questions
- **THEN** the panel renders a form with 3 fields matching the question types, rationale text, and a "Generate Sub-Board" button

#### Scenario: Generation progress displayed
- **WHEN** the user submits answers and sub-board generation starts
- **THEN** the panel shows a progress indicator: "Creating board structure..." then "Enriching tasks (3/8)..." as SSE events arrive

#### Scenario: Generation completes
- **WHEN** the sub-board generation completes successfully
- **THEN** the panel transitions to show the sub-board section with title, progress, and "Open Sub-Board" button

#### Scenario: Generation fails with retry
- **WHEN** the sub-board generation fails
- **THEN** the panel shows an error message "Failed to generate sub-board" with a "Try Again" button that restarts the question flow

### Requirement: Sub-Board Task Node in Dagre Layout
The system SHALL handle sub-board task nodes in the dagre auto-layout. Sub-board task nodes (tasks with `sub_board_id` set) SHALL use the same dimensions as regular task nodes (280x100). The dashed border styling SHALL be applied via the node data, not the layout utility. The dagre layout utility SHALL pass `has_sub_board: true` in node data for sub-board tasks so the TaskNode component can apply the appropriate visual treatment.

#### Scenario: Sub-board task positioned normally in layout
- **WHEN** the dagre layout computes positions for a board with 2 regular tasks and 1 sub-board task
- **THEN** all 3 tasks are positioned using the same dimensions and spacing rules

#### Scenario: Sub-board flag passed in node data
- **WHEN** the dagre layout processes a task with `sub_board_id` set
- **THEN** the resulting React Flow node data includes `has_sub_board: true`

