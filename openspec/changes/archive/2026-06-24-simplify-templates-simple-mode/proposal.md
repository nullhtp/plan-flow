# Change: Simplify the Templates tab in Simple mode

## Why

In Simple mode the app aims for a guided, low-friction experience, yet the
Templates tab still shows advanced browsing chrome — a Public/My Templates
toggle, a keyword search, and a category filter — which adds noise for users who
just want to pick a ready-made public template. Other screens (dashboard,
settings, goal flow) already drop their advanced controls in Simple mode; the
Templates tab should match.

## What Changes

- In Simple mode, the Templates tab shows **only public templates**: the
  Public/My Templates toggle is hidden and the listing is forced to
  `visibility=public`.
- In Simple mode, the **keyword search input** and the **category filter** pills
  are hidden.
- The template grid (with direct create-board-from-template selection) and
  pagination remain in Simple mode.
- Advanced mode (Simple mode off) keeps the full browse experience unchanged:
  Public/My Templates toggle, search, and category filter.

## Impact

- Affected specs: `simple-mode` (ADD one requirement)
- Affected code:
  - `frontend/src/features/templates/components/TemplatesGallery.tsx`
  - `frontend/src/features/templates/__tests__/templates-gallery.test.tsx`
