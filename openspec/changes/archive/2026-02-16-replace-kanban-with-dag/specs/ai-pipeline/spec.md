## MODIFIED Requirements

### Requirement: Board Generation Node
The system SHALL implement a LangGraph node that generates a complete board structure from goal context. The node SHALL receive: the goal's original text, classification output (domain, complexity, dimensions), and all Q&A pairs (initial questions + answers, follow-up questions + answers if any). The output SHALL conform to a Pydantic schema (`BoardGenerationOutput`) containing: `board_title` (string), and `tasks` (array of objects each with `id` (string, e.g., "t1"), `title`, `description`, `due_date` (nullable ISO date string), `priority` (nullable, one of "low"/"medium"/"high"), `estimated_minutes` (nullable integer), `depends_on` (array of task id strings, e.g., ["t1", "t3"]), and `is_goal_node` (boolean, default false)). The board generation prompt SHALL be stored as a separate module in `prompts/generate_board.py`. The output MUST form a valid DAG — no circular dependencies. Tasks with an empty `depends_on` array are root tasks that can be started immediately. Exactly one task MUST have `is_goal_node: true` — this is the final goal completion task that represents the user's original goal and depends on all leaf tasks. The AI SHALL create convergence nodes where multiple parallel paths merge into a single task that requires all upstream tasks to be completed.

#### Scenario: Board generated for a relocation goal with dependencies
- **WHEN** the board generation node receives a relocation goal with classification domain "relocation", complexity 4, and answers covering timeline, budget, housing, and logistics
- **THEN** the output contains 10-20 tasks with dependency edges forming a DAG. Root tasks like "Research neighborhoods" and "Check visa requirements" have empty `depends_on`. Dependent tasks like "Sign lease" depend on "Research neighborhoods". The final task has `is_goal_node: true` with a title like "Complete: Relocate to Lisbon" and depends on all leaf tasks.

#### Scenario: Parallel paths converge into shared milestones
- **WHEN** the board generation node produces output for a goal with multiple independent dimensions (e.g., housing and employment for a relocation)
- **THEN** the output contains parallel task chains that converge at shared milestone tasks (e.g., "Finalize relocation timeline" depends on both the housing and employment chains) before ultimately feeding into the final goal node

#### Scenario: Final goal node is the single sink of the DAG
- **WHEN** the board generation node produces output
- **THEN** exactly one task has `is_goal_node: true`, it has no dependents (nothing depends on it), and all other leaf tasks (tasks with no dependents) are dependencies of the goal node

#### Scenario: Progressive metadata applied per-task
- **WHEN** the board generation node produces tasks
- **THEN** each task independently includes or omits `due_date`, `priority`, and `estimated_minutes` based on whether that metadata is relevant to the specific task and goal type

#### Scenario: Task count within bounds
- **WHEN** the board generation node produces output
- **THEN** the total task count is between 5 and 30

#### Scenario: No circular dependencies in output
- **WHEN** the board generation node produces output
- **THEN** performing a topological sort on the task dependency graph succeeds (no cycles detected)

### Requirement: Board Generation Prompt Module
The board generation system prompt SHALL be stored in `app/domains/ai/prompts/generate_board.py` as a separate module. The prompt SHALL instruct the AI to: design tasks as concrete, actionable steps for achieving the goal; define dependency edges between tasks where one task logically must complete before another can begin; create parallel task paths for independent work streams; create convergence nodes where parallel paths merge into a single milestone task; create exactly one final goal node (with `is_goal_node: true`) that represents the user's original goal, depends on all leaf tasks, and serves as the single sink of the DAG; assign progressive metadata only when it adds planning value; and ensure the dependency graph forms a valid DAG with no cycles. The prompt SHALL NOT be inlined in node logic or service functions.

#### Scenario: Board generation prompt stored separately
- **WHEN** the generate_board node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py`

### Requirement: Board Generation AI Service Function
The AI service layer SHALL expose an async function `generate_board(goal)` that accepts a Goal object (with populated `ai_context`), extracts the necessary context (original input, classification, questions, answers), invokes the board generation node with structured output enforcement, validates the output forms a valid DAG (topological sort), and returns the validated `BoardGenerationOutput`. This function SHALL hide LangGraph internals from callers. The function SHALL reuse the existing retry logic (up to 3 retries on Pydantic validation failure). If the AI produces a cyclic dependency graph, the function SHALL retry (counting toward the 3-retry limit).

#### Scenario: Service function called with answered goal
- **WHEN** `generate_board` is called with a goal in `answered` status that has classification and Q&A in `ai_context`
- **THEN** the function returns a `BoardGenerationOutput` containing the generated task list with dependency edges

#### Scenario: Service function raises on AI failure
- **WHEN** `generate_board` is called and the AI fails after all retry attempts
- **THEN** the function raises an `AIOutputError`

#### Scenario: Service function retries on cyclic output
- **WHEN** `generate_board` is called and the AI produces a cyclic dependency graph
- **THEN** the function retries the generation (counting toward the 3-retry limit)
