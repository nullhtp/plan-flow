## Context

PlanFlow persists per-user settings server-side: `UserSettings` already holds `memory_enabled`
and is read/written via `GET`/`PATCH /api/settings` (Orval-generated hooks). Separately, the
board added a per-board **Simple/Advanced** interface toggle stored only in localStorage
(`planflow:board-interface-mode`, `useInterfaceMode`), defaulting to the Simple stepper
(`board-ui` spec: *Interface Mode Selection*, *Board View Mode Toggle*).

This change introduces a single, global **Simple mode** that simplifies every screen. The four
foundational decisions below were confirmed with the requester:

1. **Master switch** — the global Simple mode is the single source of truth; it overrides the
   per-board toggle.
2. **Server-side** — `simple_mode` joins `memory_enabled` on `UserSettings` (syncs across
   devices, consistent with how settings already work).
3. **Default on** — users with no stored setting start in Simple.
4. **Hide completely** — advanced controls simply don't render in Simple mode; there are no
   per-screen "Advanced" expanders. Turning the mode off in Settings restores everything.

The per-screen simplification scope was also approved item-by-item (see proposal).

## Goals / Non-Goals

- Goals:
  - One global, server-persisted toggle that drives a simplified UI across all screens.
  - A single frontend source of truth (`useSimpleMode`) so every screen reads the same value.
  - Keep beginners on one path; keep the full app one toggle away for power users.
  - Minimal backend surface (one boolean column + migration).
- Non-Goals:
  - No change to task/status semantics, DAG data, sub-boards, or AI pipelines.
  - No new per-screen "advanced" disclosure UI (explicitly rejected: hide completely).
  - No removal of the per-board localStorage toggle — it is retained as an in-session preview
    used only while global Simple mode is **off**.

## Decisions

### 1. `simple_mode` on `UserSettings` (server, default `true`)

Add `simple_mode: bool` (server default `true`, not null) to `UserSettings`, surface it in
`UserSettingsResponse` and `UserSettingsUpdateRequest`, set it in the service `update`, and add
an Alembic migration. Regenerating the Orval client exposes it through the existing
`useGetSettingsApiSettingsGet` / `usePatchSettingsApiSettingsPatch` hooks — no new endpoint.

Alternatives considered: localStorage only (rejected — it isn't really "part of settings" and
doesn't follow the user across devices).

### 2. `useSimpleMode()` is the single source of truth

A small hook reads `settingsQuery.data.simple_mode` and returns `isSimpleMode`. **While the
settings query is loading it defaults to `true`** so the app never flashes the advanced UI (and
the board never flashes the DAG) before the setting resolves. Every screen derives its
simplified/full rendering from this one boolean via `{!isSimpleMode && <Advanced/>}` or
`{isSimpleMode ? <Simple/> : <Full/>}`.

### 3. Master switch over the board (supersedes the per-board toggle)

`board-ui`'s *Interface Mode Selection* is modified so the board mode is **derived from the
global setting**, not chosen per board:

- `simple_mode === true`: every board renders the stepper; the header shows **no** Simple/
  Advanced switch and **no** Focus/Full toggle. To leave Simple, the user opens Settings.
- `simple_mode === false`: boards render the DAG (Advanced) with the Focus/Full toggle, plus a
  per-session **Simple/Advanced** preview control that lets a power user open the stepper for a
  board without changing their global setting. This control reuses the existing
  `planflow:board-interface-mode` localStorage key, is rendered **only** while Simple mode is
  off, and defaults to **Advanced**.

This matches the approved "master switch": ON hides the per-board toggle; OFF reveals the full
UI including the DAG and its toggles. The `useInterfaceMode` hook is kept but consulted only
when `simple_mode === false`.

Alternative considered: deleting the localStorage toggle entirely (the requester chose to keep
it as an off-mode preview instead).

### 4. Per-screen simplification (hide completely)

All conditional behavior is keyed off `useSimpleMode()`:

- **Dashboard** (`routes/index.tsx`): hide the My/Shared `view` toggle (render only owned
  boards + `CreationCard`); `BoardCard` renders a simplified variant (title + plain "% done",
  no goal subtitle, no progress bar). Templates tab stays.
- **Templates**: the gallery stays browsable; selecting a template routes straight into the
  existing create-board-from-template flow. The template **detail editor**, structure
  editing/saving, `TemplateTaskDetailPanel` editing, and the **template generation** route/entry
  points are not reachable in Simple mode (guarded at the route/CTA level).
- **Settings** (`SettingsPage.tsx`): in Simple mode render only the Simple mode + AI Memory
  toggle cards; omit statistics, search, category filter, the memory list, bulk clear, and
  pagination.
- **Goal flow** (`features/goals/components/*`): hide `ReadinessIndicator` (and the readiness
  summary text) — show a plain "Ready to generate" state on the generate footer once allowed;
  render completed rounds read-only (no expand/Edit); replace "Round N" wording. Example chips
  kept.
- **Board header** (`routes/boards.$boardId.tsx`): hide Save as Template, Share (and
  `SharePanel`), and Memories (and `BoardMemorySidebar`). Title editing, breadcrumb, and the
  stepper remain.

## Risks / Trade-offs

- Changing the board mode from a per-board toggle to a global setting is a behavior shift →
  mitigated by keeping the localStorage preview when Simple mode is off and by a single,
  obvious master toggle in Settings.
- Hiding (not collapsing) advanced controls means discoverability depends on Settings →
  accepted per the "hide completely" decision; the toggle is prominent and remembered.
- The settings query gating board render could cause a brief stepper-first paint on slow
  networks → acceptable; Simple is the default and the correct mode for most users.

## Migration Plan

- Backend: additive column with server default `true`; the Alembic migration backfills existing
  rows to `true`. No data loss; rollback drops the column.
- Frontend: additive conditional rendering. On first load after release, every user resolves to
  Simple (their stored value or the default); one toggle in Settings restores the full UI.

## Open Questions

- None blocking. Optional future enhancement: a one-time tooltip pointing existing power users
  to the new Simple mode toggle in Settings.
