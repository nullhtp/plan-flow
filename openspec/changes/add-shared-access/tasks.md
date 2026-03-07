## 1. Database & Models
- [ ] 1.1 Create `GoalShare` SQLModel in `app/domains/sharing/models.py`
- [ ] 1.2 Create `GoalMember` SQLModel in `app/domains/sharing/models.py`
- [ ] 1.3 Create Alembic migration for `goal_share` and `goal_member` tables
- [ ] 1.4 Verify migration runs cleanly (upgrade + downgrade)

## 2. Sharing Domain Backend
- [ ] 2.1 Create `app/domains/sharing/schemas.py` (request/response Pydantic models)
- [ ] 2.2 Create `app/domains/sharing/repository.py` (GoalShareRepository, GoalMemberRepository)
- [ ] 2.3 Create `app/domains/sharing/service.py` (share link CRUD, member CRUD, token generation, accept logic)
- [ ] 2.4 Create `app/domains/sharing/router.py` (share management + accept endpoints)
- [ ] 2.5 Mount sharing router in `app/main.py`

## 3. Ownership Validation Modification
- [ ] 3.1 Modify `_resolve_goal_for_board` in `ownership.py` to return `(goal, role)` tuple
- [ ] 3.2 Add `validate_goal_access` function that checks owner OR member
- [ ] 3.3 Update `validate_board_ownership` to accept members (with role check)
- [ ] 3.4 Update `validate_task_ownership` to accept members (with role check)
- [ ] 3.5 Update `validate_subtask_ownership` to accept members (with role check)
- [ ] 3.6 Update `validate_artifact_ownership` to accept members (with role check)
- [ ] 3.7 Add `required_role` parameter to write-operation validations

## 4. Board & Goal Endpoint Modifications
- [ ] 4.1 Update `GET /api/boards` to include shared boards with `user_role` field
- [ ] 4.2 Add `filter` query parameter to board list endpoint
- [ ] 4.3 Update `GET /api/boards/:id` to include `user_role` in response
- [ ] 4.4 Update `GET /api/goals/:id` to allow member access with `user_role`
- [ ] 4.5 Add role-based permission checks to write endpoints (403 for viewers)

## 5. Backend Tests
- [ ] 5.1 Unit tests for sharing service (create link, accept, revoke, member CRUD)
- [ ] 5.2 Integration tests for sharing endpoints
- [ ] 5.3 Integration tests for ownership validation with shared access
- [ ] 5.4 Test viewer vs editor permission enforcement
- [ ] 5.5 Test edge cases (expired links, duplicate membership, owner self-join)

## 6. Frontend - Share Dialog
- [ ] 6.1 Create share dialog component (`features/sharing/components/share-dialog.tsx`)
- [ ] 6.2 Create share link list sub-component with copy-to-clipboard
- [ ] 6.3 Create member list sub-component with role management
- [ ] 6.4 Add share button to board view (visible to owner only)
- [ ] 6.5 Add "Shared with you" indicator for members

## 7. Frontend - Share Link Acceptance
- [ ] 7.1 Create `/share/:token` route
- [ ] 7.2 Implement auto-accept flow for authenticated users
- [ ] 7.3 Implement login/register redirect for unauthenticated users
- [ ] 7.4 Add error states for invalid/expired tokens

## 8. Frontend - Board List Updates
- [ ] 8.1 Update board list to show `user_role` badge (owner/editor/viewer)
- [ ] 8.2 Add filter controls for owned/shared/all boards
- [ ] 8.3 Generate updated API hooks via Orval

## 9. API Contract
- [ ] 9.1 Regenerate OpenAPI spec with new sharing endpoints
- [ ] 9.2 Regenerate Orval hooks for frontend consumption
