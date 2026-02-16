# Change: Polish DAG graph visual styling

## Why
The current DAG graph looks like a default React Flow example with plain boxy nodes, flat colors, basic straight edges, and generic styling. It needs a clean, minimal, product-quality visual polish to feel like a polished SaaS app rather than a prototype.

## What Changes
- **Node styling**: Very rounded corners (20-24px), refined soft shadows, better typography (sizes, weights, spacing), muted/pastel priority color palette (rose, amber, sky instead of harsh red/yellow/blue)
- **Edge styling**: Replace default straight edges with smooth bezier curves. Use color + thickness differentiation for locked vs unlocked edges (thicker colored for unlocked, thinner gray for locked). No animation.
- **Completed tasks**: Enhanced green treatment with subtle green glow/gradient instead of just a green border
- **Locked tasks**: Muted but keep color tinting (reduce opacity slightly, no full grayscale)
- **Background**: Remove dot grid, use clean plain canvas
- **Connection handles**: Hidden since nodes are not user-connectable
- **Minimap**: Styled to match the overall visual theme
- **Transitions**: Smooth CSS transitions on status changes (color morphs, opacity changes)
- **No hover effects beyond cursor pointer** (keep it simple)
- **No edge animation** (static but well-styled bezier curves)
- **Keep current layout spacing** (nodesep: 40, ranksep: 60)

## Impact
- Affected specs: `board-ui`
- Affected code:
  - `frontend/src/features/board/components/TaskNode.tsx` — node styling overhaul
  - `frontend/src/features/board/components/GoalNode.tsx` — minor style refinement
  - `frontend/src/features/board/components/DagView.tsx` — background, minimap, handle visibility config
  - `frontend/src/features/board/utils/dagre-layout.ts` — edge type changed to bezier, edge styling updates
