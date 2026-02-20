## MODIFIED Requirements
### Requirement: Goal Data Model
The system SHALL store goals as database records with the following fields: `id` (UUID primary key), `user_id` (FK to User), `title` (AI-generated or user-provided), `original_input` (raw user text), `status` (pipeline state enum), `ai_context` (JSON), `created_at`, and `updated_at`. The `ai_context` JSON field SHALL store classification output, question-answer rounds as an ordered array, and `user_meta` (user environment context). The `ai_context.rounds` field SHALL be an array of round objects, each containing: `round` (integer, 1-indexed), `questions` (array of question schemas), `answers` (dict mapping question ID to value), and `readiness` (readiness assessment object with `score`, `covered_dimensions`, `uncovered_dimensions`, `summary`). Round 1 SHALL contain the initial questions; subsequent rounds contain follow-up questions. The `user_meta` object within `ai_context` SHALL conform to the `UserMeta` schema: `timezone` (string, IANA), `locale` (string, BCP 47), `current_datetime` (string, ISO 8601 UTC), `location` (nullable object with optional `city` and `country`), and `device_type` (string). The `user_meta` is stored at goal creation time and used by the AI during question generation and board generation. Questions stored in `ai_context` SHALL always include a non-null `options` list (minimum 3 items) and an `allow_other` boolean field.

#### Scenario: Goal record created with initial fields
- **WHEN** a user submits a new goal via `POST /goals`
- **THEN** a Goal record is created with `original_input` set to the user's text, `status` set to `classifying`, `ai_context` initialized as an empty JSON object, and `user_id` set to the authenticated user's ID

#### Scenario: Goal ai_context populated after classification and question generation
- **WHEN** classification and question generation complete successfully
- **THEN** `ai_context` SHALL contain `classification` (domain, complexity, confidence, dimensions, suggested_title), `rounds` (array with one entry for round 1 containing `questions`, empty `answers`, and initial `readiness`), and `user_meta` (if provided at goal creation), and `status` SHALL be `questioning`

#### Scenario: Goal ai_context includes user_meta when provided
- **WHEN** a user creates a goal with `user_meta` in the request body
- **THEN** `ai_context` SHALL contain a `user_meta` key with the timezone, locale, current_datetime, location, and device_type

#### Scenario: Backward compatibility with existing goals
- **WHEN** the system reads an existing goal whose `ai_context` contains the old flat format (`questions`, `answers`, `follow_up_questions`, `follow_up_answers` at the top level)
- **THEN** the API SHALL convert the old format to the rounds array format on-the-fly when serving the response, mapping initial Q&A to round 1 and follow-up Q&A to round 2

#### Scenario: Multiple rounds stored in ai_context
- **WHEN** a user has completed 4 rounds of Q&A
- **THEN** `ai_context.rounds` contains 4 entries, each with its `round` number, `questions`, `answers`, and `readiness` assessment

### Requirement: Goal Status State Machine
The Goal model SHALL have a `status` field tracking pipeline progress through ordered states: `input`, `classifying`, `questioning`, `generating`, `active`, `completed`, `archived`. The `questioning` status SHALL persist throughout all iterative question-answer rounds. When the user triggers board generation, the status transitions directly from `questioning` to `generating`, then to `active` upon successful generation. The `answered` status SHALL be retained in the enum for backward compatibility with existing goals but SHALL NOT be used for new goals. The board generation endpoint SHALL accept goals in either `questioning` or `answered` status (for backward compatibility). Transitions MUST be forward-only within a pipeline run (no skipping states). The `status` field SHALL be a string enum. The goals domain (`app/domains/goals/service.py`) SHALL own all goal status transitions, including `transition_to_generating()`, `transition_to_active()`, and `revert_to_questioning()`. The existing `revert_goal_to_answered()` function SHALL be renamed to `revert_goal_to_questioning()` and SHALL revert the goal to `questioning` status instead of `answered`. Other domains (e.g., boards) SHALL call these goal service functions to request state transitions rather than modifying goal status directly.

#### Scenario: Status transitions during goal creation
- **WHEN** a user creates a goal via `POST /goals`
- **THEN** the status transitions from `input` -> `classifying` -> `questioning` as the AI pipeline processes the goal

#### Scenario: Status remains questioning throughout iterative rounds
- **WHEN** a user submits answers for round 1, 2, 3, etc.
- **THEN** the status remains `questioning` throughout all rounds

