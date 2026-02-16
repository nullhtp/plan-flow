## ADDED Requirements

### Requirement: Kanban Board Layout
The system SHALL render a board as a horizontally scrollable layout with columns displayed side-by-side. Each column SHALL display its title as a header and its tasks as vertically stacked cards below the header. The board title SHALL be displayed above the columns. The layout SHALL be responsive — on narrow viewports, columns scroll horizontally.

#### Scenario: Board renders with columns and tasks
- **WHEN** an authenticated user navigates to `/boards/:boardId`
- **THEN** the page displays the board title, columns arranged horizontally, and task cards within each column ordered by position

#### Scenario: Empty column displayed
- **WHEN** a column has no tasks
- **THEN** the column is rendered with its header and an empty area with a prompt to add tasks

#### Scenario: Board with many columns scrolls horizontally
- **WHEN** the board has more columns than fit in the viewport
- **THEN** the user can scroll horizontally to see all columns

### Requirement: Task Card Display
The system SHALL render each task as a card within its column showing the task title. If the task has a priority set, a color-coded indicator SHALL be visible on the card (e.g., red for high, yellow for medium, green for low). If the task has a due date, it SHALL be displayed on the card. If the task has subtasks, a progress indicator SHALL show the count of completed vs total subtasks (e.g., "2/5").

#### Scenario: Task card with all metadata
- **WHEN** a task has title, priority "high", due date, and 3 subtasks (1 completed)
- **THEN** the card shows the title, a high-priority indicator, the due date, and "1/3" subtask progress

#### Scenario: Task card with no metadata
- **WHEN** a task has only a title (no priority, due date, or subtasks)
- **THEN** the card shows only the title

### Requirement: Drag-and-Drop Tasks
The system SHALL enable drag-and-drop for task cards using `@dnd-kit`. Users SHALL be able to drag a task to a different position within the same column (reorder) or to a different column (move). During drag, the dragged card SHALL have a visual drag overlay. Drop targets SHALL be visually indicated. On drop, the UI SHALL update optimistically and send a `PATCH /api/tasks/:id` request with the new `position` and optionally `column_id`.

#### Scenario: Reorder task within column
- **WHEN** a user drags a task from position 2 to position 0 in the same column
- **THEN** the UI immediately reflects the new order and a PATCH request is sent with the new fractional index position

#### Scenario: Move task to another column
- **WHEN** a user drags a task from "To Do" column and drops it into "In Progress" column
- **THEN** the UI immediately moves the card to the target column and a PATCH request is sent with the new `column_id` and `position`

#### Scenario: Drag-and-drop server error rollback
- **WHEN** the server returns an error for the reorder/move PATCH request
- **THEN** the UI reverts to the previous state and displays an error toast

### Requirement: Drag-and-Drop Columns
The system SHALL enable drag-and-drop for columns using `@dnd-kit`. Users SHALL be able to drag columns to reorder them horizontally. On drop, the UI SHALL update optimistically and send a `PATCH /api/columns/:id` request with the new `position`.

#### Scenario: Reorder columns
- **WHEN** a user drags the third column to the first position
- **THEN** the UI immediately reflects the new column order and a PATCH request is sent with the new fractional index position

#### Scenario: Column reorder server error rollback
- **WHEN** the server returns an error for the column reorder PATCH request
- **THEN** the UI reverts to the previous column order and displays an error toast

### Requirement: Task Detail Side Panel
The system SHALL display a slide-out side panel on the right when a user clicks a task card. The panel SHALL contain editable fields for: title (text input), description (textarea), due date (date picker), priority (select: low/medium/high/none), estimated minutes (number input), and a subtask checklist. The panel SHALL have a close button. The board SHALL remain visible behind the panel. The panel state SHALL be reflected in the URL via a `task` search parameter (`?task=<taskId>`) so that direct linking and browser navigation work.

#### Scenario: Open task detail panel
- **WHEN** a user clicks a task card
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

### Requirement: Add Column Inline
The system SHALL display an "+ Add Column" button after the last column on the board. Clicking the button SHALL reveal an inline text input for the column title. Pressing Enter or clicking a confirm button SHALL create the column optimistically and send a `POST /api/boards/:id/columns` request. Pressing Escape SHALL cancel the input.

#### Scenario: Add new column
- **WHEN** a user clicks "+ Add Column", types "Review", and presses Enter
- **THEN** a new column "Review" appears at the end of the board immediately (optimistic) and a POST request creates it on the server

#### Scenario: Cancel add column
- **WHEN** a user clicks "+ Add Column" and then presses Escape
- **THEN** the inline input disappears and no column is created

