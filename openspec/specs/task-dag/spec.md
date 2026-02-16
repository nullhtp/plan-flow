# task-dag Specification

## Purpose
DAG validation and structural integrity for task dependency graphs. Provides cycle detection (Kahn's algorithm), goal node validation (single sink), and query helpers for dependency traversal and lock status computation.
## Requirements
### Requirement: DAG Validation Utility
The system SHALL provide a utility function that validates a set of tasks and dependency edges form a valid directed acyclic graph. The utility SHALL use topological sort (Kahn's algorithm) to detect cycles. The utility SHALL be located in `app/domains/boards/dag_utils.py` and be callable from both the AI service (to validate AI output) and the board service (to validate persistence input).

#### Scenario: Valid DAG passes validation
- **WHEN** the utility receives 10 tasks with 15 edges forming a valid DAG
- **THEN** the utility returns success and the topologically sorted task order

#### Scenario: Cyclic graph fails validation
- **WHEN** the utility receives tasks where A depends on B and B depends on A
- **THEN** the utility raises a `CyclicDependencyError` identifying the involved tasks

#### Scenario: Self-dependency fails validation
- **WHEN** the utility receives a task that depends on itself
- **THEN** the utility raises a `CyclicDependencyError`

### Requirement: Task Dependency Query Helpers
The system SHALL provide query helper functions in the board service to efficiently retrieve dependency information: `get_task_dependencies(task_id)` returning all prerequisite tasks, `get_task_dependents(task_id)` returning all tasks that depend on the given task, and `are_dependencies_met(task_id)` returning a boolean indicating whether all prerequisite tasks have status `done`. These helpers SHALL be used by the status transition validation logic.

#### Scenario: Query dependencies for a task
- **WHEN** `get_task_dependencies(task_id)` is called for a task with 3 prerequisites
- **THEN** the function returns the 3 prerequisite task records

#### Scenario: Check met dependencies
- **WHEN** `are_dependencies_met(task_id)` is called for a task whose 2 dependencies both have status `done`
- **THEN** the function returns `true`

#### Scenario: Check unmet dependencies
- **WHEN** `are_dependencies_met(task_id)` is called for a task whose 1 of 2 dependencies has status `in_progress`
- **THEN** the function returns `false`

### Requirement: Board Completion Detection
The system SHALL detect board completion by checking whether the goal node task (the task with `is_goal_node: true`) has status `done`. The GET board endpoint SHALL include a `is_completed` boolean field on the board response. The frontend uses this field to trigger the celebration animation. Since the goal node depends on all leaf tasks, its completion inherently means the entire plan is finished.

#### Scenario: Board completed when goal node is done
- **WHEN** a board's goal node task has status `done`
- **THEN** `is_completed` is `true` in the board response

#### Scenario: Board not completed when goal node is not done
- **WHEN** a board has 15 tasks, 14 have status `done`, but the goal node has status `in_progress`
- **THEN** `is_completed` is `false` in the board response

#### Scenario: Board not completed when upstream tasks remain
- **WHEN** a board has 15 tasks and 10 have status `done` but the goal node is still `not_started` (locked by unfinished prerequisites)
- **THEN** `is_completed` is `false` in the board response

### Requirement: DAG Structure Validation
The system SHALL validate that every generated board has a valid DAG structure with exactly one goal node. The validation SHALL check: (1) exactly one task has `is_goal_node: true`, (2) the goal node has no dependents (nothing depends on it — it is the single sink), (3) all other leaf tasks (tasks with no dependents except the goal node) are direct dependencies of the goal node. This validation SHALL run during board persistence before committing to the database.

#### Scenario: Valid DAG with single goal node passes
- **WHEN** the validator receives a board with 15 tasks, one goal node, and all leaf tasks feeding into the goal node
- **THEN** the validation passes

#### Scenario: Missing goal node fails validation
- **WHEN** the validator receives a board with no task marked as `is_goal_node: true`
- **THEN** the validation fails with an error indicating a goal node is required

#### Scenario: Multiple goal nodes fails validation
- **WHEN** the validator receives a board with 2 tasks marked as `is_goal_node: true`
- **THEN** the validation fails with an error indicating only one goal node is allowed

#### Scenario: Goal node with dependents fails validation
- **WHEN** the validator receives a board where the goal node has a dependent task
- **THEN** the validation fails with an error indicating the goal node must be the final task

