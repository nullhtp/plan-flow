## MODIFIED Requirements

### Requirement: Artifact Creation Triggers Refresh
The system SHALL refetch the artifacts list after any chat response that includes a `save_artifact` or `update_artifact` tool action with status "executed". This ensures newly created or updated artifacts appear in the Artifacts section without manual refresh.

#### Scenario: New artifact appears after AI generates content
- **WHEN** the AI chat response includes a `save_artifact` tool action with status "executed"
- **THEN** the Artifacts section refetches and displays the newly created artifact

#### Scenario: Updated artifact appears after AI revises content
- **WHEN** the AI chat response includes an `update_artifact` tool action with status "executed"
- **THEN** the Artifacts section refetches and displays the updated artifact with its new content
