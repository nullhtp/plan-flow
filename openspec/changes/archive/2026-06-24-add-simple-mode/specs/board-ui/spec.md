## MODIFIED Requirements

### Requirement: Interface Mode Selection

The board interface mode SHALL be governed by the global, server-persisted **Simple mode** user
setting (see the `simple-mode` capability), not by a per-board choice. When Simple mode is
**enabled**, every board SHALL render in the **Simple** guided stepper, and the board header
SHALL NOT show a Simple/Advanced switch or the Focus/Full toggle. When Simple mode is
**disabled**, every board SHALL render in **Advanced** (the DAG graph) by default, and the
board header SHALL show the Focus/Full toggle together with a per-session **Simple/Advanced**
segmented control that lets the user open the stepper for a board without changing the global
setting. The per-session control SHALL persist in browser local storage (key
`planflow:board-interface-mode`), SHALL be rendered **only** while Simple mode is disabled, and
SHALL default to **Advanced**. While the global Simple mode setting is still loading, the board
SHALL default to the Simple stepper to avoid flashing the DAG. The Simple/Advanced choice SHALL
NOT be encoded in the URL; the existing `view` and `task` search parameters SHALL continue to
function within Advanced mode.

#### Scenario: Board follows the global Simple mode setting
- **WHEN** a user whose `simple_mode` setting is `true` opens `/boards/:boardId`
- **THEN** the board renders in the Simple guided stepper and no Simple/Advanced or Focus/Full switch is shown in the header

#### Scenario: Disabling Simple mode reveals the DAG and its toggles
- **WHEN** a user whose `simple_mode` setting is `false` opens `/boards/:boardId`
- **THEN** the board renders the DAG (Advanced) by default, the Focus/Full toggle is shown, and a per-session Simple/Advanced control is shown

#### Scenario: Per-session preview when Simple mode is off
- **WHEN** a user with Simple mode disabled clicks "Simple" on the per-session control of one board
- **THEN** that board re-renders as the stepper and `simple` is written to the `planflow:board-interface-mode` local storage key, without changing the global `simple_mode` setting

#### Scenario: Default to stepper while the setting loads
- **WHEN** the global settings query has not yet resolved on board open
- **THEN** the board renders the Simple stepper rather than flashing the DAG

#### Scenario: Setting applies across all boards
- **WHEN** a user's `simple_mode` setting is `true` and they open several different boards
- **THEN** every board opens in the Simple stepper because the mode is global

### Requirement: Board View Mode Toggle

The system SHALL provide, **while the Advanced interface mode is active** (i.e. global Simple
mode is off and the per-session control is not previewing the stepper), a toggle control in the
board header toolbar that switches the DAG between two view modes: **Focus** and **Full**. The
toggle SHALL be rendered as a segmented control or switch with labels "Focus" and "Full DAG",
placed alongside the other Advanced-mode toolbar buttons (Share, Save as Template, Memories).
The default DAG view mode SHALL be Focus when no `view` search parameter is present in the URL.
The active view mode SHALL be persisted in the URL via a `view` search parameter
(`?view=focus` or `?view=full`) so that direct linking and browser back/forward navigation
preserve the selected mode. While the **Simple** interface mode is active, the Focus/Full toggle
SHALL NOT be rendered and the `view` parameter SHALL have no visible effect until Advanced mode
is active.

#### Scenario: Default DAG view mode is Focus in Advanced
- **WHEN** a user is in Advanced mode and navigates to `/boards/:boardId` without a `view` search parameter
- **THEN** the DAG renders in Focus mode and the toggle shows "Focus" as active

#### Scenario: No board view toggles in Simple mode
- **WHEN** a user is in Simple mode
- **THEN** neither the Focus/Full toggle nor a Simple/Advanced switch is rendered in the header

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
