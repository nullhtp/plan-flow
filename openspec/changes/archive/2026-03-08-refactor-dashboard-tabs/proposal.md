# Change: Refactor dashboard to tabbed layout with creation cards

## Why
Templates are currently hidden behind a header button that navigates to a separate `/templates` page, making them hard to discover. Board creation also lacks an obvious entry point -- the "New Goal" button in the header is the only way. Users need a more intuitive, discoverable layout where templates and board creation are front-and-center.

## What Changes
- Replace the dashboard header buttons ("New Goal", "Templates") with a tabbed layout using Shadcn Tabs (Radix-based)
- Dashboard gets two top-level tabs: **Boards** and **Templates**
- **Boards** tab has a secondary toggle ("My Boards" / "Shared with Me") mirroring the same pattern as the public/my toggle in Templates
- Add a "+" creation card as the first card in the **Boards** tab "My Boards" view (navigates to `/goals/new`)
- Add a "+" creation card as the first card in the **Templates** tab grid (navigates to `/templates/generate`)
- Remove the standalone `/templates` route (template detail `/templates/:id` and generation wizard `/templates/generate` remain)
- Simplify the header: PlanFlow logo on the left, user avatar/email dropdown on the right (containing Settings + Log out)
- Remove "New Goal" and "Templates" buttons from the header
- Move templates gallery content (public/my toggle, category filter, search, pagination) into the Templates tab

## Impact
- Affected specs: `board-ui`, `board-templates`
- Affected code:
  - `frontend/src/routes/index.tsx` (dashboard page -- major rewrite)
  - `frontend/src/routes/templates.tsx` (remove route, move content to dashboard)
  - `frontend/src/routes/router.ts` (remove `/templates` route)
  - `frontend/src/shared/components/` (new: user dropdown, creation card components)
  - `frontend/src/components/ui/` (add Shadcn Tabs component)
