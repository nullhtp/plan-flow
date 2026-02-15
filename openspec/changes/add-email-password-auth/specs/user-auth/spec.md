## ADDED Requirements

### Requirement: User Registration
The system SHALL allow new users to register with an email address and password via `POST /auth/register`.

The email MUST be validated as a well-formed email address. The email MUST be unique (case-insensitive). The password MUST be at least 8 characters long. On success, the system SHALL create a new User record with a bcrypt-hashed password, set httpOnly access and refresh token cookies, and return the user profile (id, email, created_at).

#### Scenario: Successful registration
- **WHEN** a user submits a valid, unique email and a password of at least 8 characters to `POST /auth/register`
- **THEN** a new User record is created with the password bcrypt-hashed
- **AND** httpOnly cookies are set for `access_token` (15 min expiry) and `refresh_token` (30 day expiry)
- **AND** the response body contains the user's id, email, and created_at with status 201

#### Scenario: Duplicate email registration
- **WHEN** a user submits an email that already exists in the system (case-insensitive comparison)
- **THEN** the system returns HTTP 409 with an error message indicating the email is already registered

#### Scenario: Invalid email format
- **WHEN** a user submits a malformed email address
- **THEN** the system returns HTTP 422 with a validation error

#### Scenario: Password too short
- **WHEN** a user submits a password shorter than 8 characters
- **THEN** the system returns HTTP 422 with a validation error indicating the minimum length requirement

### Requirement: User Login
The system SHALL allow registered users to log in with their email and password via `POST /auth/login`.

On successful credential verification, the system SHALL set httpOnly access and refresh token cookies and return the user profile. On failure, the system SHALL return a generic error that does not reveal whether the email exists.

#### Scenario: Successful login
- **WHEN** a user submits a valid email and correct password to `POST /auth/login`
- **THEN** httpOnly cookies are set for `access_token` (15 min expiry) and `refresh_token` (30 day expiry)
- **AND** the response body contains the user's id, email, and created_at with status 200

#### Scenario: Wrong password
- **WHEN** a user submits a valid email but incorrect password
- **THEN** the system returns HTTP 401 with a generic "Invalid email or password" message

#### Scenario: Non-existent email
- **WHEN** a user submits an email that does not exist in the system
- **THEN** the system returns HTTP 401 with a generic "Invalid email or password" message (same as wrong password to prevent email enumeration)

#### Scenario: Inactive user login
- **WHEN** a user whose account is marked as inactive attempts to log in
- **THEN** the system returns HTTP 401 with a generic "Invalid email or password" message

### Requirement: User Logout
The system SHALL allow authenticated users to log out via `POST /auth/logout`.

Logout SHALL clear both access and refresh token cookies.

#### Scenario: Successful logout
- **WHEN** an authenticated user sends `POST /auth/logout`
- **THEN** the `access_token` and `refresh_token` cookies are cleared (set to empty with max-age=0)
- **AND** the response returns HTTP 200 with a success message

#### Scenario: Logout without authentication
- **WHEN** an unauthenticated request is sent to `POST /auth/logout`
- **THEN** the system still clears any cookies and returns HTTP 200 (idempotent, no error)

### Requirement: Token Refresh
The system SHALL allow clients to obtain a new access token using a valid refresh token via `POST /auth/refresh`.

#### Scenario: Successful token refresh
- **WHEN** a request with a valid, non-expired refresh token cookie is sent to `POST /auth/refresh`
- **THEN** a new `access_token` cookie is set with a fresh 15 min expiry
- **AND** a new `refresh_token` cookie is set with a fresh 30 day expiry (rotation)
- **AND** the response returns HTTP 200 with the user profile

#### Scenario: Expired refresh token
- **WHEN** a request with an expired refresh token cookie is sent to `POST /auth/refresh`
- **THEN** the system returns HTTP 401 and clears both token cookies

#### Scenario: Missing refresh token
- **WHEN** a request without a refresh token cookie is sent to `POST /auth/refresh`
- **THEN** the system returns HTTP 401

### Requirement: Current User Retrieval
The system SHALL provide a `GET /auth/me` endpoint that returns the authenticated user's profile.

#### Scenario: Authenticated user retrieves profile
- **WHEN** an authenticated user sends `GET /auth/me`
- **THEN** the response contains the user's id, email, is_active, and created_at with status 200

#### Scenario: Unauthenticated request
- **WHEN** a request without a valid access token is sent to `GET /auth/me`
- **THEN** the system returns HTTP 401

### Requirement: JWT httpOnly Cookie Transport
The system SHALL deliver all authentication tokens exclusively via httpOnly cookies. Tokens MUST NOT appear in response bodies.

Cookies MUST be configured as httpOnly, SameSite=Lax. The Secure flag MUST be enabled in production and MAY be disabled in development (localhost over HTTP). The refresh token cookie path MUST be scoped to `/api/auth/refresh`.

#### Scenario: Cookie security attributes in production
- **WHEN** the application runs in production mode
- **THEN** all token cookies are set with httpOnly=true, Secure=true, SameSite=Lax

#### Scenario: Cookie security attributes in development
- **WHEN** the application runs in development mode
- **THEN** all token cookies are set with httpOnly=true, Secure=false, SameSite=Lax

