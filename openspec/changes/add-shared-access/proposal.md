# Change: Add Shared Access to Board Execution

## Why
PlanFlow is currently single-user only. Users want to invite collaborators to participate in board execution — sharing progress, editing tasks, and using AI features together. Link-based sharing at the goal level provides a simple, low-friction way to onboard collaborators without requiring email infrastructure.

## What Changes
- New `goal_share` data model: stores share links with role (`viewer` / `editor`) and token-based access
- New `goal_member` data model: tracks users who have accepted a share link
- New share management endpoints: create/list/revoke share links, list/remove members
- New share link acceptance endpoint: join a goal via token
- **MODIFIED** ownership validation: all `validate_*_ownership` functions now also grant access to goal members (not just the goal owner)
- **MODIFIED** board list endpoint: shared boards appear alongside owned boards
- **MODIFIED** goal get endpoint: shared goals accessible to members
- Frontend share dialog UI for managing links and members
- Frontend share link acceptance page

## Impact
- Affected specs: `board-management` (ownership checks, board listing), `goal-management` (goal access), new `shared-access` capability
- Affected code: `app/domains/boards/ownership.py` (core change), new `app/domains/sharing/` domain, board/goal routers and services, frontend share components
- Security: share tokens must be cryptographically random, roles enforced server-side, owner-only management operations
