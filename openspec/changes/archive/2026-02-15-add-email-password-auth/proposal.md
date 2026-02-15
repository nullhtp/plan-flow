# Change: Add email + password authentication

## Why
PlanFlow requires user authentication before any core features (goals, boards) can be built. Users need to register, log in, log out, and access protected resources. This is the foundational security layer that all subsequent features depend on.

## What Changes
- Add `User` SQLModel with email, hashed password, and timestamps
- Add `backend/app/core/security.py` — password hashing (bcrypt) and JWT creation/verification
- Add `backend/app/core/deps.py` — shared `get_current_user` dependency
- Extend `backend/app/core/config.py` with auth settings (`SECRET_KEY`, token expiry, cookie config)
- Create `backend/app/domains/auth/` domain — models, schemas, router, service, deps
- Add endpoints: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `POST /auth/refresh`, `GET /auth/me`
- JWT access tokens (short-lived, 15 min) delivered via httpOnly cookies
- Refresh tokens (long-lived, 30 days) delivered via httpOnly cookies
- Generate first Alembic migration for the `user` table
- Register auth router in `main.py`
- Regenerate Orval API client to pick up auth endpoints
- Create `frontend/src/features/auth/` — login page, register page, auth context, route guards
- Add TanStack Router protected route pattern with redirect to `/login?returnTo=...`

## Impact
- Affected specs: new `user-auth` capability
- Affected code:
  - `backend/app/core/config.py` (extend settings)
  - `backend/app/core/security.py` (new)
  - `backend/app/core/deps.py` (new)
  - `backend/app/domains/auth/*` (new domain)
  - `backend/app/main.py` (add router, cookie middleware)
  - `backend/migrations/versions/` (first migration)
  - `backend/pyproject.toml` (add bcrypt, python-jose)
  - `frontend/src/features/auth/*` (new feature module)
  - `frontend/src/routes/` (login, register, route guards)
  - `frontend/src/api/generated/` (regenerated)
  - `docker-compose.yml` / `.env.example` (SECRET_KEY env var)
