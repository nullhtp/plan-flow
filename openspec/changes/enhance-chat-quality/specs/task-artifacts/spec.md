## MODIFIED Requirements

### Requirement: Artifact Response Schema
The system SHALL define `ArtifactResponse` Pydantic schema with fields: `id` (str), `task_id` (str), `title` (str), `content` (str), `content_type` (str), `created_by` (str), `created_at` (datetime), `updated_at` (datetime, nullable — null if never updated). `ArtifactListResponse` SHALL contain a field `artifacts` (list of `ArtifactResponse`).

#### Scenario: Artifact response includes all fields
- **WHEN** an artifact is returned from any endpoint
- **THEN** the response includes id, task_id, title, content, content_type, created_by, created_at, and updated_at

#### Scenario: Artifact response with no updates
- **WHEN** an artifact that has never been updated is returned
- **THEN** the response includes `updated_at` set to null or the same as `created_at`
