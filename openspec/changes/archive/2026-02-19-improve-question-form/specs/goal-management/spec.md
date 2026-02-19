## MODIFIED Requirements

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
