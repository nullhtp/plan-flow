# simple-mode Specification

## Purpose
TBD - created by archiving change add-simple-mode. Update Purpose after archive.
## Requirements
### Requirement: Simple Mode Setting Persistence

The system SHALL store a per-user `simple_mode` boolean on the `UserSettings` model, defaulting
to `true`. The value SHALL be returned by `GET /api/settings` and updatable via
`PATCH /api/settings` alongside `memory_enabled`. An Alembic migration SHALL add the column as
non-null with a server default of `true` so existing users are backfilled to Simple mode.

#### Scenario: New user defaults to Simple mode
- **WHEN** a user with no stored settings calls `GET /api/settings`
- **THEN** the response includes `simple_mode: true`

#### Scenario: Toggle persists via PATCH
- **WHEN** a user sends `PATCH /api/settings` with `{ "simple_mode": false }`
- **THEN** the value is persisted and subsequent `GET /api/settings` responses return `simple_mode: false`

#### Scenario: Existing rows backfilled by migration
- **WHEN** the Alembic migration runs against a database with existing `user_settings` rows
- **THEN** every existing row receives `simple_mode = true`

### Requirement: Simple Mode Master Toggle in Settings

The settings page SHALL display a **Simple mode** toggle at the top of the page, above the AI
Memory toggle. It SHALL reflect the current `simple_mode` value from `GET /api/settings`, and
toggling it SHALL send `PATCH /api/settings` with the new value and update optimistically. A
short description SHALL explain the toggle (e.g. "Simplify the whole app — hide advanced
controls and guide you step by step."). If the request fails, the toggle SHALL revert and a
toast SHALL indicate the failure.

#### Scenario: Disable Simple mode from settings
- **WHEN** a user switches the Simple mode toggle off
- **THEN** the toggle updates immediately, a `PATCH /api/settings` request with `simple_mode: false` is sent, and advanced UI becomes available across the app

#### Scenario: Enable Simple mode from settings
- **WHEN** a user switches the Simple mode toggle on
- **THEN** the toggle updates immediately and the app re-renders its simplified UI across screens

#### Scenario: Toggle failure rollback
- **WHEN** the `PATCH /api/settings` request to update `simple_mode` fails
- **THEN** the toggle reverts to its previous state and a toast shows an update-failed message

### Requirement: Simple Mode Source of Truth

The frontend SHALL expose a single `useSimpleMode()` hook that reads `simple_mode` from the
settings query and returns an `isSimpleMode` boolean. While the settings query is loading,
`isSimpleMode` SHALL default to `true` so the app never renders advanced UI before the setting
resolves. Every screen that conditions on Simple mode SHALL derive its rendering from this
single value.

#### Scenario: Default to Simple while loading
- **WHEN** the settings query has not yet resolved
- **THEN** `useSimpleMode()` returns `isSimpleMode: true`

#### Scenario: Resolves to stored value
- **WHEN** the settings query resolves with `simple_mode: false`
- **THEN** `useSimpleMode()` returns `isSimpleMode: false` and dependent screens render their full UI

### Requirement: Dashboard Simplification in Simple Mode

While Simple mode is enabled, the dashboard SHALL hide the "My Boards / Shared with Me" view
toggle and render only the user's own boards alongside the New Board card. Board cards SHALL
render a simplified variant showing the board title and a plain percent-complete value, without
the goal subtitle and without the progress bar. While Simple mode is disabled, the dashboard
SHALL render the full layout (My/Shared toggle and detailed cards).

#### Scenario: Shared toggle hidden in Simple mode
- **WHEN** a user with Simple mode enabled opens the dashboard
- **THEN** the "My Boards / Shared with Me" toggle is not rendered and only owned boards plus the New Board card are shown

#### Scenario: Simplified board cards in Simple mode
- **WHEN** a user with Simple mode enabled views the boards grid
- **THEN** each card shows the title and a plain "% done" value, without the goal subtitle or progress bar

#### Scenario: Full dashboard when Simple mode is off
- **WHEN** a user with Simple mode disabled opens the dashboard
- **THEN** the My/Shared toggle and the detailed board cards (goal subtitle and progress bar) are shown

### Requirement: Templates Restricted to Creation-Only in Simple Mode

While Simple mode is enabled, the Templates tab SHALL remain available for browsing, and
selecting a template SHALL start the create-board-from-template flow directly. The template
detail editor, template structure editing/saving, the template task detail editing panel, and
the template authoring/generation flow SHALL NOT be reachable in Simple mode. While Simple mode
is disabled, the full template browse/view/edit/author experience SHALL be available.

#### Scenario: Use a template to create a board in Simple mode
- **WHEN** a user with Simple mode enabled selects a template from the Templates tab
- **THEN** the create-board-from-template flow starts directly without opening the template editor

#### Scenario: Template editing and authoring hidden in Simple mode
- **WHEN** a user with Simple mode enabled is on the Templates tab
- **THEN** there is no entry point to edit a template's structure or to author/generate a new template, and navigating to a template editor or generation route does not present editing controls

#### Scenario: Full template experience when Simple mode is off
- **WHEN** a user with Simple mode disabled opens a template
- **THEN** the template detail editor, structure save, and template generation flow are available

### Requirement: Settings Page Simplification in Simple Mode

While Simple mode is enabled, the settings page SHALL show only the Simple mode and AI Memory
toggle cards (each with its description) and SHALL hide the memory statistics, the search input,
the category filter, the editable memory list, the bulk-clear action, and pagination. While
Simple mode is disabled, the full memory-management UI SHALL be shown.

#### Scenario: Only toggles shown in Simple mode
- **WHEN** a user with Simple mode enabled opens the settings page
- **THEN** only the Simple mode and AI Memory toggle cards are rendered, and the memory statistics, search, category filter, memory list, bulk clear, and pagination are not rendered

#### Scenario: Full memory management when Simple mode is off
- **WHEN** a user with Simple mode disabled opens the settings page
- **THEN** the memory statistics, search, category filter, editable memory list, bulk clear, and pagination are all rendered

### Requirement: Goal Flow Simplification in Simple Mode

While Simple mode is enabled, the goal/question flow SHALL hide the readiness percentage
indicator (and its summary text) and instead present a plain "Ready to generate" state on the
generate footer once generation is allowed; answered question rounds SHALL render as a read-only
summary without expand or Edit affordances; and technical "Round N" labels SHALL be replaced
with friendlier progress wording. Example-goal chips SHALL remain visible. While Simple mode is
disabled, the full goal flow (readiness indicator, editable past rounds, round labels) SHALL be
shown.

#### Scenario: Readiness gauge hidden in Simple mode
- **WHEN** a user with Simple mode enabled progresses through the question flow
- **THEN** the readiness percentage indicator is not rendered and the generate footer shows a plain "Ready to generate" state once generation is allowed

#### Scenario: Past rounds read-only in Simple mode
- **WHEN** a user with Simple mode enabled has answered one or more question rounds
- **THEN** the answered rounds appear as a read-only summary without expand or Edit controls

#### Scenario: Friendlier progress labels in Simple mode
- **WHEN** a user with Simple mode enabled is asked a follow-up round of questions
- **THEN** the round is labeled with friendly progress wording rather than "Round N"

#### Scenario: Full goal flow when Simple mode is off
- **WHEN** a user with Simple mode disabled progresses through the question flow
- **THEN** the readiness indicator, editable past rounds, and round labels are shown

### Requirement: Board Header Simplification in Simple Mode

While Simple mode is enabled, the board header SHALL hide the "Save as Template", "Share", and
"Memories" actions, and the share panel and board memory sidebar SHALL be unreachable from the
board. The breadcrumb navigation, the (editable) board title, and the guided stepper SHALL
remain. While Simple mode is disabled, the full board header (including those actions) SHALL be
shown.

#### Scenario: Power actions hidden in Simple mode
- **WHEN** a user with Simple mode enabled opens a board
- **THEN** the Save as Template, Share, and Memories actions are not rendered and their panels/sidebars cannot be opened from the board

#### Scenario: Breadcrumb and title remain in Simple mode
- **WHEN** a user with Simple mode enabled opens a board
- **THEN** the breadcrumb navigation, the board title, and the stepper are still shown

#### Scenario: Full header when Simple mode is off
- **WHEN** a user with Simple mode disabled opens a board
- **THEN** the Save as Template, Share, and Memories actions are rendered in the header

