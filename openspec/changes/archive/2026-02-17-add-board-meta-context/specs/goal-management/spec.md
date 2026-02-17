## MODIFIED Requirements

### Requirement: Goal Data Model
The system SHALL store goals as database records with the following fields: `id` (UUID primary key), `user_id` (FK to User), `title` (AI-generated or user-provided), `original_input` (raw user text), `status` (pipeline state enum), `ai_context` (JSON), `created_at`, and `updated_at`. The `ai_context` JSON field SHALL store classification output, generated questions, user answers, follow-up questions, follow-up answers, and `user_meta` (user environment context). The `user_meta` object within `ai_context` SHALL conform to the `UserMeta` schema: `timezone` (string, IANA), `locale` (string, BCP 47), `current_datetime` (string, ISO 8601 UTC), `location` (nullable object with optional `city` and `country`), and `device_type` (string). The `user_meta` is stored at goal creation time and used by the AI during question generation and board generation.

#### Scenario: Goal record created with initial fields
- **WHEN** a user submits a new goal via `POST /goals`
- **THEN** a Goal record is created with `original_input` set to the user's text, `status` set to `classifying`, `ai_context` initialized as an empty JSON object, and `user_id` set to the authenticated user's ID

#### Scenario: Goal ai_context populated after classification and question generation
- **WHEN** classification and question generation complete successfully
- **THEN** `ai_context` SHALL contain `classification` (domain, complexity, confidence, dimensions, suggested_title), `questions` (array of question schemas), and `user_meta` (if provided at goal creation), and `status` SHALL be `questioning`

#### Scenario: Goal ai_context includes user_meta when provided
- **WHEN** a user creates a goal with `user_meta` in the request body
- **THEN** `ai_context` SHALL contain a `user_meta` key with the timezone, locale, current_datetime, location, and device_type

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
