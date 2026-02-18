## ADDED Requirements

### Requirement: Action Suggestion Endpoint
The system SHALL provide a `POST /api/tasks/{task_id}/actions/suggest` endpoint that returns 2–4 contextual AI action suggestions for the specified task. The endpoint SHALL validate task ownership (task → board → goal → user). The endpoint SHALL build a context string including the task's title, description, status, subtask titles and completion states, and the titles and statuses of immediate dependency and dependent tasks. The endpoint SHALL call the LLM with structured output to produce a list of action suggestions. Each suggestion SHALL include a `label` (short, user-facing button text, e.g., "Generate agreement draft"), an `icon` hint (a semantic category such as "generate", "research", "plan", "analyze", "summarize"), and a `prompt` (the natural language message to send to the task chat endpoint when clicked). The endpoint SHALL return an `ActionSuggestionsResponse` containing the list of suggestions.

#### Scenario: Suggest actions for a content-creation task
- **WHEN** a user requests action suggestions for a task titled "Create rental agreement" with status "not_started"
- **THEN** the endpoint returns 2–4 suggestions such as `{ label: "Generate agreement draft", icon: "generate", prompt: "Generate a rental agreement draft based on the task details" }`

#### Scenario: Suggest actions for a research task
- **WHEN** a user requests action suggestions for a task titled "Find best watch options" with status "in_progress"
- **THEN** the endpoint returns suggestions such as `{ label: "Research watch options with AI", icon: "research", prompt: "Search for and compare the best watch options considering my requirements" }`

#### Scenario: Suggest actions for a completed task
- **WHEN** a user requests action suggestions for a task with status "done"
- **THEN** the endpoint returns suggestions contextual to completion, such as "Review outcome", "Generate summary", or "Suggest follow-up tasks"

#### Scenario: Suggest actions considering dependencies
- **WHEN** a user requests action suggestions for a task that depends on a "done" task titled "Research moving companies"
- **THEN** the suggestions MAY reference available context from completed dependencies, e.g., "Compare options based on research results"

#### Scenario: Unauthorized task access
- **WHEN** a user requests action suggestions for a task they do not own
- **THEN** the endpoint returns 403 Forbidden

#### Scenario: Task not found
- **WHEN** a user requests action suggestions for a non-existent task ID
- **THEN** the endpoint returns 404 Not Found

### Requirement: Action Suggestion Schema
The system SHALL define Pydantic schemas for action suggestions: `ActionSuggestion` with fields `label` (str, max 60 chars), `icon` (str, one of: "generate", "research", "plan", "analyze", "summarize", "review", "compare", "create"), and `prompt` (str, max 500 chars). `ActionSuggestionsResponse` SHALL contain a field `actions` (list of `ActionSuggestion`, min 2, max 4).

#### Scenario: Valid action suggestion structure
- **WHEN** the LLM produces action suggestions
- **THEN** each suggestion conforms to the `ActionSuggestion` schema with label, icon, and prompt fields

#### Scenario: Action count within bounds
- **WHEN** the LLM is prompted for suggestions
- **THEN** exactly 2–4 suggestions are returned, enforced by the structured output schema

### Requirement: Action Suggestion Prompt
The system SHALL store the action suggestion system prompt as a separate module in `app/domains/ai/prompts/action_suggestions.py`. The prompt SHALL instruct the LLM to generate contextual, actionable suggestions based on the task's content, status, subtasks, and relationship to other tasks. The prompt SHALL emphasize producing diverse action types (not all the same category) and using the user's language (matching the task's language).

#### Scenario: Prompt stored as module
- **WHEN** the action suggestion feature is invoked
- **THEN** the system prompt is loaded from the dedicated prompt module, not inline in the endpoint

#### Scenario: Suggestions match task language
- **WHEN** a task has a Russian title "Найти лучшие часы"
- **THEN** the action suggestions are returned in Russian, e.g., `{ label: "Исследовать варианты часов", ... }`

### Requirement: Action Suggestion Model Configuration
The system SHALL use a configurable LLM model for action suggestions via the `AI_ACTION_SUGGEST_MODEL` setting, defaulting to `AI_CHAT_MODEL` if not set, which in turn defaults to `AI_DEFAULT_MODEL`. This allows using a cheaper/faster model for suggestions.

#### Scenario: Custom suggestion model configured
- **WHEN** `AI_ACTION_SUGGEST_MODEL` is set to "openai/gpt-4o-mini"
- **THEN** action suggestion generation uses that model

#### Scenario: Suggestion model falls back to chat model
- **WHEN** `AI_ACTION_SUGGEST_MODEL` is not set
- **THEN** the system uses `AI_CHAT_MODEL` (or `AI_DEFAULT_MODEL` as final fallback)
