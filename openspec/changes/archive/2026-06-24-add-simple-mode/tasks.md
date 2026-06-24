## 1. Backend: `simple_mode` setting

- [x] 1.1 Add `simple_mode: bool` (server default `true`, non-null) to `UserSettings` in `backend/app/domains/settings/models.py`
- [x] 1.2 Add `simple_mode` to `UserSettingsResponse` and `UserSettingsUpdateRequest` in `schemas.py`
- [x] 1.3 Handle `simple_mode` in `update_user_settings` (and the GET mapping) in `service.py` / `router.py`
- [x] 1.4 Create an Alembic migration adding the column with `server_default="true"`, backfilling existing rows (`e5f6a7b8c9d0_add_simple_mode_setting.py`)
- [x] 1.5 Add/extend backend tests for GET/PATCH of `simple_mode` (default true, update, persistence, independence from `memory_enabled`)

## 2. Frontend: source of truth

- [x] 2.1 Regenerate the Orval client so `simple_mode` is available on the settings hooks (`make codegen`)
- [x] 2.2 Add `useSimpleMode()` exposing `isSimpleMode` (defaults to `true` while loading). Placed in `shared/hooks/use-simple-mode.ts` (not `features/board/hooks`) because it is consumed across features — features may not import each other, only `shared/`.
- [x] 2.3 Unit test `useSimpleMode` (loading → true, resolved false → false, resolved true → true)

## 3. Settings page

- [x] 3.1 Add the **Simple mode** master toggle card at the top of `SettingsPage.tsx` (optimistic cache write, failure rollback toast)
- [x] 3.2 In Simple mode, render only the Simple mode + AI Memory toggles; hide statistics, search, category filter, memory list, bulk clear, and pagination
- [x] 3.3 Tests: master toggle patches the setting + simplified-vs-full settings layout (`settings-page.test.tsx`)

## 4. Board: master switch + header

- [x] 4.1 Derive board interface mode from `useSimpleMode()`; force the stepper and hide the Simple/Advanced + Focus/Full switches when Simple mode is on (default to stepper while settings load)
- [x] 4.2 When Simple mode is off, render the DAG by default with Focus/Full and the per-session Simple/Advanced control (reusing `use-interface-mode`, now defaulting to Advanced)
- [x] 4.3 Hide "Save as Template", "Share" (+ `SharePanel`), and "Memories" (+ `BoardMemorySidebar`) in the header while Simple mode is on; gate the stepper's "View full DAG" CTA on Simple mode being off
- [x] 4.4 Tests: `use-interface-mode` default flipped to Advanced; `use-simple-mode` and `stepper-view` cover the composed logic (route wiring covered by type-check)

## 5. Dashboard

- [x] 5.1 Hide the "My Boards / Shared with Me" toggle and render only owned boards + New Board when Simple mode is on (`routes/index.tsx`)
- [x] 5.2 Add a simplified `BoardCard` variant (title + plain "% done", no goal subtitle, no progress bar) used in Simple mode
- [x] 5.3 Tests: `board-card.test.tsx` covers the simplified vs full card variant

## 6. Templates (creation-only in Simple mode)

- [x] 6.1 In Simple mode, selecting a template starts the create-board-from-template flow directly (no editor) — `TemplateCard.onSelect` + `UseTemplateDialog` in the gallery
- [x] 6.2 Guard the template detail editor and template generation routes (redirect to the gallery) and hide the "Create Template" entry point in Simple mode
- [x] 6.3 Tests: `templates-gallery.test.tsx` — use-template-to-create in Simple mode; authoring + editor navigation only when off

## 7. Goal / question flow

- [x] 7.1 Hide `ReadinessIndicator` + readiness summary; show a plain "Ready to generate" state on the generate footer in Simple mode
- [x] 7.2 Render answered rounds as a read-only summary (no expand/Edit) and use friendlier progress labels in Simple mode (kept example chips)
- [x] 7.3 Tests: `dynamic-question-form.test.tsx` — readiness hidden, rounds read-only, friendly labels in Simple mode; full flow when off

## 8. Validation

- [x] 8.1 Frontend type-check + Biome clean on all changed files; backend Ruff clean and Pyright introduces no new errors (2 pre-existing repository.py errors remain)
- [x] 8.2 Frontend suite green (128 tests, 22 files); backend settings suite green (5 tests); Alembic chain verified single-head (`e5f6a7b8c9d0`)
- [x] 8.3 Run `openspec validate add-simple-mode --strict --no-interactive`
