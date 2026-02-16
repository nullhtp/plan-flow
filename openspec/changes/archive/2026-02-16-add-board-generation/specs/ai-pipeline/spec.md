## ADDED Requirements

### Requirement: Board Generation Node
The system SHALL implement a LangGraph node that generates a complete board structure from goal context. The node SHALL receive: the goal's original text, classification output (domain, complexity, dimensions), and all Q&A pairs (initial questions + answers, follow-up questions + answers if any). The output SHALL conform to a Pydantic schema (`BoardGenerationOutput`) containing: `board_title` (string), and `columns` (array of objects each with `title`, `description`, `position`, and nested `tasks` array). Each task SHALL contain: `title`, `description`, `position`, `due_date` (nullable ISO date string), `priority` (nullable, one of "low"/"medium"/"high"), and `estimated_minutes` (nullable integer). The board generation prompt SHALL be stored as a separate module in `prompts/generate_board.py`.

#### Scenario: Board generated for a relocation goal
- **WHEN** the board generation node receives a relocation goal with classification domain "relocation", complexity 4, and answers covering timeline, budget, housing, and logistics
- **THEN** the output contains 4-6 columns with domain-specific titles (e.g., "Research", "Documentation", "Logistics", "Settlement") and each column contains 2-6 concrete, actionable tasks relevant to the relocation context

#### Scenario: Columns reflect goal-specific workflow phases
- **WHEN** the board generation node produces output for any goal
- **THEN** column titles represent the goal's natural workflow phases, NOT generic kanban labels like "To Do", "In Progress", "Done"

#### Scenario: Progressive metadata applied per-task
- **WHEN** the board generation node produces tasks
- **THEN** each task independently includes or omits `due_date`, `priority`, and `estimated_minutes` based on whether that metadata is relevant to the specific task and goal type

#### Scenario: Column count guided by complexity
- **WHEN** the board generation node receives a goal with complexity score 1-2
- **THEN** the output contains 3-4 columns
- **WHEN** the board generation node receives a goal with complexity score 4-5
- **THEN** the output contains 5-7 columns

#### Scenario: Task count within bounds
- **WHEN** the board generation node produces output
- **THEN** each column contains 2-6 tasks and the total task count across all columns does not exceed 30

### Requirement: Board Generation Prompt Module
The board generation system prompt SHALL be stored in `app/domains/ai/prompts/generate_board.py` as a separate module. The prompt SHALL instruct the AI to: design columns as workflow phases specific to the goal domain, create concrete and actionable tasks, assign progressive metadata only when it adds planning value, order columns from earliest to latest phase, and order tasks within columns by suggested execution order. The prompt SHALL NOT be inlined in node logic or service functions.

#### Scenario: Board generation prompt stored separately
- **WHEN** the generate_board node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py`

### Requirement: Board Generation AI Service Function
The AI service layer SHALL expose an async function `generate_board(goal)` that accepts a Goal object (with populated `ai_context`), extracts the necessary context (original input, classification, questions, answers), invokes the board generation node with structured output enforcement, and returns the validated `BoardGenerationOutput`. This function SHALL hide LangGraph internals from callers. The function SHALL reuse the existing retry logic (up to 3 retries on Pydantic validation failure).

#### Scenario: Service function called with answered goal
- **WHEN** `generate_board` is called with a goal in `answered` status that has classification and Q&A in `ai_context`
- **THEN** the function returns a `BoardGenerationOutput` containing the generated board structure

#### Scenario: Service function raises on AI failure
- **WHEN** `generate_board` is called and the AI fails after all retry attempts
- **THEN** the function raises an `AIOutputError`

## MODIFIED Requirements

### Requirement: LangGraph Pipeline Definition
The system SHALL define a LangGraph `StateGraph` for the goal understanding pipeline with nodes `classify`, `generate_questions`, and `generate_board`. The graph SHALL use a `GoalPipelineState` TypedDict as its state schema. The `GoalPipelineState` SHALL include a `board_generation` field (nullable `BoardGenerationOutput`) for storing the board generation result. The pipeline SHALL be defined in `app/domains/ai/pipeline.py` and individual nodes in `app/domains/ai/nodes/`. The AI service layer (`app/domains/ai/service.py`) SHALL expose simple async functions (`classify_goal`, `generate_questions`, `generate_follow_up_questions`, `generate_board`) that hide LangGraph internals from callers.

#### Scenario: Pipeline executes classification then question generation
- **WHEN** the AI service's `classify_goal` function is called with raw goal text
- **THEN** the LangGraph pipeline executes the classify node followed by the generate_questions node (if not rejected) and returns the combined result

#### Scenario: Pipeline short-circuits on rejection
- **WHEN** the classify node produces a confidence score below the rejection threshold
- **THEN** the pipeline does not execute the generate_questions node and returns the rejection result

#### Scenario: Board generation invoked as separate entry point
- **WHEN** the AI service's `generate_board` function is called with a goal
- **THEN** only the generate_board node executes (not the full classify+questions pipeline)

### Requirement: System Prompts as Modules
System prompts for classification, question generation, and board generation SHALL be stored as separate Python modules in `app/domains/ai/prompts/`. Each module SHALL export a string constant or function that returns the prompt. Prompts SHALL NOT be inlined in node logic or service functions.

#### Scenario: Classification prompt stored separately
- **WHEN** the classify node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/classify.py`

#### Scenario: Question generation prompt stored separately
- **WHEN** the generate_questions node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/questions.py`

#### Scenario: Board generation prompt stored separately
- **WHEN** the generate_board node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py`
