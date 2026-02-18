## MODIFIED Requirements

### Requirement: Task Dependency Query Helpers
The system SHALL provide query helper functions in the boards domain to efficiently retrieve dependency information: `get_task_dependencies(task_id)` returning all prerequisite tasks, `get_task_dependents(task_id)` returning all tasks that depend on the given task, and `are_dependencies_met(task_id)` returning a boolean indicating whether all prerequisite tasks have status `done`. These helpers SHALL be implemented in `app/domains/boards/task_repository.py` (for raw DB queries) and exposed through `app/domains/boards/task_service.py` (for business logic consumers). These helpers SHALL be used by the status transition validation logic and SHALL be the single source of truth for dependency queries — the AI domain's `pending_actions.py` and tools SHALL call these helpers instead of reimplementing dependency checks.

#### Scenario: Query dependencies for a task
- **WHEN** `get_task_dependencies(task_id)` is called for a task with 3 prerequisites
- **THEN** the function returns the 3 prerequisite task records

#### Scenario: Check met dependencies
- **WHEN** `are_dependencies_met(task_id)` is called for a task whose 2 dependencies both have status `done`
- **THEN** the function returns `true`

#### Scenario: Check unmet dependencies
- **WHEN** `are_dependencies_met(task_id)` is called for a task whose 1 of 2 dependencies has status `in_progress`
- **THEN** the function returns `false`

#### Scenario: AI domain uses boards dependency helpers
- **WHEN** `ai/pending_actions.py` needs to check if a task's dependencies are met before confirming a status change
- **THEN** it calls `boards/task_service.are_dependencies_met()` instead of querying the database directly
