## 1. Implementation

- [x] 1.1 In `TemplatesGallery.tsx`, gate the Public/My Templates toggle, the
  search input, and the `CategoryFilter` block behind `!isSimpleMode` so they are
  not rendered in Simple mode.
- [x] 1.2 Compute the `useTemplates` params from `isSimpleMode`: in Simple mode
  pass `visibility="public"` and omit `category`/`search` (ignore those state
  values), keeping the hook call unconditional to respect the rules of hooks.
- [x] 1.3 Ensure the empty-state message uses the public-templates copy in Simple
  mode (the "My Templates" empty path is unreachable there).

## 2. Tests & validation

- [x] 2.1 Extend `templates-gallery.test.tsx`: with Simple mode enabled, assert
  the toggle, search input, and category filter are not rendered and that the
  list request loads only public templates.
- [x] 2.2 Add/keep coverage that with Simple mode disabled the toggle, search
  input, and category filter are all rendered.
- [x] 2.3 Run frontend typecheck, Biome lint, and the templates Vitest suite;
  resolve any failures.
