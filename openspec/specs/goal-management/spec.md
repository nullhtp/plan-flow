# goal-management Specification

## Purpose
Goal lifecycle management. Covers the goal data model, status state machine (input through active/completed/archived), create/get/answer endpoints, and the adaptive questioning flow including follow-up question rounds.
## Requirements
### Requirement: Goal Data Model
The system SHALL store goals as database records with the following fields: `id` (UUID primary key), `user_id` (FK to User), `title` (AI-generated or user-provided), `original_input` (raw user text), `status` (pipeline state enum), `ai_context` (JSON), `created_at`, and `updated_at`. The `ai_context` JSON field SHALL store classification output, generated questions (each with required `options` list and `allow_other` flag), user answers, follow-up questions, follow-up answers, and `user_meta` (user environment context). The `user_meta` object within `ai_context` SHALL conform to the `UserMeta` schema: `timezone` (string, IANA), `locale` (string, BCP 47), `current_datetime` (string, ISO 8601 UTC), `location` (nullable object with optional `city` and `country`), and `device_type` (string). The `user_meta` is stored at goal creation time and used by the AI during question generation and board generation. Questions stored in `ai_context` SHALL always include a non-null `options` list (minimum 3 items) and an `allow_other` boolean field.

#### Scenario: Goal record created with initial fields
- **WHEN** a user submits a new goal via `POST /goals`
- **THEN** a Goal record is created with `original_input` set to the user's text, `status` set to `classifying`, `ai_context` initialized as an empty JSON object, and `user_id` set to the authenticated user's ID

#### Scenario: Goal ai_context populated after classification and question generation
- **WHEN** classification and question generation complete successfully
- **THEN** `ai_context` SHALL contain `classification` (domain, complexity, confidence, dimensions, suggested_title), `questions` (array of question schemas, each with non-null `options` and `allow_other` fields), and `user_meta` (if provided at goal creation), and `status` SHALL be `questioning`

#### Scenario: Goal ai_context includes user_meta when provided
- **WHEN** a user creates a goal with `user_meta` in the request body
- **THEN** `ai_context` SHALL contain a `user_meta` key with the timezone, locale, current_datetime, location, and device_type

#### Scenario: Backward compatibility with existing goals
- **WHEN** the system reads an existing goal whose `ai_context` contains questions with `options: null`
- **THEN** the API SHALL return the questions as-is (null options) and the frontend SHALL gracefully handle null options by falling back to a plain text input

### Requirement: Goal Status State Machine
The Goal model SHALL have a `status` field tracking pipeline progress through ordered states: `input`, `classifying`, `questioning`, `answered`, `generating`, `active`, `completed`, `archived`. M2 uses states through `answered`. M3 enables the `answered` -> `generating` -> `active` transitions when board generation is triggered. Transitions MUST be forward-only within a pipeline run (no skipping states). The `status` field SHALL be a string enum. The goals domain (`app/domains/goals/service.py`) SHALL own all goal status transitions, including `transition_to_generating()`, `transition_to_active()`, and `revert_to_answered()`. Other domains (e.g., boards) SHALL call these goal service functions to request state transitions rather than modifying goal status directly.

#### Scenario: Status transitions during goal creation
- **WHEN** a user creates a goal via `POST /goals`
- **THEN** the status transitions from `input` -> `classifying` -> `questioning` as the AI pipeline processes the goal

#### Scenario: Status transitions during answer submission
- **WHEN** a user submits answers and no follow-up questions are generated
- **THEN** the status transitions to `answered`

#### Scenario: Status remains questioning when follow-ups are generated
- **WHEN** a user submits initial answers and the AI generates follow-up questions
- **THEN** the status remains `questioning` until the follow-up answers are submitted

#### Scenario: Status transitions during board generation
- **WHEN** a user triggers board generation via `POST /goals/:id/generate-board`
- **THEN** the status transitions from `answered` -> `generating` while the AI processes, then to `active` when the board is successfully persisted

#### Scenario: Status reverts on generation failure
- **WHEN** the AI board generation fails (timeout, validation error, provider error)
- **THEN** the goal status reverts to `answered` so the user can retry

#### Scenario: Goal state transitions owned by goals domain
- **WHEN** the boards domain needs to transition a goal to `generating` status during board generation
- **THEN** it calls `goals/service.transition_to_generating()` instead of modifying the goal model directly

### Requirement: Create Goal Endpoint
The system SHALL expose `POST /api/goals` as an authenticated endpoint that accepts `{ "original_input": string, "user_meta"?: UserMeta }` in the request body. The `user_meta` field is optional. When provided, the system SHALL store it in `Goal.ai_context["user_meta"]` before running the AI pipeline. The backend SHALL also capture the client IP address from request headers (`X-Forwarded-For` or `request.client.host`) and store it in `ai_context["user_meta"]["client_ip"]` for potential future geolocation fallback. The `current_datetime` field in `user_meta` SHALL be set or overridden server-side to the current UTC time to prevent client clock manipulation. The endpoint SHALL create a Goal record, run the AI classification and question generation pipeline synchronously (passing `user_meta` to the question generation prompts when available), and return the result. On success, the response SHALL include the goal ID, suggested title, and generated questions. On rejection (goal too vague), the response SHALL include the rejection reason and refinement suggestions with HTTP 422.

