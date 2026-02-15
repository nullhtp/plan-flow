## Context

PlanFlow is a SPA (React + Vite) with a FastAPI backend. Authentication must work across these two separate origins during development (frontend on `:5173`, backend on `:8000`). The project uses no OAuth — email + password only for MVP. This is the first domain being built, so it sets patterns that all future domains will follow.

Key stakeholders: solo developer, MVP timeline of 1-2 months.

## Goals / Non-Goals

- **Goals:**
  - Secure email + password registration and login
  - JWT-based stateless authentication with httpOnly cookies
  - Refresh token rotation for persistent sessions
  - Protected route pattern on the frontend that other features can reuse
  - `get_current_user` dependency usable by all future backend domains
  - First Alembic migration establishing the User table

- **Non-Goals:**
  - OAuth / social login (explicitly excluded from MVP)
  - Email verification (deferred)
  - Password reset flow (deferred)
  - Rate limiting on auth endpoints (deferred)
  - Two-factor authentication
  - User profile management (separate change)

## Decisions

### 1. Token delivery: httpOnly cookies (not response body)

**Decision:** Both access and refresh tokens are set as httpOnly, Secure, SameSite=Lax cookies by the backend. The frontend never touches tokens directly.

**Why:** Prevents XSS attacks from stealing tokens. The SPA makes credentialed requests (`credentials: "include"` / `withCredentials`) and the backend reads tokens from cookie headers.

**Alternatives considered:**
- *JWT in response body + localStorage:* Simpler but tokens are accessible to any JS on the page (XSS risk). Rejected for security.
- *Server-side sessions (Redis/DB):* Most secure but adds stateful infrastructure. Over-engineered for MVP. Rejected for complexity.

**Cookie configuration:**
| Cookie | Name | Max-Age | Path | httpOnly | Secure | SameSite |
|--------|------|---------|------|----------|--------|----------|
| Access | `access_token` | 900s (15 min) | `/api` | Yes | Yes (No in dev) | Lax |
| Refresh | `refresh_token` | 30 days | `/api/auth/refresh` | Yes | Yes (No in dev) | Lax |

- Refresh token cookie path is scoped to `/api/auth/refresh` so it's only sent on refresh requests, reducing exposure.
- `Secure` flag is disabled in development (HTTP on localhost) and enabled in production.

### 2. Token type: JWT with access + refresh pair

**Decision:** Short-lived access token (15 min) + long-lived refresh token (30 days). Both are JWTs signed with HS256.

**Why:** Access tokens expire quickly, limiting damage from token theft. Refresh tokens allow users to stay logged in. HS256 is sufficient for a single-service architecture (no need for asymmetric RS256).

**Access token payload:**
```json
{
  "sub": "<user_uuid>",
  "exp": "<timestamp>",
  "type": "access"
}
```

**Refresh token payload:**
```json
{
  "sub": "<user_uuid>",
  "exp": "<timestamp>",
  "type": "refresh"
}
```

### 3. Password hashing: bcrypt via passlib

**Decision:** Use `passlib[bcrypt]` with the CryptContext configured for bcrypt.

**Why:** bcrypt is the industry standard for password hashing. passlib provides a clean API and handles salt generation, work factor tuning, and hash verification. Widely used in FastAPI projects.

**Alternatives considered:**
- *argon2:* Newer, arguably better, but less ecosystem support in Python. passlib supports it if we want to switch later.
- *Raw bcrypt library:* Lower-level, more manual work. passlib is a thin wrapper that adds convenience.

### 4. User model: minimal for MVP

**Decision:** `User` table with: `id` (UUID), `email` (unique, indexed), `hashed_password`, `is_active` (default true), `created_at`, `updated_at`.

**Why:** Only the fields needed for authentication. Display name, avatar, and other profile fields are deferred to a separate change. `is_active` provides a soft-disable mechanism without deletion.

### 5. Frontend auth state: React Context + TanStack Query

**Decision:** An `AuthProvider` context wraps the app. It uses TanStack Query to call `GET /auth/me` on app load to determine auth state. The query result is exposed via `useAuth()` hook.

**Why:** TanStack Query already handles caching, loading states, and error handling. Combining it with a thin React Context gives components easy access to `user`, `isAuthenticated`, `isLoading`. No additional state library needed.

**Auth flow:**
1. On app load, `GET /auth/me` fires (cookie sent automatically)
2. If 200 — user is authenticated, context provides user data
3. If 401 — user is unauthenticated, context provides `null`
4. On login/register — mutation calls endpoint, on success invalidates the `/auth/me` query
5. On logout — mutation calls `POST /auth/logout`, on success invalidates and clears query

### 6. Route protection: TanStack Router `beforeLoad` guard

**Decision:** Protected routes use TanStack Router's `beforeLoad` hook to check auth state. If unauthenticated, throw `redirect({ to: '/login', search: { returnTo: location.href } })`.

**Why:** This is TanStack Router's built-in mechanism for route guards. It runs before the route component loads, preventing flash of protected content.

### 7. CORS configuration for cookie-based auth

**Decision:** Update CORS middleware to include `allow_credentials=True` and explicitly list allowed origins (no wildcard).

**Why:** Browsers block cookies on cross-origin requests unless the server explicitly allows credentials. `Access-Control-Allow-Origin` cannot be `*` when credentials are allowed — must be the specific frontend origin.

## Risks / Trade-offs

- **Risk:** httpOnly cookies add cross-origin complexity (CORS credentials, SameSite, Secure flag per environment)
  - *Mitigation:* Document cookie config clearly. Use environment-based Secure flag. Test cross-origin auth in Docker Compose.

- **Risk:** No refresh token revocation (tokens valid until expiry)
  - *Mitigation:* 30-day refresh token expiry limits exposure. Token revocation (blocklist) can be added later if needed. For MVP with single-user focus, this is acceptable.

- **Risk:** No email verification means anyone can register with any email
  - *Mitigation:* Acceptable for MVP. Email verification will be added as a separate change before public launch.

- **Trade-off:** `passlib` is in maintenance mode (no new features, still receives security fixes)
  - *Mitigation:* passlib is stable and widely used. If it becomes unmaintained, switching to raw `bcrypt` library is straightforward.

## Open Questions

- None — all decisions resolved via user input.
