## ADDED Requirements

### Requirement: Settings Page Route
The system SHALL provide a `/settings` route protected by the auth wrapper. The page SHALL display a tabbed or sectioned layout with a "Memory" section. The page SHALL be accessible via a user menu/avatar dropdown in the app header. The route SHALL be defined using TanStack Router.

#### Scenario: Navigate to settings
- **WHEN** an authenticated user clicks their avatar/menu in the header and selects "Settings"
- **THEN** the browser navigates to `/settings` and the settings page loads

#### Scenario: Unauthenticated redirect
- **WHEN** an unauthenticated user navigates to `/settings`
- **THEN** they are redirected to the login page

### Requirement: Memory Settings Toggle
The system SHALL display a "Memory" toggle switch in the settings page that controls whether the AI remembers information about the user. The toggle SHALL reflect the current `memory_enabled` state from `GET /api/settings`. Toggling SHALL send `PATCH /api/settings` with the new value. The toggle SHALL update optimistically. A description SHALL explain what the toggle does: "When enabled, the AI remembers your preferences, past goals, and patterns to personalize future experiences."

#### Scenario: Toggle memory off
- **WHEN** a user switches the memory toggle from on to off
- **THEN** the toggle updates immediately (optimistic), a PATCH request is sent, and the AI stops using memories for that user

#### Scenario: Toggle memory on
- **WHEN** a user switches the memory toggle from off to on
- **THEN** the toggle updates immediately and the AI resumes using memories

#### Scenario: Toggle failure rollback
- **WHEN** the PATCH request to update memory_enabled fails
- **THEN** the toggle reverts to its previous state and a toast shows "Failed to update setting"

### Requirement: Memory List in Settings
The system SHALL display a paginated list of the user's memories in the settings page Memory section. Each memory item SHALL show: the content text (truncatable), a category badge (colored pill: blue for preference, green for fact, purple for pattern, gray for context), the creation date, and the last used date (if set). The list SHALL support: text search via a search input (triggers semantic search via `GET /api/memories?q=...`), category filter dropdown, and pagination controls. The list SHALL show the total count of active memories. When the list is empty, a placeholder message SHALL say "No memories stored yet. The AI will remember information as you use PlanFlow."

#### Scenario: Display memory list
- **WHEN** a user with 25 memories visits the settings page
- **THEN** the first 20 memories are displayed with content, category badges, and dates, with pagination showing "1 of 2"

#### Scenario: Search memories
- **WHEN** a user types "budget" in the search input
- **THEN** the list updates to show memories semantically related to "budget", ordered by relevance

#### Scenario: Filter by category
- **WHEN** a user selects "Preferences" from the category filter
- **THEN** only memories with category "preference" are displayed

#### Scenario: Empty memory list
- **WHEN** a new user with no memories visits settings
- **THEN** a placeholder message is shown instead of an empty list

### Requirement: Memory Edit in Settings
The system SHALL allow users to edit a memory's content inline in the memory list. Clicking a memory item or an edit icon SHALL make the content editable (inline text input or a small modal). Saving SHALL send `PATCH /api/memories/{id}` with the new content. The update SHALL be optimistic. A brief note SHALL inform the user that editing triggers re-embedding for search accuracy.

#### Scenario: Edit memory inline
- **WHEN** a user clicks edit on a memory with content "Budget: $3000" and changes it to "Budget: $5000-8000"
- **THEN** the content updates immediately (optimistic), a PATCH request is sent, and the memory's embedding is regenerated server-side

#### Scenario: Cancel edit
- **WHEN** a user starts editing a memory and presses Escape
- **THEN** the edit is cancelled and the original content is restored

#### Scenario: Edit failure rollback
- **WHEN** the PATCH request fails
- **THEN** the memory reverts to its original content and a toast shows "Failed to update memory"

### Requirement: Memory Delete in Settings
The system SHALL allow users to delete individual memories from the memory list. Each memory item SHALL have a delete button (trash icon). Clicking delete SHALL show a brief confirmation (inline or toast-based, not a full modal). Upon confirmation, the memory is removed optimistically and `DELETE /api/memories/{id}` is sent.

#### Scenario: Delete single memory
- **WHEN** a user clicks delete on a memory and confirms
- **THEN** the memory disappears from the list immediately and a DELETE request is sent

#### Scenario: Delete failure rollback
- **WHEN** the DELETE request fails
- **THEN** the memory reappears in the list and a toast shows "Failed to delete memory"

### Requirement: Bulk Memory Clear in Settings
The system SHALL provide a "Clear All Memories" button in the settings page. Clicking it SHALL show a confirmation dialog warning: "This will permanently remove all your stored memories. The AI will no longer have context from your past interactions. This cannot be undone." Upon confirmation, `DELETE /api/memories` is sent. The list SHALL clear optimistically. An optional category-specific clear SHALL be available via the category filter (e.g., "Clear all preferences").

#### Scenario: Clear all memories
- **WHEN** a user clicks "Clear All Memories" and confirms
- **THEN** all memories are removed from the list, a DELETE request is sent, and the stats update to show 0 active

