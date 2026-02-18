## ADDED Requirements

### Requirement: Nesting Depth Validation
The system SHALL provide a validation function that enforces the 1-level sub-board nesting limit. Before creating a sub-board for a task, the system SHALL check that the task's board does NOT have a `parent_task_id` set (i.e., the task must belong to a root-level board). This validation SHALL be located in `app/domains/boards/dag_utils.py` and be callable from the sub-board generation service. The function SHALL accept a board and return whether sub-board creation is allowed for tasks on that board.

#### Scenario: Sub-board allowed for root board task
- **WHEN** the nesting validation is called for a task whose board has `parent_task_id = null`
- **THEN** the validation passes (sub-board creation is allowed)

#### Scenario: Sub-board rejected for sub-board task
- **WHEN** the nesting validation is called for a task whose board has `parent_task_id` set to a non-null value
- **THEN** the validation fails with a `NestingDepthError` indicating sub-boards cannot be nested beyond 1 level

### Requirement: Sub-Board Completion Detection
The system SHALL detect when a sub-board's goal node is completed and propagate the completion to the parent task. The detection SHALL be integrated into the existing task status update flow in `app/domains/boards/task_service.py`. After a task status transitions to `done`, if the task has `is_goal_node: true`, the service SHALL check if the task's board has a `parent_task_id`. If so, the parent task SHALL be transitioned to `done`. The parent task status transition SHALL bypass the normal `in_progress` prerequisite check (since the sub-board completion proves the work is done). This propagation SHALL use the existing board service and task service infrastructure.

#### Scenario: Goal node completion triggers parent task completion
- **WHEN** a task with `is_goal_node: true` on a sub-board transitions to `done`
- **AND** the sub-board has `parent_task_id` pointing to task P on the root board
- **THEN** task P is automatically transitioned to `done`

#### Scenario: Regular task completion does not propagate
- **WHEN** a regular task (not a goal node) on a sub-board transitions to `done`
- **THEN** no propagation to the parent task occurs

#### Scenario: Goal node on root board does not propagate
- **WHEN** the goal node on a root board (no `parent_task_id`) transitions to `done`
- **THEN** no parent task propagation occurs (existing board completion behavior applies)

#### Scenario: Parent task done unlocks dependents on root board
- **WHEN** task P on the root board is auto-completed via sub-board propagation
- **AND** task Q on the root board depends only on task P
- **THEN** task Q becomes unlocked
