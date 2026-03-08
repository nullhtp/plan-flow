## 1. UI Component Setup
- [x] 1.1 Add Shadcn Tabs component (`npx shadcn@latest add tabs`) to `frontend/src/components/ui/`
- [x] 1.2 Add Shadcn DropdownMenu component (`npx shadcn@latest add dropdown-menu`) if not already present
- [x] 1.3 Create `CreationCard` component in `frontend/src/shared/components/creation-card.tsx` -- dashed border card with "+" icon and configurable label, matching sibling card dimensions

## 2. Header Refactor
- [x] 2.1 Create `UserDropdown` component in `frontend/src/shared/components/user-dropdown.tsx` -- user email trigger, dropdown with Settings + Log out items
- [x] 2.2 Update dashboard header in `frontend/src/routes/index.tsx` to use simplified layout: PlanFlow logo + UserDropdown (remove New Goal, Templates, Settings, Log out buttons)

## 3. Dashboard Tabbed Layout
- [x] 3.1 Refactor `frontend/src/routes/index.tsx` to use Shadcn Tabs with two top-level tabs: "Boards" and "Templates"
- [x] 3.2 Add `tab` search parameter to the route definition for URL persistence (TanStack Router search params validation)
- [x] 3.3 Implement "Boards" tab with secondary toggle ("My Boards" / "Shared with Me") using same button-toggle pattern as templates public/my toggle
- [x] 3.4 Implement "My Boards" secondary view: CreationCard (-> `/goals/new`) as first grid item, followed by BoardCard grid (existing `useBoardList` hook)
- [x] 3.5 Implement "Shared with Me" secondary view: BoardCard grid using `useBoardList(true)` with empty state message, no creation card
- [x] 3.6 Extract templates gallery content from `frontend/src/routes/templates.tsx` into a reusable component (e.g., `frontend/src/features/templates/components/TemplatesGallery.tsx`)
- [x] 3.7 Implement "Templates" tab content: embed TemplatesGallery with CreationCard (-> `/templates/generate`) as first grid item, public/my toggle, category filter, search, pagination

## 4. Route Cleanup
- [x] 4.1 Remove `frontend/src/routes/templates.tsx` route file
- [x] 4.2 Update `frontend/src/routes/router.ts` to remove the `/templates` route from the route tree (keep `/templates/generate` and `/templates/$templateId`)
- [x] 4.3 Update any internal links pointing to `/templates` to use `/?tab=templates` instead (e.g., "Back to Templates" links in template detail/generate pages)

## 5. Verification
- [x] 5.1 Verify both tabs render correctly with proper content and secondary toggles work
- [x] 5.2 Verify tab URL persistence works (direct navigation to `/?tab=templates`)
- [x] 5.3 Verify CreationCard navigation works in both tabs
- [x] 5.4 Verify template gallery functionality works within the tab (search, filter, pagination, public/my toggle)
- [x] 5.5 Verify header dropdown works (Settings navigation, Log out)
- [x] 5.6 Run `pnpm biome check` and fix any lint/format issues
- [x] 5.7 Run `pnpm tsc --noEmit` and fix any type errors
