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
The system SHALL display a slide-out side panel on the right when a user clicks a task node in the DAG. The panel SHALL contain editable fields for: title (text input), description (textarea), due date (date picker), priority (select: low/medium/high/none), estimated minutes (number input), status (select: not_started/in_progress/done with lock enforcement), and a subtask checklist. The panel SHALL show a "Dependencies" section listing prerequisite tasks (read-only, linking to those tasks). The panel SHALL show an "Unlocks" section listing dependent tasks (read-only). The panel SHALL show an "AI Actions" section with contextual action buttons generated by the AI (see task-chat-ui spec). The panel SHALL show an "Artifacts" section listing persistent content generated by the AI (see task-artifacts spec). The panel SHALL show a "Chat" section at the bottom for conversing with the AI about this task (see task-chat-ui spec). The panel SHALL have a close button. The graph SHALL remain visible behind the panel. The panel state SHALL be reflected in the URL via a `task` search parameter (`?task=<taskId>`) so that direct linking and browser navigation work. All sections SHALL be in a single scrollable view in the order: Status, Title, Description, Metadata, Dependencies, Unlocks, Subtasks (or Sub-Board), AI Actions, Artifacts, Chat. **Sub-board section**: When a task has a sub-board (`sub_board_id` is non-null), the Subtasks section SHALL be replaced by a "Sub-Board" section showing the sub-board title, progress summary (e.g., "3/8 tasks completed"), and a prominent "Open Sub-Board" button that navigates to `/boards/:subBoardId`. **Sub-board creation**: When a task has no sub-board and belongs to a root-level board, the panel SHALL show an "Expand to Board" button below the subtasks section. Clicking this button SHALL navigate to `/boards/$boardId/expand/$taskId` to start the full-screen sub-board creation flow. If the task has existing subtasks, a confirmation dialog SHALL warn the user that subtasks will be replaced before navigating. The panel SHALL NOT contain any inline sub-board creation flow (questions, generation progress, or completion states).

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

#### Scenario: Expand to Board button navigates to expansion page
- **WHEN** a user clicks "Expand to Board" on a task with no sub-board on a root board
- **THEN** the browser navigates to `/boards/$boardId/expand/$taskId`

#### Scenario: No Expand to Board button on sub-board task
- **WHEN** a user opens the detail panel for a task on a sub-board
- **THEN** no "Expand to Board" button is shown

#### Scenario: Expand to Board with existing subtasks shows confirmation then navigates
- **WHEN** a user clicks "Expand to Board" for a task that has 4 existing subtasks
- **THEN** a confirmation dialog warns "This will replace the 4 existing subtasks with a detailed sub-board. Continue?" and on confirmation navigates to `/boards/$boardId/expand/$taskId`

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
The system SHALL display the authenticated user's dashboard on the index page (`/`) using a tabbed layout with two top-level tabs: **Boards** and **Templates**. The tabs SHALL use the Shadcn Tabs component (Radix-based) for proper accessibility and semantics. The active tab SHALL be persisted in the URL via a `tab` search parameter (e.g., `/?tab=templates`) so that direct linking and browser navigation work. The default tab SHALL be "Boards" when no `tab` parameter is present.

**Boards tab**: SHALL display boards in a responsive card grid with a secondary toggle between "My Boards" and "Shared with Me" views (using the same button-toggle pattern as the public/my toggle in the Templates tab). The default secondary view SHALL be "My Boards". In the "My Boards" view, the first card in the grid SHALL be a "Create Board" card -- a visually distinct card with a "+" icon and label (e.g., "+ New Board") styled as an actionable placeholder at the same size as board cards. Clicking the creation card SHALL navigate to `/goals/new`. Remaining cards SHALL be `BoardCard` components showing board title, goal summary, task progress, and creation date. Clicking a board card SHALL navigate to `/boards/:boardId`. If the user has no boards, only the "+" creation card SHALL be displayed (no separate empty state message needed since the "+" card serves as the call-to-action). In the "Shared with Me" view, boards shared with the user (fetched via `GET /api/boards?shared=true`) SHALL be displayed in the same card grid layout. No creation card SHALL appear in this view. If no shared boards exist, a message like "No shared boards yet" SHALL be displayed.

**Templates tab**: SHALL embed the full templates gallery previously at `/templates`, including: public/my templates toggle (as a secondary toggle within the tab, using the same button-toggle pattern as the Boards tab), category filter, search input, pagination, and template cards in a grid. The first card in the template grid SHALL be a "Create Template" card -- a visually distinct card with a "+" icon and label (e.g., "+ Create Template") at the same size as template cards. Clicking the creation card SHALL navigate to `/templates/generate`. The "+" creation card SHALL appear in both "Public Templates" and "My Templates" sub-views.

