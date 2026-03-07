## ADDED Requirements

### Requirement: Goal Share Data Model
The system SHALL store goal share links as database records in a `goal_share` table with the following fields: `id` (UUID primary key), `goal_id` (FK to Goal, indexed), `token` (varchar(64), unique, cryptographically random hex string), `role` (varchar(20), one of `viewer` or `editor`), `created_by` (FK to User), `is_active` (boolean, default true), `created_at` (timestamptz), `expires_at` (timestamptz, nullable). A share link allows anyone with the token to join the goal as a member with the specified role. Multiple share links MAY exist per goal with different roles. Deactivated links (`is_active = false`) SHALL NOT allow new members to join.

#### Scenario: Share link created for a goal
- **WHEN** the goal owner creates a share link with role `editor`
- **THEN** a GoalShare record is created with a cryptographically random 32-byte hex token, `role` set to `editor`, `is_active` set to true, and `created_by` set to the owner's user ID

#### Scenario: Multiple share links per goal
- **WHEN** the owner creates a viewer link and an editor link for the same goal
- **THEN** two GoalShare records exist for the goal with different tokens and roles

#### Scenario: Deactivated share link prevents joining
- **WHEN** a user tries to accept a share link that has `is_active = false`
- **THEN** the system rejects the request with a 404 (link not found or inactive)

#### Scenario: Expired share link prevents joining
- **WHEN** a user tries to accept a share link whose `expires_at` is in the past
- **THEN** the system rejects the request with a 410 (Gone) indicating the link has expired

### Requirement: Goal Member Data Model
The system SHALL store goal members in a `goal_member` table with the following fields: `id` (UUID primary key), `goal_id` (FK to Goal, indexed), `user_id` (FK to User, indexed), `role` (varchar(20), one of `viewer` or `editor`), `joined_via` (FK to GoalShare, nullable — null if the owner), `created_at` (timestamptz). A unique constraint SHALL exist on `(goal_id, user_id)` to prevent duplicate memberships. The goal owner is NOT stored in the `goal_member` table — ownership is determined by `goal.user_id`.

#### Scenario: Member record created when accepting share link
- **WHEN** a user accepts a share link with role `editor`
- **THEN** a GoalMember record is created with `user_id` set to the accepting user, `role` set to `editor`, and `joined_via` set to the GoalShare ID

#### Scenario: Duplicate membership rejected
- **WHEN** a user who is already a member tries to accept another share link for the same goal
- **THEN** the system returns 409 (Conflict) indicating the user is already a member

#### Scenario: Owner cannot join own goal as member
- **WHEN** the goal owner tries to accept a share link for their own goal
- **THEN** the system returns 409 (Conflict) indicating the user already owns this goal

### Requirement: Share Link Management Endpoints
The system SHALL expose share link management endpoints accessible only to the goal owner:

- `POST /api/goals/:id/shares` — Create a share link. Request body: `{ "role": "viewer" | "editor", "expires_in_days"?: number }`. Returns the share link with token and a full shareable URL.
- `GET /api/goals/:id/shares` — List all share links for the goal (active and inactive).
- `DELETE /api/goals/:id/shares/:share_id` — Deactivate a share link (sets `is_active = false`). Does NOT remove existing members who joined via this link.

All endpoints SHALL validate that the goal exists and belongs to the authenticated user (owner only — members cannot manage shares).

#### Scenario: Owner creates a share link
- **WHEN** the goal owner sends `POST /api/goals/:id/shares` with `{ "role": "editor" }`
- **THEN** the response status is 201 and includes the share link `id`, `token`, `role`, `is_active`, `created_at`, and a `url` field with the full shareable URL

#### Scenario: Owner creates a share link with expiration
- **WHEN** the goal owner sends `POST /api/goals/:id/shares` with `{ "role": "viewer", "expires_in_days": 7 }`
- **THEN** the share link has `expires_at` set to 7 days from now

#### Scenario: Owner lists share links
- **WHEN** the goal owner sends `GET /api/goals/:id/shares`
- **THEN** the response contains all share links for the goal, each with member count

#### Scenario: Owner deactivates a share link
- **WHEN** the goal owner sends `DELETE /api/goals/:id/shares/:share_id`
- **THEN** the share link `is_active` is set to false and the response status is 200
- **AND** existing members who joined via this link retain their access

#### Scenario: Non-owner cannot manage shares
- **WHEN** a member (not owner) sends `POST /api/goals/:id/shares`
- **THEN** the response status is 403 (Forbidden)

### Requirement: Accept Share Link Endpoint
The system SHALL expose `POST /api/shares/accept` as an authenticated endpoint that accepts `{ "token": string }`. The endpoint SHALL look up the GoalShare by token, validate it is active and not expired, and create a GoalMember record for the authenticated user with the share link's role.

