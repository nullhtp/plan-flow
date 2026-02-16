# ai-pipeline Specification

## Purpose
TBD - created by archiving change add-goal-understanding. Update Purpose after archive.
## Requirements
### Requirement: OpenRouter LLM Client
The system SHALL integrate with OpenRouter (`https://openrouter.ai/api/v1`) via LangChain's `ChatOpenAI` class configured with the OpenRouter base URL. The API key and default model SHALL be read from environment variables (`OPENROUTER_API_KEY`, `AI_DEFAULT_MODEL`). The default model SHALL be `openai/gpt-5.2`. Individual LLM calls SHALL have a 20-second timeout.

#### Scenario: LLM client configured from environment
- **WHEN** the application starts
- **THEN** the LLM client is configured with the OpenRouter API key and model from environment variables

#### Scenario: LLM call timeout
- **WHEN** an LLM call does not respond within 20 seconds
- **THEN** the call is cancelled and an appropriate error is raised

#### Scenario: Missing API key
- **WHEN** the `OPENROUTER_API_KEY` environment variable is not set
- **THEN** the application SHALL fail to start with a clear error message indicating the missing configuration

### Requirement: Goal Classification Node
The system SHALL implement a LangGraph node that classifies a goal from raw text input. The classification output SHALL conform to a Pydantic schema containing: `domain` (string — e.g., "relocation", "learning", "product-launch"), `complexity` (integer 1-5), `confidence` (float 0.0-1.0), `dimensions` (list of strings — key aspects to explore), and `suggested_title` (a clean, concise title derived from the raw input). The classification prompt SHALL be stored as a separate module in `prompts/classify.py`.

#### Scenario: Clear goal classified with high confidence
- **WHEN** the classification node receives "Move from Berlin to Lisbon within 3 months"
- **THEN** the output includes a domain (e.g., "relocation"), complexity >= 3, confidence >= 0.7, relevant dimensions (e.g., ["timeline", "budget", "housing", "logistics"]), and a suggested title (e.g., "Relocate from Berlin to Lisbon")

#### Scenario: Vague goal classified with low confidence
- **WHEN** the classification node receives "be happier"
- **THEN** the output includes confidence < 0.3 and the `dimensions` list is sparse or generic

### Requirement: Confidence-Based Goal Rejection
The system SHALL reject goals whose classification confidence score falls below a configurable threshold (default: 0.3). When a goal is rejected, the classification node SHALL also output a `rejection_reason` (string explaining why the goal is too vague) and `refinement_suggestions` (list of 2-3 concrete, actionable alternative goal descriptions). The rejection output is part of the classification response, not a separate LLM call.

#### Scenario: Goal below confidence threshold is rejected
- **WHEN** the classification node produces a confidence score of 0.15 for "do stuff"
- **THEN** the pipeline marks the goal as rejected, includes a `rejection_reason` (e.g., "This goal is too vague to generate a meaningful plan"), and provides `refinement_suggestions` (e.g., ["Organize my home office in 2 weekends", "Learn basic cooking skills in 1 month"])

#### Scenario: Goal above confidence threshold proceeds to question generation
- **WHEN** the classification node produces a confidence score of 0.8 for "Launch an MVP for my SaaS product"
- **THEN** the pipeline proceeds to the question generation node without rejection

### Requirement: Question Generation Node
The system SHALL implement a LangGraph node that generates 3-7 structured questions based on the classification output. Each question SHALL conform to a Pydantic schema containing: `id` (unique string, e.g., "q1"), `text` (the question), `type` (one of: "text", "select", "multiselect", "number"), `options` (list of strings, required for select/multiselect, null for text/number), `rationale` (string explaining why this question matters for planning), and `required` (boolean, default true). The question generation prompt SHALL be stored as a separate module in `prompts/questions.py`.

#### Scenario: Questions generated for a relocation goal
- **WHEN** the question generation node receives a classification with domain "relocation" and dimensions ["timeline", "budget", "housing", "logistics"]
- **THEN** the output contains 3-7 questions covering the identified dimensions, each with appropriate field types (e.g., a budget question might be type "select" with predefined ranges, a timeline question might be type "text")