#### Scenario: Clear by category
- **WHEN** a user filters by "Preferences" and clicks "Clear filtered"
- **THEN** all preference memories are archived and removed from the list

#### Scenario: Clear cancelled
- **WHEN** a user clicks "Clear All Memories" and cancels the confirmation
- **THEN** no memories are deleted

### Requirement: Memory Statistics in Settings
The system SHALL display memory statistics above the memory list, fetched from `GET /api/memories/stats`. Statistics SHALL include: total active memories count, a breakdown by category (shown as small colored counts or a mini chart), and the date range (oldest to newest memory). If memory is disabled, the stats area SHALL show "Memory is disabled" with a prompt to enable it.

#### Scenario: Display memory stats
- **WHEN** a user with 45 active memories visits settings
- **THEN** the stats show "45 memories" with a breakdown like "Preferences: 20, Facts: 10, Patterns: 8, Context: 7"

#### Scenario: Stats with memory disabled
- **WHEN** a user with memory disabled visits settings
- **THEN** the stats area shows "Memory is disabled" and a link to the toggle

### Requirement: Board Memory Sidebar
The system SHALL provide a collapsible "AI Memory" sidebar panel on the board page. The panel SHALL be toggled via a brain/memory icon button in the board toolbar (near the board title area). When open, the panel SHALL display memories relevant to the current board's goal, fetched from `GET /api/boards/{board_id}/memories`. Each memory item SHALL show: content text, category badge, and a relevance score indicator (e.g., a small bar or percentage). Each memory item SHALL have edit and delete buttons (same behavior as settings page). The panel SHALL show a link to "Manage all memories" pointing to `/settings`. When no relevant memories are found, the panel SHALL show "No relevant memories for this board."

#### Scenario: Open memory sidebar on board
- **WHEN** a user clicks the memory icon in the board toolbar
- **THEN** a sidebar panel slides in showing memories relevant to the board's goal, sorted by relevance

#### Scenario: Edit memory from board sidebar
- **WHEN** a user edits a memory in the board sidebar
- **THEN** the memory content is updated via PATCH, the sidebar refreshes, and the change is reflected in settings too

#### Scenario: Delete memory from board sidebar
- **WHEN** a user deletes a memory from the board sidebar
- **THEN** the memory is soft-deleted and removed from the sidebar list

#### Scenario: Close memory sidebar
- **WHEN** a user clicks the memory icon again or clicks outside the panel
- **THEN** the sidebar closes

#### Scenario: No relevant memories
- **WHEN** a board's goal has no relevant memories
- **THEN** the sidebar shows "No relevant memories for this board." with a link to settings

### Requirement: Memory Badges on Chat Messages
The system SHALL display small pill badges under AI chat messages showing which memories were used to generate the response. Badges SHALL be rendered based on the `used_memory_ids` field in the `ChatResponse`. Each badge SHALL show a truncated preview of the memory content (first 30 characters + ellipsis). Clicking a badge SHALL open a popover showing the full memory content, category, and a "View in Settings" link. If `used_memory_ids` is empty, no badges are shown. Badges SHALL use a subtle styling (muted background, small text) to avoid cluttering the chat.

#### Scenario: AI message with memory badges
- **WHEN** the AI responds with `used_memory_ids: ["mem-1", "mem-2"]` and those memories have content "Budget: $3000-5000" and "Preferred language: Russian"
- **THEN** two pill badges appear under the AI message: "Budget: $3000-5000" and "Preferred language: Ru..."

#### Scenario: Click memory badge to view details
- **WHEN** a user clicks a memory badge
- **THEN** a popover shows the full memory content, category badge, and a "View in Settings" link

#### Scenario: No memory badges when empty
- **WHEN** the AI responds with `used_memory_ids: []`
- **THEN** no memory badges are displayed under the message

#### Scenario: Memory badges with memory disabled
- **WHEN** a user with memory disabled receives a chat response
- **THEN** `used_memory_ids` is empty and no badges appear

### Requirement: Memory Badge Data Resolution
The system SHALL resolve memory badge content from a client-side cache. When the settings page or board memory sidebar loads memories, those memories SHALL be stored in a React Query cache keyed by memory ID. When rendering badges, the system SHALL first check the cache for each `used_memory_id`. For cache misses, the system SHALL fetch `GET /api/memories/{id}` lazily. This avoids adding memory content to every chat response payload.

#### Scenario: Badge content from cache
- **WHEN** a user has already loaded the settings page (memories cached) and receives a chat response with `used_memory_ids`
- **THEN** the badge content is resolved from the React Query cache without additional API calls

#### Scenario: Badge content via lazy fetch
- **WHEN** a chat response includes a `used_memory_id` not in the cache
- **THEN** the system fetches `GET /api/memories/{id}` to resolve the content, showing a loading skeleton badge until resolved

#### Scenario: Deleted memory in badge
- **WHEN** a chat response references a `used_memory_id` that has been deleted
- **THEN** the badge shows "Memory removed" in muted text and is not clickable
