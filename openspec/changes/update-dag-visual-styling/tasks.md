## 1. Node Styling Overhaul

- [x] 1.1 Update `TaskNode.tsx`: increase border radius to 20-24px (`rounded-2xl` or `rounded-3xl`), replace `shadow-sm` with a larger soft shadow (`shadow-md` or custom), add `transition-all duration-300 ease-in-out` for smooth status changes
- [x] 1.2 Update `TaskNode.tsx` priority color palette: replace harsh red/yellow/blue with muted pastel tones (e.g., `border-rose-400 bg-rose-50`, `border-amber-400 bg-amber-50`, `border-sky-400 bg-sky-50` and dark mode equivalents)
- [x] 1.3 Update `TaskNode.tsx` completed state: add subtle green-tinted background (`bg-green-50 dark:bg-green-950/20`) alongside the green border
- [x] 1.4 Update `TaskNode.tsx` locked state: replace `opacity-50 grayscale` with `opacity-60` only (keep priority colors, drop grayscale filter)
- [x] 1.5 Update `TaskNode.tsx` typography: refine font sizes, weights, and spacing for title and metadata row
- [x] 1.6 Hide connection handles in `TaskNode.tsx`: remove `<Handle>` components or set `!opacity-0 !w-0 !h-0` styles (handles are required by React Flow internally but can be hidden)

## 2. Goal Node Refinement

- [x] 2.1 Update `GoalNode.tsx`: match the rounded corner increase (`rounded-2xl` or `rounded-3xl`)
- [x] 2.2 Hide the target handle on `GoalNode.tsx` (same approach as task nodes)
- [x] 2.3 Add `transition-all duration-300 ease-in-out` to goal node for smooth state changes

## 3. Edge Styling

- [x] 3.1 Update `dagre-layout.ts`: change edge `type` from `"default"` to `"smoothstep"` or `"bezier"` for curved connections
- [x] 3.2 Update edge styling: unlocked edges get thicker stroke (3px) with indigo color; locked edges get thinner stroke (1.5px) with muted gray
- [x] 3.3 Update arrowhead markers to match the new thickness/color scheme

## 4. Graph Canvas & DagView Config

- [x] 4.1 Update `DagView.tsx`: change `<Background />` to `<Background variant="none" />` or remove it for a clean canvas (use plain CSS background color instead)
- [x] 4.2 Style the `<MiniMap>` component: set background color, node color, and mask color to match the visual theme
- [x] 4.3 Add `cursor-pointer` class to selectable nodes via React Flow's `className` or node wrapper styling

## 5. Verification

- [x] 5.1 Visual QA: open a board with mixed task states (done, in_progress, not_started, locked) and verify all styling changes render correctly in both light and dark mode
- [x] 5.2 Run frontend build (`pnpm build`) to confirm no regressions
- [x] 5.3 Run frontend tests (`pnpm test`) to confirm no regressions
