# Change: Add global Simple mode (a settings-driven simplified UI across all screens)

## Why

PlanFlow already ships a board-level **Simple/Advanced** toggle (the guided stepper vs. the
DAG), but it only simplifies the board. Every other screen — the dashboard, the goal/question
flow, templates, and the settings page itself — still exposes power-user controls that
overwhelm newcomers. We want a single, global **Simple mode** that lives in Settings and
simplifies the *whole* interface, so a beginner can move "goal → plan → done" without ever
meeting a knob they don't need. Power users turn it off once and get the full app back.

## What Changes

- Add a per-user, **server-persisted** `simple_mode` setting on `UserSettings` (default
  `true`), exposed through the existing `GET`/`PATCH /api/settings` endpoints alongside
  `memory_enabled`. The Orval client is regenerated and a `useSimpleMode()` hook becomes the
  single source of truth for the frontend.
- Add a **Simple mode** master toggle at the top of the Settings page.
- **Master switch over the board mode (BREAKING, UX):** the board interface mode is now driven
  by the global `simple_mode` setting instead of a per-board choice. When Simple mode is **on**,
  every board renders the stepper and the board's Simple/Advanced and Focus/Full switches are
  hidden. When **off**, boards render the DAG with the Focus/Full toggle and a per-session
  Simple/Advanced preview control (the existing `planflow:board-interface-mode` localStorage
  key is reused only while Simple mode is off, defaulting to Advanced). New/existing users with
  no setting default to Simple.
- **When Simple mode is on, hide advanced UI completely (no "Advanced" expanders):**
  - **Dashboard:** hide the "My Boards / Shared with Me" toggle (show only the user's own
    boards + New Board) and render simplified board cards (title + plain "% done", without the
    goal subtitle and progress bar).
  - **Templates:** keep the Templates tab for **creating boards from a template only** —
    selecting a template starts the create-board flow directly; the template detail editor,
    structure editing/saving, and the template authoring/generation flow are not reachable.
  - **Settings page:** show only the Simple mode and AI Memory toggles; hide memory statistics,
    search, category filter, the editable memory list, bulk clear, and pagination.
  - **Goal / question flow:** hide the readiness percentage indicator (replace with a plain
    "Ready to generate" state), render answered rounds as a read-only summary (no expand/Edit),
    and replace technical "Round N" labels with friendlier progress wording. Example-goal chips
    are kept (they help beginners).
  - **Board header:** hide "Save as Template", "Share", and "Memories" (and make their
    panels/sidebars unreachable from the board). Breadcrumb, title, and the stepper remain.
- Auth, navigation/breadcrumbs, board-generation progress, the celebration, and the stepper's
  own card are unchanged.

The only backend change is the new `simple_mode` column + migration; everything else is
frontend conditional rendering keyed off `useSimpleMode()`.

## Impact

- Affected specs:
  - `simple-mode` (NEW capability): setting persistence + API, master toggle, source-of-truth
    hook, and the per-screen simplification contract (dashboard, templates, settings, goal flow,
    board header).
  - `board-ui` (MODIFIED): **Interface Mode Selection** now governed by the global setting;
    **Board View Mode Toggle** scenario wording updated for Simple mode hiding both switches.
- Affected code:
  - `backend/app/domains/settings/{models,schemas,service,router}.py` + an Alembic migration.
  - `frontend/src/api/generated/**` (Orval regen).
  - `frontend/src/features/board/hooks/use-simple-mode.ts` (new), `use-interface-mode.ts`
    (gated on Simple mode off).
  - `frontend/src/features/settings/components/SettingsPage.tsx` (master toggle + simplified
    layout).
  - `frontend/src/routes/index.tsx`, `routes/boards.$boardId.tsx`,
    `features/goals/components/*`, `features/templates/components/*`, `features/board/components/*`.
- No change to task/status semantics, the DAG data model, or AI pipelines.