#### Scenario: Successful goal creation with user meta and questions
- **WHEN** an authenticated user sends `POST /api/goals` with `{ "original_input": "Move from Berlin to Lisbon within 3 months", "user_meta": { "timezone": "Europe/Berlin", "locale": "de-DE", "location": { "city": "Berlin", "country": "Germany" }, "device_type": "desktop" } }`
- **THEN** the response status is 201 and the body contains `goal_id`, `title` (AI-suggested), `status` set to `questioning`, and `questions` (array of 3-7 question objects)
- **AND** `ai_context.user_meta` contains the provided meta with `current_datetime` set server-side

#### Scenario: Successful goal creation without user meta (backward compatible)
- **WHEN** an authenticated user sends `POST /api/goals` with `{ "original_input": "Learn Spanish in 6 months" }` (no `user_meta`)
- **THEN** the response status is 201 and goal creation proceeds normally without `user_meta` in `ai_context`

#### Scenario: Client IP captured for geolocation fallback
- **WHEN** a goal is created with `user_meta` that has no `location` (browser geolocation denied)
- **THEN** the backend stores the client IP in `ai_context.user_meta.client_ip` from request headers

#### Scenario: Server-side datetime override
- **WHEN** a goal is created with `user_meta` containing any `current_datetime` value
- **THEN** the backend overrides `current_datetime` with the current server UTC time

#### Scenario: Goal rejected as too vague
- **WHEN** an authenticated user sends `POST /api/goals` with `{ "original_input": "be happier" }`
- **AND** the AI classification confidence score is below the rejection threshold
- **THEN** the response status is 422 and the body contains `rejection_reason` (explanation) and `refinement_suggestions` (array of 2-3 concrete alternative goal descriptions)

#### Scenario: Unauthenticated request rejected
- **WHEN** an unauthenticated user sends `POST /api/goals`
- **THEN** the response status is 401

### Requirement: Submit Answers Endpoint
The system SHALL expose `POST /api/goals/:id/answers` as an authenticated endpoint that accepts `{ "answers": { [question_id]: value }, "round": number }`. For round 1, the endpoint SHALL store answers in `ai_context`, call the AI to determine if follow-up questions are needed, and return either follow-up questions or a completion confirmation. For round 2, the endpoint SHALL store follow-up answers and transition the goal status to `answered` without generating further follow-ups.

#### Scenario: Round 1 answers with follow-up questions generated
- **WHEN** a user submits round 1 answers for a goal in `questioning` status
- **AND** the AI determines additional information is needed
- **THEN** the response contains `follow_up_questions` (array of question objects), `is_complete` is false, and `ai_context` is updated with the initial answers

#### Scenario: Round 1 answers with no follow-ups needed
- **WHEN** a user submits round 1 answers for a goal in `questioning` status
- **AND** the AI determines no additional information is needed
- **THEN** the response contains an empty `follow_up_questions` array, `is_complete` is true, `status` transitions to `answered`, and `ai_context` is updated with the answers

#### Scenario: Round 2 answers always complete questioning
- **WHEN** a user submits round 2 answers for a goal in `questioning` status
- **THEN** the response has `is_complete` set to true, `status` transitions to `answered`, and `ai_context` is updated with both initial and follow-up answers

#### Scenario: Answers submitted for wrong goal status
- **WHEN** a user submits answers for a goal not in `questioning` status
- **THEN** the response status is 409 (Conflict) with an error message indicating the goal is not in the questioning phase

#### Scenario: User can only submit answers to own goals
- **WHEN** user A tries to submit answers to user B's goal
- **THEN** the response status is 404

### Requirement: Get Goal Endpoint
The system SHALL expose `GET /api/goals/:id` as an authenticated endpoint that returns the goal's current state including `id`, `title`, `original_input`, `status`, and relevant `ai_context` data (classification, questions, answers). Users SHALL only be able to retrieve their own goals.

#### Scenario: Retrieve goal in questioning status
- **WHEN** an authenticated user requests `GET /api/goals/:id` for their own goal in `questioning` status
- **THEN** the response includes the goal fields, classification summary, and current questions

#### Scenario: Retrieve another user's goal
- **WHEN** user A requests `GET /api/goals/:id` for user B's goal
- **THEN** the response status is 404

### Requirement: Goal Alembic Migration
The system SHALL include an Alembic migration that creates the `goal` table with all required columns, a foreign key to the `user` table, and an index on `user_id`.

#### Scenario: Migration creates goal table
- **WHEN** `alembic upgrade head` is run
- **THEN** the `goal` table exists with columns: `id` (UUID PK), `user_id` (UUID FK to user), `title` (varchar), `original_input` (text), `status` (varchar), `ai_context` (JSON), `created_at` (timestamptz), `updated_at` (timestamptz)
- **AND** an index exists on `user_id`