#### Scenario: Status transitions during board generation from questioning
- **WHEN** a user triggers board generation via `POST /goals/:id/generate-board` for a goal in `questioning` status
- **THEN** the status transitions from `questioning` -> `generating` while the AI processes, then to `active` when the board is successfully persisted

#### Scenario: Backward compatible board generation from answered status
- **WHEN** a user triggers board generation for an existing goal in `answered` status (legacy)
- **THEN** the status transitions from `answered` -> `generating` -> `active` as before

#### Scenario: Status reverts on generation failure
- **WHEN** the AI board generation fails (timeout, validation error, provider error)
- **THEN** the goal status reverts to `questioning` so the user can retry or answer more questions

#### Scenario: Goal state transitions owned by goals domain
- **WHEN** the boards domain needs to transition a goal to `generating` status during board generation
- **THEN** it calls `goals/service.transition_to_generating()` instead of modifying the goal model directly

### Requirement: Submit Answers Endpoint
The system SHALL expose `POST /api/goals/:id/answers` as an authenticated endpoint that accepts `{ "answers": { [question_id]: value }, "round": number }`. The endpoint SHALL store answers for the specified round in `ai_context.rounds[round-1].answers`, then call the AI to generate the next batch of follow-up questions with a readiness assessment. The response SHALL always include `next_questions` (array of 2-4 question objects for the next round), `readiness` (readiness assessment object), and `next_round` (integer, the round number for the newly generated questions). When the submitted `round` is less than the current maximum round stored in `ai_context`, the endpoint SHALL truncate all rounds after the submitted round before storing answers and generating new follow-ups (supporting the edit-and-regenerate flow). The endpoint SHALL NOT transition the goal out of `questioning` status — the goal remains in `questioning` until the user triggers board generation.

#### Scenario: Round 1 answers submitted with follow-up generation
- **WHEN** a user submits round 1 answers for a goal in `questioning` status
- **THEN** the response contains `next_questions` (2-4 follow-up questions), `readiness` (assessment with initial coverage), and `next_round` (2)

#### Scenario: Round N answers submitted with progressive follow-up
- **WHEN** a user submits round 4 answers for a goal in `questioning` status
- **THEN** the response contains `next_questions` (2-4 deeper questions), `readiness` (updated assessment reflecting all 4 rounds of answers), and `next_round` (5)

#### Scenario: Earlier round re-submitted truncates later rounds
- **WHEN** a user re-submits edited answers for round 2 and rounds 3-5 exist in `ai_context`
- **THEN** rounds 3-5 are deleted from `ai_context.rounds`, round 2 answers are updated, and new follow-up questions are generated as round 3

#### Scenario: Answers submitted for wrong goal status
- **WHEN** a user submits answers for a goal not in `questioning` status
- **THEN** the response status is 409 (Conflict) with an error message indicating the goal is not in the questioning phase

#### Scenario: User can only submit answers to own goals
- **WHEN** user A tries to submit answers to user B's goal
- **THEN** the response status is 404

### Requirement: Create Goal Endpoint
The system SHALL expose `POST /api/goals` as an authenticated endpoint that accepts `{ "original_input": string, "user_meta"?: UserMeta }` in the request body. The `user_meta` field is optional. When provided, the system SHALL store it in `Goal.ai_context["user_meta"]` before running the AI pipeline. The backend SHALL also capture the client IP address from request headers (`X-Forwarded-For` or `request.client.host`) and store it in `ai_context["user_meta"]["client_ip"]` for potential future geolocation fallback. The `current_datetime` field in `user_meta` SHALL be set or overridden server-side to the current UTC time to prevent client clock manipulation. The endpoint SHALL create a Goal record, run the AI classification and question generation pipeline synchronously (passing `user_meta` to the question generation prompts when available), and return the result. On success, the response SHALL include the goal ID, suggested title, generated questions for round 1, and the initial readiness assessment. On rejection (goal too vague), the response SHALL include the rejection reason and refinement suggestions with HTTP 422.

#### Scenario: Successful goal creation with user meta, questions, and readiness
- **WHEN** an authenticated user sends `POST /api/goals` with `{ "original_input": "Move from Berlin to Lisbon within 3 months", "user_meta": { "timezone": "Europe/Berlin", "locale": "de-DE", "location": { "city": "Berlin", "country": "Germany" }, "device_type": "desktop" } }`
- **THEN** the response status is 201 and the body contains `goal_id`, `title` (AI-suggested), `status` set to `questioning`, `questions` (array of 3-7 question objects for round 1), and `readiness` (initial assessment with score near 0.0)

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


