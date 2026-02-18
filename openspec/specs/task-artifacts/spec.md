# task-artifacts Specification

## Purpose
TBD - created by archiving change add-task-ai-actions. Update Purpose after archive.
## Requirements
### Requirement: Artifact Data Model
The system SHALL define an `Artifact` SQLModel with fields: `id` (UUID, primary key), `task_id` (UUID, foreign key to task), `title` (str, max 200 chars), `content` (text, markdown), `content_type` (str, default "text/markdown"), `created_by` (str, one of "ai" or "user"), `created_at` (datetime, server default), `updated_at` (datetime, server default, on-update). The model SHALL have an index on `task_id` for efficient querying. Deleting a task SHALL cascade-delete its artifacts.

#### Scenario: Artifact created by AI
- **WHEN** the AI chat calls the `save_artifact` tool with title "Rental Agreement Draft" and markdown content
- **THEN** an Artifact record is created with `created_by: "ai"`, the provided title and content, and `content_type: "text/markdown"`

#### Scenario: Artifacts cascade-deleted with task
- **WHEN** a task with 3 artifacts is deleted
- **THEN** all 3 artifact records are also deleted

### Requirement: Artifact Alembic Migration
The system SHALL include an Alembic migration that creates the `artifact` table with all columns, indexes, and the foreign key constraint to the `task` table with cascade delete.

#### Scenario: Migration creates artifact table
- **WHEN** the migration runs
- **THEN** the `artifact` table is created with columns: id, task_id, title, content, content_type, created_by, created_at, updated_at, and an index on task_id

### Requirement: Artifact CRUD Endpoints
The system SHALL provide the following endpoints for artifact management:
- `GET /api/tasks/{task_id}/artifacts` — list all artifacts for a task, ordered by `created_at` descending
- `GET /api/tasks/{task_id}/artifacts/{artifact_id}` — get a single artifact
- `DELETE /api/tasks/{task_id}/artifacts/{artifact_id}` — delete an artifact
All endpoints SHALL validate task ownership (task → board → goal → user_id).

#### Scenario: List artifacts for a task
- **WHEN** a user requests artifacts for a task with 2 artifacts
- **THEN** the endpoint returns both artifacts ordered by creation date (newest first)

#### Scenario: List artifacts for a task with none
- **WHEN** a user requests artifacts for a task with no artifacts
- **THEN** the endpoint returns an empty list

#### Scenario: Delete an artifact
- **WHEN** a user deletes an artifact they own
- **THEN** the artifact is removed and subsequent list requests do not include it

#### Scenario: Delete artifact on another user's task
- **WHEN** a user tries to delete an artifact on a task they do not own
- **THEN** the endpoint returns 403 Forbidden

#### Scenario: Artifact not found
- **WHEN** a user requests a non-existent artifact ID
- **THEN** the endpoint returns 404 Not Found

### Requirement: Artifact Response Schema
The system SHALL define `ArtifactResponse` Pydantic schema with fields: `id` (str), `task_id` (str), `title` (str), `content` (str), `content_type` (str), `created_by` (str), `created_at` (datetime). `ArtifactListResponse` SHALL contain a field `artifacts` (list of `ArtifactResponse`).

#### Scenario: Artifact response includes all fields
- **WHEN** an artifact is returned from any endpoint
- **THEN** the response includes id, task_id, title, content, content_type, created_by, and created_at

### Requirement: Artifact Included in Task Response
The system SHALL include a summary of artifacts in the `TaskResponse` schema. A new field `artifact_count` (int, default 0) SHALL be added to `TaskResponse`, representing the number of artifacts associated with the task. This allows the UI to show an artifact indicator without fetching full artifact content.

#### Scenario: Task response includes artifact count
- **WHEN** a task with 3 artifacts is fetched
- **THEN** the task response includes `artifact_count: 3`

#### Scenario: Task response with no artifacts
- **WHEN** a task with no artifacts is fetched
- **THEN** the task response includes `artifact_count: 0`

