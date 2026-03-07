# Change: Add Shared Access to Boards

## Why
PlanFlow boards are currently single-user only — the owner is the only person who can view or interact with them. Users need the ability to share boards with collaborators (friends, teammates, coaches) so others can contribute to task execution without needing to own the goal.

## What Changes
- New `board_share` table storing share links (token, board_id, created_by) and `board_member` table storing per-user access grants (board_id, user_id, role)
- New endpoints for share-link management: create/regenerate link, get link, delete link
- New endpoints for member management: list members, revoke member access
- New join-via-token endpoint: authenticated user redeems a share token to become a member
- Ownership validation (`ownership.py`) broadened to accept collaborators — owner retains full control including board deletion; collaborators can edit tasks, subtasks, artifacts, and use AI chat but cannot delete the board or manage sharing
- Sub-board access inherits from root board — no separate share links for sub-boards
- Frontend share dialog on the board page to copy/manage share link and view/revoke members
- **BREAKING**: Ownership checks change from "owner-only" to "owner-or-collaborator" for most board/task/subtask/artifact endpoints

## Impact
- Affected specs: `board-management` (new models, endpoints, modified ownership)
- Affected code:
  - `backend/app/domains/boards/models.py` — new BoardShare, BoardMember models
  - `backend/app/domains/boards/ownership.py` — access validation broadened
  - `backend/app/domains/boards/router.py` — new share/member endpoints
  - `backend/app/domains/boards/board_service.py` — share/member business logic
  - `backend/migrations/` — new Alembic migration
  - `frontend/src/features/board/components/` — share dialog UI
  - `frontend/src/features/board/hooks/` — share/member hooks