The dashboard header SHALL be simplified: PlanFlow logo/text on the left, and a user dropdown menu on the right. The user dropdown SHALL display the user's email or avatar and contain menu items for "Settings" (navigates to `/settings`) and "Log out" (triggers logout). The "New Goal", "Templates", and standalone "Settings" / "Log out" buttons SHALL be removed from the header.

#### Scenario: Home page shows tabbed layout with Boards default
- **WHEN** an authenticated user visits `/`
- **THEN** the page displays two tabs: "Boards" (active by default) and "Templates", with the Boards tab showing the "My Boards" secondary view containing a "+" creation card as the first item followed by board cards

#### Scenario: Create Board card navigates to goal creation
- **WHEN** a user clicks the "+" creation card in the Boards tab "My Boards" view
- **THEN** the browser navigates to `/goals/new`

#### Scenario: My Boards view with no boards shows only creation card
- **WHEN** an authenticated user with no boards views the "My Boards" secondary view
- **THEN** only the "+" creation card is displayed in the grid

#### Scenario: Shared with Me view shows shared boards
- **WHEN** a user toggles to the "Shared with Me" secondary view within the Boards tab and has 2 shared boards
- **THEN** the view shows 2 board cards with no creation card

#### Scenario: Shared with Me view empty state
- **WHEN** a user toggles to the "Shared with Me" secondary view and has no shared boards
- **THEN** a message "No shared boards yet" is displayed

#### Scenario: Templates tab shows template gallery with creation card
- **WHEN** a user clicks the "Templates" tab
- **THEN** the tab content shows the template gallery with a "+" creation card as the first item, public/my toggle, category filter, search, and template cards

#### Scenario: Templates creation card navigates to generate wizard
- **WHEN** a user clicks the "+" creation card in the Templates tab
- **THEN** the browser navigates to `/templates/generate`

#### Scenario: Tab state persisted in URL
- **WHEN** a user clicks the "Templates" tab
- **THEN** the URL updates to `/?tab=templates`

#### Scenario: Direct link to tab
- **WHEN** a user navigates to `/?tab=templates`
- **THEN** the "Templates" tab is active

#### Scenario: Simplified header with user dropdown
- **WHEN** an authenticated user views the dashboard
- **THEN** the header shows the PlanFlow logo on the left and a user dropdown on the right containing "Settings" and "Log out" options

#### Scenario: Navigate to settings from dropdown
- **WHEN** a user opens the dropdown and clicks "Settings"
- **THEN** the browser navigates to `/settings`

#### Scenario: Log out from dropdown
- **WHEN** a user opens the dropdown and clicks "Log out"
- **THEN** the user is logged out and redirected to the login page

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
The system SHALL NOT render any inline sub-board creation flow within the task detail panel. The "Expand to Board" button SHALL navigate to the dedicated full-screen sub-board expansion page at `/boards/$boardId/expand/$taskId`. All question rendering, generation progress, and completion states are handled by the expansion page (see `board-generation-progress` spec for sub-board generation progress requirements).

#### Scenario: No inline creation flow in panel
- **WHEN** a user clicks "Expand to Board" on a task
- **THEN** the browser navigates to the expansion page instead of showing any inline questions or progress within the panel

### Requirement: Sub-Board Task Node in Dagre Layout
The system SHALL handle sub-board task nodes in the dagre auto-layout. Sub-board task nodes (tasks with `sub_board_id` set) SHALL use the same dimensions as regular task nodes (280x100). The dashed border styling SHALL be applied via the node data, not the layout utility. The dagre layout utility SHALL pass `has_sub_board: true` in node data for sub-board tasks so the TaskNode component can apply the appropriate visual treatment.

#### Scenario: Sub-board task positioned normally in layout
- **WHEN** the dagre layout computes positions for a board with 2 regular tasks and 1 sub-board task
- **THEN** all 3 tasks are positioned using the same dimensions and spacing rules

#### Scenario: Sub-board flag passed in node data
- **WHEN** the dagre layout processes a task with `sub_board_id` set
- **THEN** the resulting React Flow node data includes `has_sub_board: true`

### Requirement: Sub-Board Expansion Page
The system SHALL provide a dedicated full-screen page at route `/boards/$boardId/expand/$taskId` for creating a sub-board from a task. The page SHALL be protected by the existing auth route wrapper. The page SHALL implement a linear state machine with states: `loading-questions`, `questions`, `generating`, and `error`. The page SHALL display a context header showing the task title as the heading and "Expanding task from [Parent Board Title]" as the subtitle throughout all states.

#### Scenario: Navigate to expansion page
- **WHEN** an authenticated user navigates to `/boards/$boardId/expand/$taskId`
- **THEN** the page loads in the `loading-questions` state, showing a centered spinner with "Preparing questions..." and the task/board context header

#### Scenario: Unauthenticated user redirected
- **WHEN** an unauthenticated user navigates to `/boards/$boardId/expand/$taskId`
- **THEN** the user is redirected to the login page

