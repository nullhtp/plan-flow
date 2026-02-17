## ADDED Requirements

### Requirement: Pending Action Alembic Migration
The system SHALL include an Alembic migration that creates the `pending_action` table with columns: `id` (UUID PK), `user_id` (UUID FK to user), `thread_id` (varchar, indexed), `tool_name` (varchar), `tool_args` (JSON), `description` (varchar), `status` (varchar, default `pending`), `result` (JSON, nullable), `created_at` (timestamptz), `expires_at` (timestamptz). Indexes SHALL exist on `user_id`, `thread_id`, and `(thread_id, status)` for efficient lookups.

#### Scenario: Migration creates pending_action table
- **WHEN** `alembic upgrade head` is run
- **THEN** the `pending_action` table exists with all specified columns, foreign keys, and indexes

### Requirement: Board Chat Endpoint in Router
The system SHALL mount the `POST /api/boards/{board_id}/chat` endpoint in the AI router alongside the existing task chat endpoint. The endpoint SHALL follow the same authentication and ownership validation pattern as existing board endpoints (trace board to goal to user). The endpoint SHALL be tagged with `ai` in the OpenAPI spec.

#### Scenario: Board chat endpoint accessible
- **WHEN** an authenticated user sends POST /api/boards/{board_id}/chat
- **THEN** the request is routed to the board chat handler

#### Scenario: Board chat endpoint in OpenAPI spec
- **WHEN** the OpenAPI spec is generated
- **THEN** the board chat endpoint appears under the `ai` tag with request/response schemas documented
