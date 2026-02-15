## 1. Backend Dependencies & Configuration
- [ ] 1.1 Add `passlib[bcrypt]` and `python-jose[cryptography]` to `backend/pyproject.toml` dependencies
- [ ] 1.2 Add auth settings to `backend/app/core/config.py`: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` (15), `REFRESH_TOKEN_EXPIRE_DAYS` (30), `COOKIE_SECURE` (env-based), `FRONTEND_ORIGIN`
- [ ] 1.3 Add `SECRET_KEY` and `FRONTEND_ORIGIN` to `.env.example` and `docker-compose.yml` environment

## 2. Core Security Utilities
- [ ] 2.1 Create `backend/app/core/security.py` with `hash_password()`, `verify_password()` (passlib bcrypt), `create_access_token()`, `create_refresh_token()`, `decode_token()` (python-jose)
- [ ] 2.2 Create `backend/app/core/deps.py` with `get_current_user()` dependency (reads access_token from cookie, decodes JWT, fetches User from DB, raises 401 if invalid)

## 3. Auth Domain — Models & Schemas
- [ ] 3.1 Create `backend/app/domains/auth/__init__.py`
- [ ] 3.2 Create `backend/app/domains/auth/models.py` with `User` SQLModel: id (UUID), email (unique indexed), hashed_password, is_active (default True), created_at, updated_at
- [ ] 3.3 Create `backend/app/domains/auth/schemas.py` with `RegisterRequest` (email, password), `LoginRequest` (email, password), `UserResponse` (id, email, is_active, created_at)

## 4. Database Migration
- [ ] 4.1 Import User model in Alembic env.py so autogenerate discovers it
- [ ] 4.2 Generate first Alembic migration for the `user` table
- [ ] 4.3 Verify migration applies cleanly (`alembic upgrade head`)

## 5. Auth Domain — Service & Router
- [ ] 5.1 Create `backend/app/domains/auth/service.py` with `register_user()`, `authenticate_user()`, `get_user_by_id()` functions
- [ ] 5.2 Create `backend/app/domains/auth/deps.py` with domain-specific dependencies if needed (e.g., `get_current_active_user`)
- [ ] 5.3 Create `backend/app/domains/auth/router.py` with endpoints:
  - `POST /auth/register` — validate input, create user, set cookies, return 201
  - `POST /auth/login` — verify credentials, set cookies, return 200
  - `POST /auth/logout` — clear cookies, return 200
  - `POST /auth/refresh` — read refresh cookie, issue new tokens, return 200
  - `GET /auth/me` — return current user profile, return 200
- [ ] 5.4 Create cookie-setting helper function (reusable for login, register, refresh)

## 6. App Integration
- [ ] 6.1 Register auth router in `backend/app/main.py` with prefix `/api/auth`
- [ ] 6.2 Update CORS middleware: set `allow_credentials=True`, replace wildcard origin with `settings.FRONTEND_ORIGIN`

## 7. Backend Tests
- [ ] 7.1 Set up test fixtures in `backend/tests/conftest.py`: async test client, test DB session, user factory helper
- [ ] 7.2 Write tests for `core/security.py`: password hashing roundtrip, token creation/decoding, expired token rejection
- [ ] 7.3 Write tests for `POST /auth/register`: success (201 + cookies), duplicate email (409), invalid email (422), short password (422)
- [ ] 7.4 Write tests for `POST /auth/login`: success (200 + cookies), wrong password (401), non-existent email (401), inactive user (401)
- [ ] 7.5 Write tests for `POST /auth/logout`: clears cookies (200)
- [ ] 7.6 Write tests for `POST /auth/refresh`: success (200 + new cookies), expired token (401), missing token (401)
- [ ] 7.7 Write tests for `GET /auth/me`: authenticated (200), unauthenticated (401)

## 8. Frontend API Client Regeneration
- [ ] 8.1 Regenerate Orval API client from updated OpenAPI spec (new auth endpoints)
- [ ] 8.2 Verify generated hooks include auth mutations and queries

## 9. Frontend Auth Infrastructure
- [ ] 9.1 Create `frontend/src/features/auth/hooks/use-auth.ts` — `AuthProvider` context + `useAuth()` hook using TanStack Query for `GET /auth/me`
- [ ] 9.2 Wrap app with `AuthProvider` in `frontend/src/app.tsx`
- [ ] 9.3 Configure the API client / fetch to send `credentials: "include"` for all requests

## 10. Frontend Auth Pages
- [ ] 10.1 Create `frontend/src/routes/login.tsx` — login page with email/password form, validation, error display, link to register
- [ ] 10.2 Create `frontend/src/routes/register.tsx` — register page with email/password/confirm form, validation, error display, link to login
- [ ] 10.3 Create `frontend/src/features/auth/components/` — extract shared form components if needed

## 11. Frontend Route Protection
- [ ] 11.1 Implement authenticated route layout using TanStack Router `beforeLoad` guard with `returnTo` redirect
- [ ] 11.2 Add redirect logic after login/register to honor `returnTo` search param
- [ ] 11.3 Update root route to serve as authenticated shell (or add an `_authenticated` layout route)

## 12. Frontend Tests
- [ ] 12.1 Write tests for login page: form submission, validation errors, server error display
- [ ] 12.2 Write tests for register page: form submission, password mismatch, server error display
- [ ] 12.3 Write tests for auth context: authenticated state, unauthenticated state, loading state

## 13. End-to-End Verification
- [ ] 13.1 Manually verify full flow in Docker Compose: register -> auto-login -> refresh -> access /auth/me -> logout -> route guard redirect
- [ ] 13.2 Verify cookies are httpOnly and correctly scoped (browser DevTools)
- [ ] 13.3 Run full backend test suite (`pytest`)
- [ ] 13.4 Run full frontend test suite (`vitest`)
- [ ] 13.5 Run linters and type checks (`ruff`, `pyright`, `biome`, `tsc`)