### Requirement: Add Task Inline
The system SHALL display an "+ Add Task" button at the bottom of each column. Clicking the button SHALL reveal an inline text input for the task title. Pressing Enter SHALL create the task optimistically and send a `POST /api/columns/:id/tasks` request. Pressing Escape SHALL cancel the input.

#### Scenario: Add new task
- **WHEN** a user clicks "+ Add Task" in a column, types "Book flight", and presses Enter
- **THEN** a new task card appears at the bottom of the column immediately (optimistic) and a POST request creates it on the server

#### Scenario: Cancel add task
- **WHEN** a user clicks "+ Add Task" and then presses Escape
- **THEN** the inline input disappears and no task is created

### Requirement: Edit Column Title Inline
The system SHALL allow users to edit a column title by double-clicking the column header. Double-clicking SHALL transform the header into an editable text input. Pressing Enter or clicking outside (blur) SHALL save the change via `PATCH /api/columns/:id`. Pressing Escape SHALL cancel the edit and revert to the original title.

#### Scenario: Edit column title
- **WHEN** a user double-clicks a column header, changes the text, and presses Enter
- **THEN** the column title updates immediately (optimistic) and a PATCH request updates it on the server

#### Scenario: Cancel column title edit
- **WHEN** a user double-clicks a column header and presses Escape
- **THEN** the header reverts to the original title

### Requirement: Delete Column with Confirmation
The system SHALL provide a delete option for columns (e.g., via a context menu or icon button on the column header). If the column contains tasks, a confirmation dialog SHALL appear showing the task count and a dropdown to select a target column for task migration. The dialog SHALL have "Move & Delete" and "Cancel" buttons. If the column is empty, the deletion proceeds after a simpler confirmation. The last remaining column on a board SHALL NOT be deletable.

#### Scenario: Delete column with tasks
- **WHEN** a user clicks delete on a column with 5 tasks
- **THEN** a dialog appears showing "This column has 5 tasks. Select a column to move them to:" with a dropdown of other columns

#### Scenario: Confirm column deletion with task migration
- **WHEN** the user selects a target column and clicks "Move & Delete"
- **THEN** the column is removed from the UI (optimistic), tasks appear in the target column, and a DELETE request with `target_column_id` is sent

#### Scenario: Delete empty column
- **WHEN** a user clicks delete on a column with no tasks
- **THEN** a simpler confirmation dialog appears and upon confirmation the column is deleted

#### Scenario: Cannot delete last column
- **WHEN** the board has only one column
- **THEN** the delete option is disabled or hidden for that column

### Requirement: Delete Task
The system SHALL provide a delete option for tasks (e.g., via a context menu on the task card or a delete button in the task detail panel). Deleting a task SHALL show a brief confirmation and then remove the task optimistically, sending a `DELETE /api/tasks/:id` request.

#### Scenario: Delete task from detail panel
- **WHEN** a user clicks "Delete" in the task detail panel and confirms
- **THEN** the panel closes, the task card is removed from the column immediately, and a DELETE request is sent

#### Scenario: Delete task from card context menu
- **WHEN** a user right-clicks or clicks a menu on a task card and selects "Delete"
- **THEN** the task card is removed immediately (optimistic) and a DELETE request is sent

### Requirement: Board List on Home Page
The system SHALL display a list of the authenticated user's boards on the index page (`/`). Each board SHALL be rendered as a card showing the board title, goal summary (goal title or input), column count, task progress (e.g., "5/12 tasks"), and creation date. Clicking a board card SHALL navigate to `/boards/:boardId`. The board list SHALL be fetched via `GET /api/boards`. If the user has no boards, the page SHALL display a message encouraging them to create a goal.

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
The system SHALL display a skeleton loading state while the board data is being fetched. The skeleton SHALL approximate the kanban layout with placeholder columns and card shapes.

#### Scenario: Board loading skeleton
- **WHEN** a user navigates to `/boards/:boardId` and the data is loading
- **THEN** a skeleton layout is displayed with placeholder columns and cards

#### Scenario: Board loaded successfully
- **WHEN** the board data finishes loading
- **THEN** the skeleton is replaced with the actual board content

### Requirement: Optimistic Update Error Handling
The system SHALL display a toast notification when an optimistic update fails (server rejects the mutation). The toast SHALL include a brief error message. The UI SHALL revert to the state before the failed mutation. The board query SHALL be invalidated to re-sync with the server.

#### Scenario: Mutation failure toast and rollback
- **WHEN** a task move PATCH request fails with a server error
- **THEN** the task reverts to its original column and position, a toast displays "Failed to move task", and the board data is refetched

#### Scenario: Network error during mutation
- **WHEN** a mutation request fails due to network error
- **THEN** the UI reverts, a toast displays "Network error. Please try again.", and the board data is refetched
