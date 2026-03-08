## 1. Frontend: Remove SaveAsTemplateDialog and streamline board page
- [x] 1.1 In `boards.$boardId.tsx`: replace `SaveAsTemplateDialog` usage with a direct `useCreateTemplate` mutation call that creates the template with defaults (board title, private, no description, no category) and navigates to `/templates/$templateId` on success
- [x] 1.2 Remove the `showSaveAsTemplate` state variable and `SaveAsTemplateDialog` component render from `boards.$boardId.tsx`
- [x] 1.3 Remove the `SaveAsTemplateDialog` import from `boards.$boardId.tsx`
- [x] 1.4 Delete `frontend/src/features/templates/components/SaveAsTemplateDialog.tsx`

## 2. Frontend: Add visibility toggle to template detail page
- [x] 2.1 In `templates.$templateId.tsx`: replace the read-only visibility `<span>` (line 281) with an interactive `<select>` dropdown (private/public) for owners, keeping the read-only span for non-owners
- [x] 2.2 Wire the visibility select to call `handleMetadataSave("visibility", value)` on change (same pattern as the existing category dropdown)

## 3. Cleanup
- [x] 3.1 Remove any test files specific to `SaveAsTemplateDialog` if they exist
- [x] 3.2 Verify the template detail page loads correctly after navigation from board page (manual test)
