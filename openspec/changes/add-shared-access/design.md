## Context
PlanFlow boards are currently single-user. Adding shared access requires a new domain (`sharing`), modifications to the ownership validation layer, and frontend UI for managing share links and members. Sharing is scoped at the goal level — a shared goal grants access to its board and all sub-boards.

## Goals / Non-Goals
- Goals:
  - Link-based sharing (no email infrastructure needed)
  - Two roles: `viewer` (read-only) and `editor` (full task/AI interaction)
  - Per-goal scope with sub-board inheritance
  - Owner retains exclusive control over sharing management
- Non-Goals:
  - Email invitations (future enhancement)
  - Real-time collaboration / presence indicators
  - Per-board or per-task granular permissions
  - Transfer of ownership

## Decisions

### 1. New `sharing` domain
- **Decision**: Create `app/domains/sharing/` with its own models, schemas, repository, service, router
- **Why**: Follows the existing domain-based architecture. Sharing is orthogonal to boards/goals and deserves its own domain
- **Alternative**: Add to `boards` domain — rejected because sharing is goal-scoped, not board-scoped

### 2. Share link model (`goal_share`)
- **Decision**: `goal_share` table with `id`, `goal_id` (FK), `token` (unique, 32-byte hex), `role` (viewer/editor), `created_by` (FK to user), `is_active` (boolean), `created_at`, `expires_at` (nullable)
- **Why**: Supports multiple simultaneous share links with different roles, revocable independently
- **Alternative**: Single share link per goal — too limiting for different permission levels

### 3. Membership model (`goal_member`)
- **Decision**: `goal_member` table with `id`, `goal_id` (FK), `user_id` (FK), `role` (viewer/editor), `joined_via` (FK to goal_share), `created_at`. Unique constraint on `(goal_id, user_id)`.
- **Why**: Records which users have accepted which share links. Role is copied from the share link at acceptance time.
- **Alternative**: Check share links at every request — slower, can't revoke individual members without revoking the link

### 4. Ownership validation modification
- **Decision**: Modify `_resolve_goal_for_board` chain to also check `goal_member` table. Add a `required_role` parameter (default: `viewer`). Write endpoints pass `required_role="editor"`.
- **Why**: Centralizes access control in the existing ownership module. Minimal code changes across all existing endpoints.
- **Alternative**: Separate middleware — more complex, duplicates the goal-resolution logic

### 5. Owner retains goal.user_id
- **Decision**: The original creator remains `goal.user_id`. Members are tracked separately in `goal_member`. Only the owner can manage shares.
- **Why**: Simple, backward-compatible. No migration of existing data needed.

## Risks / Trade-offs
- **Risk**: Performance of ownership checks (extra DB query for `goal_member`) → Mitigation: index on `(goal_id, user_id)`, single query with `EXISTS`
- **Risk**: Editor role allows AI usage which costs money → Mitigation: acceptable per user's decision; can add rate limiting later
- **Risk**: Share link token exposure → Mitigation: 32-byte cryptographically random tokens, HTTPS only

## Migration Plan
1. Add `goal_share` and `goal_member` tables (non-destructive)
2. Modify ownership validation (backward-compatible — existing users still pass as owner)
3. Add sharing endpoints and frontend UI
4. No data migration needed — existing goals have no shares

## Open Questions
- Should expired share links auto-cleanup via a background job, or just be filtered at query time?
- Should there be a maximum number of members per goal?
