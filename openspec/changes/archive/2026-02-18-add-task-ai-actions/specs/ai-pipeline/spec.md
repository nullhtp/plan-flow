## ADDED Requirements

### Requirement: Action Suggestion Generation
The system SHALL provide an async function `generate_action_suggestions(task_context: str, model: str | None = None) -> list[ActionSuggestion]` in the AI service layer. The function SHALL call the LLM with structured output using the action suggestion prompt and task context string. The function SHALL use the `AI_ACTION_SUGGEST_MODEL` (falling back to `AI_CHAT_MODEL`, then `AI_DEFAULT_MODEL`). The function SHALL return 2–4 `ActionSuggestion` objects. The function SHALL NOT use LangGraph or tools — it is a single structured output LLM call.

#### Scenario: Generate suggestions for a planning task
- **WHEN** `generate_action_suggestions` is called with context for a task titled "Plan team offsite"
- **THEN** it returns 2–4 ActionSuggestion objects with contextual labels and prompts

#### Scenario: Suggestions respect task language
- **WHEN** the task context is in German
- **THEN** the returned suggestions have German labels and prompts

### Requirement: Action Suggestion Prompt Module
The system SHALL store the action suggestion system prompt in `app/domains/ai/prompts/action_suggestions.py`. The prompt SHALL instruct the LLM to: analyze the task's title, description, status, subtasks, and relationships; generate 2–4 diverse action suggestions; use the same language as the task content; produce labels that are short and action-oriented (verb-led); produce prompts that are clear instructions for the task chat AI; and vary the icon categories across suggestions.

#### Scenario: Action suggestion prompt stored as module
- **WHEN** the action suggestion feature loads its prompt
- **THEN** the prompt is imported from `app/domains/ai/prompts/action_suggestions.py`

## MODIFIED Requirements

### Requirement: Tool-Aware Chat System Prompts
The system SHALL maintain separate system prompt modules for task chat (`app/domains/ai/prompts/chat.py`) and board chat (`app/domains/ai/prompts/board_chat.py`). The task chat prompt SHALL instruct the AI on available tools (retrieval, mutations, web search, save_artifact), establish its role as a helpful task assistant, and guide appropriate tool usage. The prompt SHALL include instructions to use the `save_artifact` tool when generating substantial, reusable content such as agreements, plans, research summaries, or comparisons — rather than including long content only in the chat message. The board chat prompt SHALL additionally cover structural tools (add/remove tasks and dependencies, split tasks).

#### Scenario: Task chat prompt includes tool instructions
- **WHEN** a task chat graph is compiled
- **THEN** the system prompt from `prompts/chat.py` is used, including instructions for all available tools

#### Scenario: Task chat prompt includes artifact instructions
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes instructions to use `save_artifact` for substantial generated content

#### Scenario: Board chat prompt includes structural tool instructions
- **WHEN** a board chat graph is compiled
- **THEN** the system prompt from `prompts/board_chat.py` is used, including instructions for structural tools
