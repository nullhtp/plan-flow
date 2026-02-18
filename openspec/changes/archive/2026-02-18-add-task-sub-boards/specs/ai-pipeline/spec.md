## ADDED Requirements

### Requirement: Sub-Board Question Generation Node
The system SHALL implement an AI service function `generate_sub_board_questions(task_title: str, task_description: str, board_title: str, goal_context: str, language: str, user_context: str | None = None, memory_context: str | None = None) -> list[QuestionSchema]` that generates 2-4 focused questions for decomposing a task into a sub-board. The function SHALL call the LLM with structured output using a dedicated sub-board question prompt. Each question SHALL conform to the same schema as goal questions (`id`, `text`, `type`, `options`, `rationale`, `required`). Question IDs SHALL be prefixed with "sbq" (e.g., "sbq1", "sbq2"). The function SHALL NOT use LangGraph — it is a single structured output LLM call. All generated content SHALL be in the specified language.

#### Scenario: Questions generated for a complex task
- **WHEN** `generate_sub_board_questions` is called with task title "Find and secure housing in Lisbon", task description, board title "Relocation to Lisbon", and goal context
- **THEN** the function returns 2-4 questions focused on housing decomposition (e.g., "What type of housing?", "Budget range?", "Timeline for securing housing?")

#### Scenario: Question count within bounds
- **WHEN** `generate_sub_board_questions` produces output
- **THEN** the number of questions is between 2 and 4 inclusive

#### Scenario: Questions in detected language
- **WHEN** the language parameter is "ru"
- **THEN** all question texts, options, and rationales are in Russian

#### Scenario: Questions informed by user context
- **WHEN** user_context includes location "Berlin, Germany"
- **THEN** the questions MAY reference the user's context where relevant

### Requirement: Sub-Board Question Prompt Module
The system SHALL store the sub-board question generation prompt in `app/domains/ai/prompts/sub_board_questions.py` as a separate module. The prompt SHALL instruct the AI to: analyze the parent task's title and description to understand what needs to be decomposed; consider the broader goal context; generate 2-4 questions that help understand HOW the user wants to approach this specific task; use appropriate field types (text, select, multiselect, number); and produce all content in the specified language. The prompt SHALL emphasize brevity and focus — these are task-specific decomposition questions, not goal-level exploration questions.

#### Scenario: Sub-board question prompt stored as module
- **WHEN** the sub-board question generation needs its prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/sub_board_questions.py`

### Requirement: Sub-Board Skeleton Generation
The system SHALL support generating sub-board skeletons via the existing board generation infrastructure with adjusted parameters. The sub-board skeleton generation SHALL receive: the parent task's title and description, the root board's title and goal context (original input, classification, Q&A pairs), the sub-board question answers, the detected language, user_context, and memory_context. The skeleton output SHALL conform to the same `BoardSkeletonOutput` Pydantic schema but with a task count range of 3-15 (instead of 5-30 for root boards). The generated board title SHALL reflect the parent task (e.g., "Housing Plan" for a "Find and secure housing" parent task). The system SHALL reuse the existing `generate_board_stream` infrastructure, adding a `parent_task_id` parameter to distinguish sub-board generation from root board generation. The sub-board skeleton prompt SHALL be a variant of the board generation prompt, stored in `app/domains/ai/prompts/generate_board.py` as a separate function or constant.

#### Scenario: Sub-board skeleton generated with fewer tasks
- **WHEN** the sub-board skeleton generation is called for a task "Find and secure housing in Lisbon"
- **THEN** the output contains 3-15 tasks with dependency edges forming a valid DAG, a single goal node, and a board title reflecting the parent task

#### Scenario: Sub-board skeleton reuses enrichment pipeline
- **WHEN** a sub-board skeleton is generated
- **THEN** the same parallel enrichment pipeline (with concurrency limits) is used for task enrichment and subtask action generation

#### Scenario: Sub-board skeleton uses parent goal context
- **WHEN** a sub-board is generated for a task on a board whose goal was "Relocate from Berlin to Lisbon"
- **THEN** the skeleton prompt includes the root goal context so the AI understands the broader plan

#### Scenario: Sub-board skeleton prompt stored in generate_board module
- **WHEN** the sub-board skeleton generation needs its prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py` (as a sub-board-specific variant)

### Requirement: Sub-Board AI Service Integration
The AI service layer SHALL expose an async generator function `generate_sub_board_stream(task: Task, board: Board, answers: list[dict], db_session)` that orchestrates sub-board generation. The function SHALL: (1) resolve the root board's goal context (original input, classification, Q&A, language, user_meta) by tracing from the board to the goal, (2) retrieve relevant memories for the user, (3) invoke the sub-board skeleton generation with the adjusted task count range (3-15), (4) yield SSE events in the same format as `generate_board_stream` (skeleton_ready, task_enriched, generation_complete, generation_error), (5) persist the sub-board via the board service with `parent_task_id` set, (6) delete existing subtasks on the parent task before creating the sub-board, (7) auto-transition the parent task to `in_progress` if applicable. The function SHALL reuse existing enrichment and persistence infrastructure.

#### Scenario: Sub-board generation streams events
- **WHEN** `generate_sub_board_stream` is called with a task and answers
- **THEN** it yields `skeleton_ready`, then multiple `task_enriched` events, then `generation_complete` with the sub-board ID

#### Scenario: Sub-board generation resolves root goal context
- **WHEN** `generate_sub_board_stream` is called for a task on a root board
- **THEN** the function resolves the root board's goal and extracts the full AI context (classification, Q&A, language, user_meta)

#### Scenario: Sub-board generation deletes existing subtasks
- **WHEN** `generate_sub_board_stream` is called for a task with 5 existing subtasks
- **THEN** the 5 subtasks are deleted before the sub-board is created

#### Scenario: Sub-board generation auto-starts parent task
- **WHEN** the parent task has status `not_started` and all dependencies are met
- **THEN** the parent task transitions to `in_progress` during sub-board generation
