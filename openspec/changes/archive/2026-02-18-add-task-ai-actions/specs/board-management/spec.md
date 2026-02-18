## ADDED Requirements

### Requirement: Artifact Data Model and Migration
The system SHALL define an `Artifact` SQLModel in `app/domains/boards/models.py` with fields: `id` (UUID string, primary key, default uuid4), `task_id` (UUID string, foreign key to `task.id`, on-delete cascade), `title` (str, max 200), `content` (text), `content_type` (str, default "text/markdown"), `created_by` (str, one of "ai" | "user"), `created_at` (datetime, server default), `updated_at` (datetime, server default, on-update). The model SHALL have an index on `task_id`. An Alembic migration SHALL create the `artifact` table.

#### Scenario: Artifact table created by migration
- **WHEN** the Alembic migration runs
- **THEN** the `artifact` table exists with all columns, the foreign key to `task` with cascade delete, and an index on `task_id`

### Requirement: Artifact Repository
The system SHALL define an `ArtifactRepository` in `app/domains/boards/artifact_repository.py` with methods: `create(db, task_id, title, content, content_type, created_by) -> Artifact`, `list_by_task(db, task_id) -> list[Artifact]` (ordered by created_at desc), `get_by_id(db, artifact_id) -> Artifact | None`, `delete(db, artifact_id) -> None`, `count_by_task(db, task_id) -> int`.

#### Scenario: List artifacts for a task ordered by newest first
- **WHEN** `list_by_task` is called for a task with 3 artifacts
- **THEN** the 3 artifacts are returned ordered by `created_at` descending

#### Scenario: Count artifacts for a task
- **WHEN** `count_by_task` is called for a task with 2 artifacts
- **THEN** the method returns 2

### Requirement: Artifact Service
The system SHALL define artifact service functions in `app/domains/boards/artifact_service.py` with methods: `create_artifact(db, task_id, title, content, content_type, created_by) -> Artifact`, `list_artifacts(db, task_id) -> list[Artifact]`, `get_artifact(db, artifact_id) -> Artifact`, `delete_artifact(db, artifact_id) -> None`. The service SHALL use `ArtifactRepository` for data access.

#### Scenario: Create artifact via service
- **WHEN** `create_artifact` is called with valid task_id and content
- **THEN** an Artifact record is created and returned

### Requirement: Artifact CRUD Router
The system SHALL provide artifact CRUD endpoints in the boards router: `GET /api/tasks/{task_id}/artifacts` (list), `GET /api/tasks/{task_id}/artifacts/{artifact_id}` (get), `DELETE /api/tasks/{task_id}/artifacts/{artifact_id}` (delete). All endpoints SHALL validate task ownership via the existing ownership utility. The router SHALL be mounted alongside existing task endpoints.

#### Scenario: List artifacts endpoint
- **WHEN** `GET /api/tasks/{task_id}/artifacts` is called by the task owner
- **THEN** the endpoint returns the list of artifacts for that task

#### Scenario: Delete artifact by non-owner
- **WHEN** `DELETE /api/tasks/{task_id}/artifacts/{artifact_id}` is called by a user who does not own the task
- **THEN** the endpoint returns 403 Forbidden

### Requirement: Action Suggestion Router
The system SHALL provide a `POST /api/tasks/{task_id}/actions/suggest` endpoint in the AI router. The endpoint SHALL validate task ownership, build the task context string (title, description, status, subtasks, immediate dependencies and dependents), call `generate_action_suggestions`, and return `ActionSuggestionsResponse`. The endpoint SHALL be mounted alongside the existing task chat endpoint.

#### Scenario: Action suggestions returned for owned task
- **WHEN** `POST /api/tasks/{task_id}/actions/suggest` is called by the task owner
- **THEN** the endpoint returns 2–4 action suggestions

#### Scenario: Action suggestions for non-owned task
- **WHEN** `POST /api/tasks/{task_id}/actions/suggest` is called by a non-owner
- **THEN** the endpoint returns 403 Forbidden
