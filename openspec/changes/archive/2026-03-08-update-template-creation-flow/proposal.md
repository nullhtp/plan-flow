# Change: Streamline "Save Board as Template" flow

## Why
The current "Save Board as Template" flow requires two steps: a modal dialog to set metadata (title, description, category, visibility) followed by optional navigation to the template detail page for structural editing. Since the template detail page already supports inline editing of title, description, and category, the modal is redundant. Removing it reduces friction — one click to create, then edit everything in one place.

## What Changes
- Remove the `SaveAsTemplateDialog` modal from the board detail page
- "Save as Template" button now creates the template immediately with defaults (board title, no description, no category, private visibility) and auto-navigates to the template detail page (`/templates/:id`)
- Add an inline visibility toggle to the template detail page header (for owners) so visibility can be changed there — previously only settable in the removed modal
- Remove the `SaveAsTemplateDialog` component entirely

## Impact
- Affected specs: `board-templates` (Save Board as Template Action, Template Detail Page)
- Affected code:
  - `frontend/src/routes/boards.$boardId.tsx` — replace dialog trigger with direct mutation + navigate
  - `frontend/src/features/templates/components/SaveAsTemplateDialog.tsx` — remove entirely
  - `frontend/src/routes/templates.$templateId.tsx` — add visibility toggle in header metadata row
