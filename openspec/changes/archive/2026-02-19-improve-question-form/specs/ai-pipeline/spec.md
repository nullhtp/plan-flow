## MODIFIED Requirements

### Requirement: Question Generation Node
The system SHALL implement a LangGraph node that generates 3-7 structured questions based on the classification output. Each question SHALL conform to a Pydantic schema containing: `id` (unique string, e.g., "q1"), `text` (the question), `type` (one of: "text", "select", "multiselect", "number"), `options` (list of 3-6 strings, REQUIRED for all question types), `rationale` (string explaining why this question matters for planning), `required` (boolean, default true), and `allow_other` (boolean, default true — indicates whether the UI should render a free-text "Other" input alongside the options). The `options` field SHALL always be a non-empty list with at least 3 items regardless of question type. For `text` type questions, options SHALL be AI-suggested likely answers. For `number` type questions, options SHALL be meaningful human-readable ranges (e.g., "$1k-5k", "2-3 months", "1-2 rooms"). For `select` and `multiselect` types, options SHALL be relevant choices as before. The question generation prompt SHALL be stored as a separate module in `prompts/questions.py`. When `user_meta` is available in the goal's `ai_context`, the formatted meta context SHALL be appended to the user prompt to enable location-aware, timezone-aware, and device-aware question generation. When memory context is available, the formatted memory block SHALL be appended to the user prompt after the user meta block. The AI SHOULD use memories to avoid asking questions whose answers are already known (e.g., if memory contains "Budget preference: under $5000", the AI MAY skip or pre-fill a budget question).

#### Scenario: Questions generated for a relocation goal
- **WHEN** the question generation node receives a classification with domain "relocation" and dimensions ["timeline", "budget", "housing", "logistics"]
- **THEN** the output contains 3-7 questions covering the identified dimensions, each with 3-6 selectable options (e.g., a budget question with options ["Under $5,000", "$5,000-$15,000", "$15,000-$30,000", "$30,000+"], a timeline question with options ["1-2 months", "3-4 months", "5-6 months", "6+ months"])

#### Scenario: Each question includes rationale
- **WHEN** questions are generated for any goal
- **THEN** every question in the output has a non-empty `rationale` field explaining its relevance

#### Scenario: Question count within bounds
- **WHEN** the question generation node produces output
- **THEN** the number of questions is between 3 and 7 inclusive

#### Scenario: All questions have non-empty options
- **WHEN** the question generation node produces output
- **THEN** every question has an `options` list with at least 3 items, regardless of question type

#### Scenario: Text question has suggested answer options
- **WHEN** a question has type "text" (e.g., "What is your main motivation for this move?")
- **THEN** the options list contains 3-6 AI-suggested likely answers (e.g., ["Career opportunity", "Better quality of life", "Family reasons", "Adventure / new experience"])

#### Scenario: Number question has range-based options
- **WHEN** a question has type "number" (e.g., "What is your monthly budget?")
- **THEN** the options list contains 3-6 human-readable ranges (e.g., ["Under $1,000", "$1,000-$2,000", "$2,000-$3,000", "$3,000+"])

#### Scenario: Questions informed by user location
- **WHEN** the question generation node receives a goal with `user_meta.location = { city: "Berlin", country: "Germany" }` and classification domain "relocation"
- **THEN** the generated questions MAY reference the user's current location (e.g., asking about moving FROM Berlin specifically)

#### Scenario: Questions generated without user meta (backward compatible)
- **WHEN** the question generation node receives a goal without `user_meta`
- **THEN** questions are generated normally without location or timezone context

#### Scenario: Questions informed by user memories
- **WHEN** the question generation node receives memory context containing "Budget preference: under $5000" and the classification dimensions include "budget"
- **THEN** the AI MAY skip the budget question or generate a confirmation question instead (e.g., "Last time your budget was under $5000. Is that still the case?")

#### Scenario: Questions generated without memories (backward compatible)
- **WHEN** the question generation node receives no memory context (empty string)
- **THEN** questions are generated normally as if no memories exist

### Requirement: Sub-Board Question Generation Node
The system SHALL implement an AI service function `generate_sub_board_questions(task_title: str, task_description: str, board_title: str, goal_context: str, language: str, user_context: str | None = None, memory_context: str | None = None) -> list[QuestionSchema]` that generates 2-4 focused questions for decomposing a task into a sub-board. The function SHALL call the LLM with structured output using a dedicated sub-board question prompt. Each question SHALL conform to the same schema as goal questions (`id`, `text`, `type`, `options`, `rationale`, `required`, `allow_other`). The `options` field SHALL always be a non-empty list with at least 3 items regardless of question type. Question IDs SHALL be prefixed with "sbq" (e.g., "sbq1", "sbq2"). The function SHALL NOT use LangGraph — it is a single structured output LLM call. All generated content SHALL be in the specified language.

#### Scenario: Questions generated for a complex task
- **WHEN** `generate_sub_board_questions` is called with task title "Find and secure housing in Lisbon", task description, board title "Relocation to Lisbon", and goal context
- **THEN** the function returns 2-4 questions focused on housing decomposition, each with 3-6 selectable options (e.g., "What type of housing?" with options ["Studio apartment", "1-bedroom apartment", "Shared flat", "House"])

#### Scenario: Question count within bounds
- **WHEN** `generate_sub_board_questions` produces output
- **THEN** the number of questions is between 2 and 4 inclusive

#### Scenario: All sub-board questions have non-empty options
- **WHEN** `generate_sub_board_questions` produces output
- **THEN** every question has an `options` list with at least 3 items, regardless of question type

#### Scenario: Questions in detected language
- **WHEN** the language parameter is "ru"
- **THEN** all question texts, options, and rationales are in Russian

#### Scenario: Questions informed by user context
- **WHEN** user_context includes location "Berlin, Germany"
- **THEN** the questions MAY reference the user's context where relevant