#### Scenario: Each question includes rationale
- **WHEN** questions are generated for any goal
- **THEN** every question in the output has a non-empty `rationale` field explaining its relevance

#### Scenario: Question count within bounds
- **WHEN** the question generation node produces output
- **THEN** the number of questions is between 3 and 7 inclusive

### Requirement: Adaptive Follow-up Question Generation
The system SHALL support generating up to 1 round of follow-up questions after the user submits initial answers. The follow-up generation reuses the question generation node with additional context: the original classification, the initial questions, and the user's answers. The AI SHALL decide whether follow-ups are needed — it MAY return an empty list if the initial answers are sufficient. Follow-up questions SHALL have IDs prefixed with "fq" (e.g., "fq1") to distinguish them from initial questions.

#### Scenario: Follow-up questions generated when answers reveal gaps
- **WHEN** a user answers initial questions for a relocation goal and indicates they have pets
- **AND** no initial question addressed pet relocation
- **THEN** the follow-up generation MAY produce additional questions about pet transport requirements

#### Scenario: No follow-ups when answers are comprehensive
- **WHEN** a user provides thorough answers to all initial questions
- **THEN** the follow-up generation returns an empty question list

#### Scenario: Maximum one follow-up round enforced
- **WHEN** the system has already generated one round of follow-up questions
- **AND** the user submits follow-up answers
- **THEN** no additional follow-up generation occurs regardless of answer content

### Requirement: Structured Output Enforcement
All LLM calls in the pipeline SHALL use LangChain's `.with_structured_output()` to enforce JSON schema compliance via the corresponding Pydantic models. When the LLM returns output that fails Pydantic validation, the system SHALL automatically retry the same prompt up to 3 times. If all retries fail, the system SHALL raise a structured error that the API layer can translate into a user-friendly error response.

#### Scenario: Valid structured output on first attempt
- **WHEN** the LLM returns valid JSON matching the Pydantic schema
- **THEN** the output is parsed into the Pydantic model and returned without retries

#### Scenario: Malformed output triggers retry
- **WHEN** the LLM returns JSON that fails Pydantic validation
- **THEN** the system retries the same prompt, up to 3 total attempts

#### Scenario: All retries exhausted
- **WHEN** all 3 retry attempts produce invalid output
- **THEN** the system raises an `AIOutputError` with details about the validation failure

### Requirement: LangGraph Pipeline Definition
The system SHALL define a LangGraph `StateGraph` for the goal understanding pipeline with nodes `classify` and `generate_questions`. The graph SHALL use a `GoalPipelineState` TypedDict as its state schema. The pipeline SHALL be defined in `app/domains/ai/pipeline.py` and individual nodes in `app/domains/ai/nodes/`. The AI service layer (`app/domains/ai/service.py`) SHALL expose simple async functions (`classify_goal`, `generate_questions`, `generate_follow_up_questions`) that hide LangGraph internals from callers.

#### Scenario: Pipeline executes classification then question generation
- **WHEN** the AI service's `classify_goal` function is called with raw goal text
- **THEN** the LangGraph pipeline executes the classify node followed by the generate_questions node (if not rejected) and returns the combined result

#### Scenario: Pipeline short-circuits on rejection
- **WHEN** the classify node produces a confidence score below the rejection threshold
- **THEN** the pipeline does not execute the generate_questions node and returns the rejection result

### Requirement: System Prompts as Modules
System prompts for classification and question generation SHALL be stored as separate Python modules in `app/domains/ai/prompts/`. Each module SHALL export a string constant or function that returns the prompt. Prompts SHALL NOT be inlined in node logic or service functions.

#### Scenario: Classification prompt stored separately
- **WHEN** the classify node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/classify.py`

#### Scenario: Question generation prompt stored separately
- **WHEN** the generate_questions node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/questions.py`

