## 1. Database Layer
- [ ] 1.1 Create Alembic migration adding `board_share` and `board_member` tables with FKs, unique constraints, and indexes
- [ ] 1.2 Add `BoardShare` and `BoardMember` SQLModel models to `app/domains/boards/models.py`

## 2. Repository Layer
- [ ] 2.1 Create `app/domains/boards/share_repository.py` with CRUD for BoardShare (create/upsert, get by board_id, get by token, delete)
- [ ] 2.2 Create `app/domains/boards/member_repository.py` with CRUD for BoardMember (create, list by board_id, get by board_id+user_id, delete, check membership)

## 3. Ownership / Access Validation
- [ ] 3.1 Modify `ownership.py` — add `validate_board_access` that accepts owner OR collaborator, keep `validate_board_ownership` for owner-only checks
- [ ] 3.2 Update `validate_task_ownership`, `validate_subtask_ownership`, `validate_artifact_ownership` to use board access (owner or collaborator) instead of owner-only
- [ ] 3.3 Add helper `get_user_role_for_board(session, board_id, user_id) -> "owner" | "collaborator" | None`

## 4. Service Layer
- [ ] 4.1 Add share link management functions to `board_service.py` (create/regenerate, get, delete share link)
- [ ] 4.2 Add join-via-token function to `board_service.py` (validate token, create member or return idempotent)
- [ ] 4.3 Add member management functions to `board_service.py` (list members with user details, revoke member)
- [ ] 4.4 Update `list_boards` in `board_service.py` to support `shared=true` query parameter
- [ ] 4.5 Update board response building to include `role` field

## 5. Router / API Layer
- [ ] 5.1 Add share link endpoints to `router.py`: POST/GET/DELETE `/api/boards/:id/share`
- [ ] 5.2 Add join endpoint to `router.py`: POST `/api/boards/join`
- [ ] 5.3 Add member endpoints to `router.py`: GET `/api/boards/:id/members`, DELETE `/api/boards/:id/members/:user_id`
- [ ] 5.4 Update existing board/task/subtask endpoints to use access validation (owner or collaborator) instead of owner-only
- [ ] 5.5 Add `shared` query parameter to GET `/api/boards` endpoint
- [ ] 5.6 Add Pydantic request/response schemas for share, join, and member endpoints

## 6. Frontend
- [ ] 6.1 Regenerate API client via Orval after backend OpenAPI changes
- [ ] 6.2 Create share dialog component (copy link, member list, revoke buttons) on board detail page
- [ ] 6.3 Create join-board page/handler for share link URL (e.g., `/join?token=...`)
- [ ] 6.4 Update board list page to show shared boards tab/section
- [ ] 6.5 Show role indicator on shared boards (e.g., "Shared with you" badge)
- [ ] 6.6 Conditionally hide owner-only actions (delete board, share settings) for collaborators

## 7. Tests
- [ ] 7.1 Backend integration tests for share link CRUD endpoints (owner-only access)
- [ ] 7.2 Backend integration tests for join endpoint (valid token, invalid token, idempotent, owner self-join)
- [ ] 7.3 Backend integration tests for member management (list, revoke, cannot remove owner)
- [ ] 7.4 Backend integration tests for access validation (collaborator can edit tasks, cannot delete board)
- [ ] 7.5 Backend unit tests for ownership.py changes (owner access, collaborator access, no access)