#### Scenario: Task already has a sub-board
- **WHEN** a user navigates to `/boards/$boardId/expand/$taskId` for a task that already has a sub-board
- **THEN** the page redirects to `/boards/:existingSubBoardId`

#### Scenario: Task not found or invalid nesting
- **WHEN** a user navigates to `/boards/$boardId/expand/$taskId` for a non-existent task or a task on a sub-board
- **THEN** the page shows an error message and a link to return to the parent board

### Requirement: Sub-Board Expansion Questions State
The system SHALL render AI-generated sub-board questions as a full-screen centered form when in the `questions` state. The form SHALL use the same full-size question field components (`QuestionFieldWrapper`, `OptionField`, `MultiselectOptionField`) as the main goal creation form (without the `compact` prop). The form layout SHALL be a centered card (max-w-2xl) with the task title as heading, "Expanding task from [Parent Board Title]" as subtitle, and "Answer a few questions to help generate a detailed task board." as description. A "Generate Board" submit button SHALL be at the bottom, disabled until all required fields have values. A "Cancel" button SHALL navigate back to the parent board page.

#### Scenario: Questions rendered full-screen
- **WHEN** the sub-board questions API returns 3 questions
- **THEN** the page renders a full-screen centered card with 3 full-size question fields, rationale text, and a "Generate Board" button

#### Scenario: Required field validation
- **WHEN** a required question has no answer
- **THEN** the "Generate Board" button is disabled

#### Scenario: Cancel returns to parent board
- **WHEN** the user clicks "Cancel" on the questions form
- **THEN** the browser navigates back to `/boards/$boardId`

#### Scenario: Question loading failure
- **WHEN** the sub-board questions API returns an error
- **THEN** the page shows an error message with a "Try Again" button and a "Back to Board" link

### Requirement: Sub-Board Expansion Generation State
The system SHALL display a full-screen generation progress view when in the `generating` state, using the same progress component as the main board generation flow. The progress view SHALL connect to the SSE endpoint `POST /api/tasks/:id/generate-sub-board/stream` and display the board title, progress counter, progress bar, and task stack log with staggered reveal animation, identical to the main board generation progress. Upon receiving the `generation_complete` event, the page SHALL auto-navigate to `/boards/:subBoardId` after a 1.5-second delay.

#### Scenario: Generation progress displayed with SSE
- **WHEN** the user submits answers and generation starts
- **THEN** the page shows a full-screen progress view with "Creating board structure..." phase text, then real-time task enrichment progress via SSE events

#### Scenario: Auto-navigate to sub-board on completion
- **WHEN** the `generation_complete` SSE event is received with a board ID
- **THEN** the page shows "Board ready -- redirecting..." and after 1.5 seconds navigates to `/boards/:subBoardId`

#### Scenario: Generation error with retry
- **WHEN** a `generation_error` SSE event is received
- **THEN** the page shows "Generation failed" with a "Try Again" button and a "Back to Board" button

#### Scenario: Connection drop during generation
- **WHEN** the SSE connection drops after `skeleton_ready` but before `generation_complete`
- **THEN** an error message is displayed with "Connection lost. Your board may have been partially created." and a "Check your board" button linking to the partially created sub-board

### Requirement: DagView Template Preview Mode
The DagView component SHALL accept a `mode` prop with values `"board"` (default) or `"template-preview"`. In `template-preview` mode: (1) task and edge data SHALL be sourced from props/local state instead of API queries (React Query hooks), (2) React Flow connection handles SHALL be visible on all nodes to allow creating new edges by dragging, (3) edge deletion SHALL be enabled (click edge to select, then delete key or context menu), (4) an "Add Task" button SHALL be rendered above the graph that creates a new unconnected task node with a default title "New Task", (5) real-time DAG validation SHALL run after each structural change (add/remove task, add/remove edge) and display a toast error if the change creates a cycle or leaves the graph without a goal node, (6) the minimap, pan, and zoom behaviors SHALL remain identical to board mode, (7) task nodes in template-preview mode SHALL NOT show status controls (no status toggle) since template tasks have no status. An `onGraphChange` callback prop SHALL notify the parent component of any structural changes (task added/removed, edge added/removed, task fields updated).

#### Scenario: DagView renders in template-preview mode from local state
- **WHEN** DagView is rendered with `mode="template-preview"` and task/edge data passed as props
- **THEN** the graph renders without making any API calls for board data

#### Scenario: Connection handles visible for edge creation
- **WHEN** DagView is in template-preview mode
- **THEN** each task node displays source (bottom) and target (top) connection handles that the user can drag to create new edges

#### Scenario: Edge deletion in template-preview mode
- **WHEN** the user clicks an edge in template-preview mode and presses Delete
- **THEN** the edge is removed and the `onGraphChange` callback fires