#### Scenario: Refresh token cookie path scoping
- **WHEN** a refresh token cookie is set
- **THEN** the cookie path is `/api/auth/refresh` so it is only sent on refresh requests

### Requirement: Password Security
The system SHALL hash all passwords using bcrypt before storage. Plain-text passwords MUST NOT be stored or logged.

#### Scenario: Password hashing on registration
- **WHEN** a user registers with a password
- **THEN** the password is hashed with bcrypt before being written to the database
- **AND** the plain-text password is not stored anywhere

#### Scenario: Password verification on login
- **WHEN** a user logs in with a password
- **THEN** the submitted password is verified against the stored bcrypt hash
- **AND** the plain-text password is not logged or persisted

### Requirement: User Model
The system SHALL store users in a `user` database table with the following fields: `id` (UUID, primary key), `email` (unique, case-insensitive index), `hashed_password`, `is_active` (boolean, default true), `created_at` (timestamp), `updated_at` (timestamp).

#### Scenario: User table schema
- **WHEN** the database migration for the user table is applied
- **THEN** the table contains columns: id (UUID PK), email (unique indexed varchar), hashed_password (varchar), is_active (boolean default true), created_at (timestamp with timezone), updated_at (timestamp with timezone)

### Requirement: CORS Credentials Support
The system SHALL configure CORS middleware to allow credentials (cookies) from the frontend origin. `Access-Control-Allow-Credentials` MUST be `true` and `Access-Control-Allow-Origin` MUST be the specific frontend origin (not wildcard).

#### Scenario: Cross-origin cookie support
- **WHEN** the frontend at `http://localhost:5173` makes a credentialed request to the backend at `http://localhost:8000`
- **THEN** the response includes `Access-Control-Allow-Credentials: true` and `Access-Control-Allow-Origin: http://localhost:5173`

### Requirement: Frontend Route Protection
The system SHALL prevent unauthenticated users from accessing protected routes. When an unauthenticated user navigates to a protected route, the system SHALL redirect to `/login` with a `returnTo` query parameter containing the originally requested path. After successful login, the system SHALL redirect back to the `returnTo` path.

#### Scenario: Unauthenticated user redirected to login
- **WHEN** an unauthenticated user navigates to a protected route (e.g., `/dashboard`)
- **THEN** the browser redirects to `/login?returnTo=%2Fdashboard`

#### Scenario: Post-login redirect
- **WHEN** a user successfully logs in with a `returnTo` parameter present
- **THEN** the browser redirects to the path specified in `returnTo`

#### Scenario: Login without returnTo
- **WHEN** a user successfully logs in without a `returnTo` parameter
- **THEN** the browser redirects to the default authenticated route (`/`)

### Requirement: Frontend Auth State Management
The system SHALL provide an `AuthProvider` React context and `useAuth()` hook that exposes the current user, authentication status, and loading state. Auth state SHALL be hydrated on app load via `GET /auth/me` using TanStack Query.

#### Scenario: App load with valid session
- **WHEN** the application loads and the user has a valid access token cookie
- **THEN** `GET /auth/me` returns the user profile
- **AND** `useAuth()` provides `{ user, isAuthenticated: true, isLoading: false }`

#### Scenario: App load without session
- **WHEN** the application loads and the user has no valid token cookies
- **THEN** `GET /auth/me` returns 401
- **AND** `useAuth()` provides `{ user: null, isAuthenticated: false, isLoading: false }`

#### Scenario: Auth state after login
- **WHEN** a user successfully logs in via the login form
- **THEN** the `/auth/me` query is invalidated and refetched
- **AND** `useAuth()` updates to reflect the authenticated user

#### Scenario: Auth state after logout
- **WHEN** a user logs out
- **THEN** the `/auth/me` query is invalidated and cleared
- **AND** `useAuth()` updates to `{ user: null, isAuthenticated: false }`

### Requirement: Login Page
The system SHALL provide a login page at `/login` with an email field, a password field, and a submit button. The page SHALL display validation errors inline and server errors (e.g., "Invalid email or password") as a form-level message. The page SHALL include a link to the registration page.

#### Scenario: Successful login submission
- **WHEN** a user enters valid credentials and submits the login form
- **THEN** the form calls `POST /auth/login`, receives cookies, and redirects to the authenticated area

#### Scenario: Login validation error display
- **WHEN** a user submits the login form with an empty email or password
- **THEN** inline validation errors are displayed without making an API call

#### Scenario: Login server error display
- **WHEN** the server returns 401 for a login attempt
- **THEN** a form-level error message "Invalid email or password" is displayed

### Requirement: Registration Page
The system SHALL provide a registration page at `/register` with an email field, a password field, a confirm password field, and a submit button. The page SHALL validate that passwords match and meet the minimum length requirement. The page SHALL include a link to the login page.

#### Scenario: Successful registration submission
- **WHEN** a user enters a valid unique email, a password of at least 8 characters, and a matching confirmation
- **THEN** the form calls `POST /auth/register`, receives cookies, and redirects to the authenticated area

#### Scenario: Password mismatch
- **WHEN** a user enters a password and confirmation that do not match
- **THEN** an inline validation error is displayed without making an API call

#### Scenario: Registration server error display
- **WHEN** the server returns 409 (email already registered) for a registration attempt
- **THEN** a form-level error message is displayed indicating the email is already in use
