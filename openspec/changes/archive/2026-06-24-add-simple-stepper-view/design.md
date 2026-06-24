## Context

The board UI (`board-ui` spec) renders a React Flow DAG with an existing two-mode toggle
(**Focus** / **Full**) persisted in the `?view` URL param, defaulting to Focus
(`frontend/src/routes/boards.$boardId.tsx:50`). The `TaskDetailPanel` already bundles the
complete single-task experience (status, description, metadata, subtasks, AI actions,
artifacts, chat). All structural data needed to order tasks — `dependency_ids`,
`dependent_ids`, `is_locked`, `status`, `is_goal_node` — is present in `BoardResponse`
client-side.

We are adding a **Simple** stepper interface that becomes the default, while keeping the
DAG as **Advanced**. The decisions below were confirmed with the requester.

## Goals / Non-Goals

- Goals:
  - A guided, one-task-per-screen stepper that defaults on, with no learning curve.
  - Switch freely between Simple and Advanced; remember the choice.
  - Reuse the existing full task-detail experience — nothing is lost vs the DAG panel.
  - Zero backend changes.
- Non-Goals:
  - No new "next task" computation on the backend; ordering is client-side.
  - No change to the DAG's internal Focus/Full behavior or to task/status semantics.
  - No manual reordering or skipping of locked tasks (dependencies remain AI-only).

## Decisions

### 1. Single linear sequence over all tasks (parallel branches serialized)

The stepper walks **every task** as one ordered sequence:

```
sequence = topologicalOrder(tasks, edges)   // all tasks, no filtering
```

A topological sort (Kahn's algorithm on `edges`, ready nodes tie-broken by `created_at`)
flattens the DAG's parallel branches into a single line where each prerequisite precedes its
dependents. The stepper therefore never shows parallel paths — independent tasks simply
become consecutive steps. Done, in-progress, not-started, and locked tasks all appear, so the
user can walk the whole plan start to finish. The **goal node** depends on all leaf tasks, so
it is always last.

Entry lands on the first `in_progress` task if any, else the first task that is not `done`
(where the user resumes), else the first task. The sequence is **derived** (recomputed from
board data each render), not stored; the *current task id* is held in component state.

Progression is **gated**: the **Next** control is enabled only when the current step's task is
`done`, so the user must complete each task before advancing (a "complete this task to
continue" hint shows while it is gated). **Previous** stays available so completed steps can
be revisited — and on a revisited done step, Next is enabled again to return forward. When the
user marks the current task `done`, the stepper auto-advances to the next step (the completed
task stays in the sequence as a done step). If the current task is **deleted**, it leaves the
sequence and the stepper clamps to the task now occupying its slot.

Locked steps are read-only: `TaskDetailContent` already disables the status control for a
locked task and explains which prerequisites are pending — so a user who jumps ahead sees the
task but cannot complete it out of order.

Alternatives considered: (a) walk only the *actionable* frontier (unlocked, not-done) — this
was the first cut, but it hid parallel/future work the user wanted to see, so it was replaced
by the full sequence at the requester's direction; (b) a depth-first linearization that keeps
each branch contiguous — deferred; Kahn + `created_at` interleaves branches roughly in
creation order, which is acceptable and simpler. Either way the full DAG remains in Advanced.

### 2. Persistence: saved global preference (localStorage)

Interface mode is stored under a single localStorage key
(`planflow:board-interface-mode` = `"simple" | "advanced"`), read via a `useInterfaceMode`
hook. It is **global** (applies to every board) and survives sessions. With no stored value
(new users) the default is `"simple"`. The app is a client-side SPA (no SSR), so reading
localStorage on first render is safe.

We deliberately do **not** put mode in the URL: the requester chose a single "how I like to
work" preference over per-board/per-link state. The existing `?view` (Focus/Full) and
`?task` params keep working **inside Advanced mode**, so DAG deep links are unchanged.

### 3. Two-level switch (Simple ⇄ Advanced; Focus/Full nested)

The header gets a top-level **Simple / Advanced** segmented control. The existing
**Focus / Full DAG** toggle renders **only when Advanced is active** and continues to drive
`?view`. This keeps a clean beginner-vs-power split and leaves the Focus/Full logic intact.

### 4. Step screen: a deliberately minimal card

Simple mode does **not** reuse the full task-detail content. Each step is a dedicated
`StepCard` showing only: read-only title, read-only description, a subtask checklist
(completion toggle only — no add/delete/rename, reusing `use-subtask-mutations`' update
only), the task AI chat (`TaskChat`), and **status buttons**. The status buttons drive the
lifecycle explicitly — Start (`not_started`→`in_progress`), Mark as done
(`in_progress`→`done`), Reset (→`not_started`), Reopen (`done`→`in_progress`) — and a locked
task shows a disabled locked indicator instead. Marking a task done advances the stepper.
As a shortcut, checking the **final remaining subtask** of an `in_progress` task auto-marks the
task `done` and advances (handled in `StepperView`'s subtask-toggle handler, gated on
`in_progress` so it never sends an invalid `not_started`→`done` transition).
Metadata, artifacts, expand-to-board, editable title/description inputs, and the delete
control are intentionally omitted to keep Simple mode focused; all of them remain in the
Advanced task-detail panel.

`TaskDetailContent` (extracted earlier from `TaskDetailPanel`) is therefore used only by the
Advanced panel now. It is kept as-is — it still keeps the panel file tidy and is the home for
the full editing experience.

### 5. Edge cases

- **Sub-board task as current step**: the step shows an "Open Sub-Board" CTA navigating to
  `/boards/:subBoardId` (matching panel behavior). The sub-board opens in Simple mode too,
  since the preference is global.
- **Board completion**: when the board is complete (every task `done`), the stepper shows a
  completion screen and triggers the existing `Celebration` instead of a step. The screen
  links back to the dashboard and offers "View full DAG" (Advanced).
- **Deep link** (`?task=<id>`): the task is always in the sequence, so the stepper simply
  opens with it as the current step — no mode switch. (The Advanced-only Focus→Full
  auto-switch for hidden tasks is unchanged.)
- **Empty board** (no tasks): show a graceful "No tasks yet — open the full DAG" fallback
  rather than a blank screen.

## Risks / Trade-offs

- Changing the default away from the DAG is a UX shift → mitigated by a prominent, always
  visible Simple/Advanced switch and a remembered preference.
- Long boards make a single sequence long to scroll through → mitigated by a stable
  "Step X of N" with a fixed N (total tasks) plus an overall completion bar (done / total),
  and by Advanced mode remaining one click away for users who want the whole graph at once.
- Extracting `TaskDetailContent` touches a central component → mitigated by keeping the
  panel's outward behavior identical and covering it with existing/added component tests.

## Migration Plan

Pure additive frontend change. On first load after release, every user (no stored
preference) lands in Simple; one click switches to Advanced and is remembered. No data
migration. Rollback = revert the frontend change; no persisted server state is affected.

## Open Questions

- None blocking. Optional future enhancement: a one-time tooltip introducing the
  Simple/Advanced switch for existing users.