#### Scenario: Successfully accept a share link
- **WHEN** an authenticated user sends `POST /api/shares/accept` with a valid, active token
- **THEN** a GoalMember record is created and the response includes the `goal_id`, `role`, and board summary

#### Scenario: Accept invalid token
- **WHEN** a user sends `POST /api/shares/accept` with a non-existent token
- **THEN** the response status is 404

#### Scenario: Accept inactive share link
- **WHEN** a user sends `POST /api/shares/accept` with a deactivated share link's token
- **THEN** the response status is 404

#### Scenario: Unauthenticated user cannot accept
- **WHEN** an unauthenticated user sends `POST /api/shares/accept`
- **THEN** the response status is 401

### Requirement: Member Management Endpoints
The system SHALL expose member management endpoints accessible only to the goal owner:

- `GET /api/goals/:id/members` — List all members of the goal. Returns user ID, email, role, and joined date.
- `PATCH /api/goals/:id/members/:member_id` — Update a member's role. Request body: `{ "role": "viewer" | "editor" }`.
- `DELETE /api/goals/:id/members/:member_id` — Remove a member from the goal. Deletes the GoalMember record.

Members SHALL also be able to remove themselves via `DELETE /api/goals/:id/members/me` (leave the goal).

#### Scenario: Owner lists members
- **WHEN** the goal owner sends `GET /api/goals/:id/members`
- **THEN** the response contains all members with their user info, role, and joined date

#### Scenario: Owner updates member role
- **WHEN** the goal owner sends `PATCH /api/goals/:id/members/:member_id` with `{ "role": "viewer" }`
- **THEN** the member's role is updated to `viewer`

#### Scenario: Owner removes a member
- **WHEN** the goal owner sends `DELETE /api/goals/:id/members/:member_id`
- **THEN** the GoalMember record is deleted and the response status is 204

#### Scenario: Member leaves goal
- **WHEN** a member sends `DELETE /api/goals/:id/members/me`
- **THEN** their GoalMember record is deleted and the response status is 204

#### Scenario: Non-owner cannot manage other members
- **WHEN** a member (not owner) sends `DELETE /api/goals/:id/members/:member_id` for another member
- **THEN** the response status is 403

### Requirement: Shared Access Alembic Migration
The system SHALL include an Alembic migration that creates: (1) `goal_share` table with all specified columns, a foreign key to `goal`, a foreign key to `user`, a unique index on `token`, and an index on `goal_id`; (2) `goal_member` table with all specified columns, foreign keys to `goal`, `user`, and `goal_share`, a unique constraint on `(goal_id, user_id)`, and indexes on `goal_id` and `user_id`.

#### Scenario: Migration creates sharing tables
- **WHEN** `alembic upgrade head` is run
- **THEN** the `goal_share` table exists with all columns, foreign keys, and indexes
- **AND** the `goal_member` table exists with all columns, foreign keys, unique constraint, and indexes
- **AND** existing data is unaffected

### Requirement: Share Link Frontend Page
The system SHALL provide a share link acceptance page at `/share/:token` that: (1) if the user is authenticated, automatically calls the accept endpoint and redirects to the shared board; (2) if the user is not authenticated, shows a prompt to log in or register with a `returnTo` parameter preserving the share link URL.

#### Scenario: Authenticated user opens share link
- **WHEN** an authenticated user navigates to `/share/:token`
- **THEN** the system automatically accepts the share link and redirects to the shared board

#### Scenario: Unauthenticated user opens share link
- **WHEN** an unauthenticated user navigates to `/share/:token`
- **THEN** the page shows a login/register prompt with `returnTo=/share/:token`

#### Scenario: Invalid share link page
- **WHEN** a user navigates to `/share/:token` with an invalid or expired token
- **THEN** an error message is displayed indicating the link is invalid or expired

### Requirement: Share Dialog Frontend Component
The system SHALL provide a share dialog accessible from the board view that allows the goal owner to: (1) create new share links with role selection, (2) copy share links to clipboard, (3) view and deactivate existing share links, (4) view and remove members, (5) update member roles. The dialog SHALL only be visible to the goal owner. Members SHALL see a "Shared with you" indicator but not the management controls.

#### Scenario: Owner opens share dialog
- **WHEN** the goal owner clicks the share button on the board view
- **THEN** a dialog opens showing existing share links, members, and controls to create new links

#### Scenario: Owner copies share link
- **WHEN** the owner clicks "Copy link" for a share link in the dialog
- **THEN** the full share URL is copied to the clipboard with a confirmation toast

#### Scenario: Member sees shared indicator
- **WHEN** a member views a shared board
- **THEN** a "Shared with you" badge or indicator is visible, but no share management controls appear
