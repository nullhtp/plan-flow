## Context
PlanFlow is a single-user app where board access is enforced via ownership chain: board → goal → user. Adding shared access requires a new access layer that sits alongside ownership without replacing it. The owner remains the sole person who can delete the board or manage sharing; collaborators get full edit access to tasks and subtasks.

## Goals / Non-Goals
- **Goals:**
  - Share link flow: owner generates a token-based URL, anyone with the link + a PlanFlow account can join
  - Full collaborator role: collaborators can create/edit/delete tasks, toggle subtasks, use AI chat
  - Member management: owner can see who has access and revoke individually
  - Sub-board inheritance: access to root board implies access to all sub-boards
- **Non-Goals:**
  - Multiple permission tiers (viewer, editor) — single "collaborator" role for now
  - Anonymous/unauthenticated access — account required
  - Notifications or activity feed for shared boards
  - Transfer of board ownership

## Decisions

### Share Link Model
- **Decision**: One `board_share` record per root board, containing a unique URL-safe token (32 chars, `secrets.token_urlsafe`). Creating a new link for a board that already has one regenerates the token (invalidating the old link).
- **Alternatives**: Per-invite tokens (more granular revocation) — rejected for simplicity; a single link per board is sufficient for MVP.

### Member Model
- **Decision**: `board_member` table with `board_id`, `user_id`, `role` (default "collaborator"), and `joined_at`. When a user redeems a share token, a member record is created. The owner is NOT stored as a member — ownership is still determined via goal.user_id.
- **Alternatives**: Storing the owner as a member with role "owner" — rejected because it duplicates the existing goal→user ownership and creates sync issues.

### Ownership Validation Changes
- **Decision**: Modify `ownership.py` validation functions to accept both the goal owner AND any board member. The functions gain an optional `require_owner=False` parameter. When `require_owner=True`, only the goal owner passes (used for board deletion and share management). Otherwise, both owner and collaborators pass.
- **Alternatives**: Separate middleware for access checks — rejected; the existing ownership pattern is clean and well-understood.

### Sub-Board Access Inheritance
- **Decision**: When validating access to a sub-board, trace up to the root board and check membership there. No separate member records for sub-boards.
- **Alternatives**: Copying member records to sub-boards — rejected; adds complexity and sync issues.

### Board List Endpoint
- **Decision**: `GET /api/boards` returns boards the user owns. A new query parameter `?shared=true` returns boards where the user is a collaborator. The response includes a `role` field ("owner" or "collaborator") so the frontend can show appropriate UI.
- **Alternatives**: Merging owned and shared boards into one list — possible future enhancement but cleaner to separate for now.

## Risks / Trade-offs
- **Token guessability** → Mitigated by 32-char `secrets.token_urlsafe` (256 bits of entropy)
- **Orphaned members** → When a board is deleted, cascade delete removes all member and share records
- **Performance** → Member lookup adds one extra DB query per request; acceptable at current scale. Can add caching later if needed.

## Open Questions
- None — all key decisions resolved via user input.