#### Scenario: Add task button creates unconnected node
- **WHEN** the user clicks "Add Task" in template-preview mode
- **THEN** a new task node with title "New Task" appears in the graph, unconnected to any other node

#### Scenario: Cycle detected on edge creation
- **WHEN** the user drags an edge from task A to task B but B already has a path to A
- **THEN** the edge is not created and a toast error "Cannot create dependency: would create a cycle" appears

#### Scenario: No status controls in template-preview mode
- **WHEN** DagView is in template-preview mode
- **THEN** task nodes do not show status toggles or lock indicators

### Requirement: TaskDetailPanel Template Preview Mode
The TaskDetailPanel component SHALL accept a `mode` prop with values `"board"` (default) or `"template-preview"`. In `template-preview` mode: (1) editable fields SHALL include title, description, subtasks (add/remove/edit), priority, and estimated_minutes, (2) the Status field SHALL NOT be shown, (3) the Dependencies and Unlocks sections SHALL be shown as read-only lists (derived from the edge data in local state), (4) the AI Actions, Artifacts, and Chat sections SHALL NOT be shown, (5) the "Delete Task" button SHALL be available with confirmation (except for the goal node), (6) a "Set as Goal" toggle SHALL be available to designate a task as the goal node (removing the flag from any other task), (7) all edits SHALL update local state via an `onTaskChange` callback (no API calls), (8) the "Expand to Board" and "Sub-Board" sections SHALL NOT be shown. An `onDeleteTask` callback prop SHALL notify the parent when a task is deleted.

#### Scenario: Template-preview panel shows editable fields
- **WHEN** a user clicks a task node in template-preview mode
- **THEN** the panel shows title, description, subtasks, priority, and estimated_minutes as editable fields

#### Scenario: No status or AI sections in template-preview mode
- **WHEN** the TaskDetailPanel is in template-preview mode
- **THEN** Status, AI Actions, Artifacts, Chat, Expand to Board, and Sub-Board sections are hidden

#### Scenario: Delete task from panel
- **WHEN** the user clicks "Delete Task" on a non-goal task in template-preview mode
- **THEN** a confirmation dialog appears, and on confirm the `onDeleteTask` callback fires

#### Scenario: Set as Goal toggle
- **WHEN** the user toggles "Set as Goal" on a regular task in template-preview mode
- **THEN** that task becomes the goal node and the previous goal node is demoted to a regular task

#### Scenario: Cannot delete goal node
- **WHEN** the user opens the panel for the goal node in template-preview mode
- **THEN** the "Delete Task" button is disabled with a tooltip "Designate another task as the goal first"

### Requirement: Creation Card Component
The system SHALL provide a reusable `CreationCard` component that renders a card-sized actionable placeholder with a "+" icon and a configurable label. The card SHALL match the dimensions of sibling cards in the grid (e.g., same height as `BoardCard` or `TemplateCard`). The card SHALL have a dashed border, a subtle hover effect (e.g., background tint or border color change), and a pointer cursor. The card SHALL accept an `onClick` handler or `href` for navigation. The card SHALL be used as the first item in both the My Boards grid and the Templates grid.

#### Scenario: Creation card renders with label
- **WHEN** a `CreationCard` is rendered with label "+ New Board"
- **THEN** the card displays a "+" icon centered above the label text, with a dashed border and consistent size with adjacent cards

#### Scenario: Creation card hover effect
- **WHEN** a user hovers over a creation card
- **THEN** the card displays a subtle visual feedback (e.g., background tint change or border color change) with a pointer cursor

#### Scenario: Creation card click triggers navigation
- **WHEN** a user clicks a creation card configured with href="/goals/new"
- **THEN** the browser navigates to `/goals/new`

### Requirement: User Dropdown Menu
The system SHALL provide a `UserDropdown` component in the dashboard header that displays the authenticated user's email and, when clicked, opens a dropdown menu with options: "Settings" (navigates to `/settings`) and "Log out" (triggers the logout mutation and redirects to login). The dropdown SHALL use Shadcn's DropdownMenu component (Radix-based) for proper accessibility. The trigger SHALL display the user's email or a user avatar icon.

#### Scenario: User dropdown displays email
- **WHEN** the dashboard header renders
- **THEN** the user dropdown trigger shows the authenticated user's email

#### Scenario: Dropdown opens with menu items
- **WHEN** a user clicks the dropdown trigger
- **THEN** a menu appears with "Settings" and "Log out" items

#### Scenario: Settings navigation from dropdown
- **WHEN** a user selects "Settings" from the dropdown
- **THEN** the browser navigates to `/settings`

#### Scenario: Log out from dropdown
- **WHEN** a user selects "Log out" from the dropdown
- **THEN** the logout mutation is triggered and the user is redirected to the login page

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

