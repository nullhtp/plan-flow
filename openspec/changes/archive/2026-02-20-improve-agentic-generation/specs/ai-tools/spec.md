## ADDED Requirements

### Requirement: URL Content Extraction Tool
The system SHALL provide a `fetch_url_content` LangChain tool in `app/domains/ai/tools/url_fetch.py` for use in chat agents. The tool SHALL accept a `url` (string) parameter and return the extracted readable text content from the page, truncated to 4000 characters. The tool SHALL execute immediately without confirmation. The tool SHALL use the same `fetch_url_content` utility function used by the pipeline research node. The tool SHALL be included in both task chat and board chat tool sets when available. The tool SHALL return a user-friendly error message if the URL cannot be fetched or content cannot be extracted. The chat system prompts SHALL instruct the AI to use this tool when the user asks to look at a specific URL or when the AI wants to dive deeper into a search result.

#### Scenario: AI fetches URL content in chat
- **WHEN** the AI calls `fetch_url_content("https://example.com/portugal-visa-guide")` during a task chat
- **THEN** the tool returns the readable text content of the page, truncated to 4000 characters

#### Scenario: URL fetch failure in chat
- **WHEN** the AI calls `fetch_url_content` for a URL that times out or returns an error
- **THEN** the tool returns a message like "Unable to fetch content from this URL. The page may be unavailable or require JavaScript to load."

#### Scenario: URL fetch tool in task chat tools
- **WHEN** `get_task_chat_tools` is called
- **THEN** the returned list includes `fetch_url_content` tool

#### Scenario: URL fetch tool in board chat tools
- **WHEN** `get_board_chat_tools` is called
- **THEN** the returned list includes `fetch_url_content` tool

## MODIFIED Requirements

### Requirement: Tool Registry
The system SHALL provide two functions to assemble context-bound tool lists: `get_task_chat_tools(db, board_id, task_id, user_id, thread_id)` returns tools scoped to a specific task (information retrieval + task mutations + web search + URL fetch + save artifact); `get_board_chat_tools(db, board_id, user_id, thread_id)` returns all task tools plus board-structure tools. Each function SHALL capture `db`, IDs, and `thread_id` via closures so tools execute in the correct context.

#### Scenario: Task chat tools returned
- **WHEN** `get_task_chat_tools` is called with valid IDs
- **THEN** the returned list includes retrieval tools, mutation tools, `save_artifact`, `fetch_url_content`, and optionally `web_search`

#### Scenario: Board chat tools returned
- **WHEN** `get_board_chat_tools` is called with valid IDs
- **THEN** the returned list includes all task chat tools plus board-structure tools

#### Scenario: Web search excluded when Tavily not configured
- **WHEN** `TAVILY_API_KEY` is not set
- **THEN** `web_search` is not included in the tool list but `fetch_url_content` is still available

## ADDED Requirements

### Requirement: Tool-Aware Chat System Prompts
The system SHALL maintain separate system prompt modules for task chat (`app/domains/ai/prompts/chat.py`) and board chat (`app/domains/ai/prompts/board_chat.py`). The task chat prompt SHALL instruct the AI on available tools (retrieval, mutations, web search, URL fetch, save_artifact), establish its role as a helpful task assistant, and guide appropriate tool usage. The prompt SHALL include instructions to use the `save_artifact` tool when generating substantial, reusable content such as agreements, plans, research summaries, or comparisons — rather than including long content only in the chat message. The prompt SHALL include instructions to use `fetch_url_content` when the user shares a URL or when the AI wants to examine a search result in detail, and to cite sources with URLs when using information from web search or fetched pages. The board chat prompt SHALL additionally cover structural tools (add/remove tasks and dependencies, split tasks). Both chat prompts SHALL include a `{user_context}` template placeholder that is populated with the formatted user meta block (from `resolve_user_context()`), enabling the AI to reason about the user's timezone, current date, day of week, locale, location, and device during chat interactions.

#### Scenario: Task chat prompt includes tool instructions
- **WHEN** a task chat graph is compiled
- **THEN** the system prompt from `prompts/chat.py` is used, including instructions for all available tools

#### Scenario: Task chat prompt includes artifact instructions
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes instructions to use `save_artifact` for substantial generated content

#### Scenario: Task chat prompt includes URL fetch instructions
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes instructions to use `fetch_url_content` for examining URLs and diving deeper into search results

#### Scenario: Board chat prompt includes structural tool instructions
- **WHEN** a board chat graph is compiled
- **THEN** the system prompt from `prompts/board_chat.py` is used, including instructions for structural tools

#### Scenario: Task chat prompt includes user context
- **WHEN** a task chat prompt is rendered with user_context containing timezone and current date
- **THEN** the rendered system prompt includes the "User context" block with timezone, date, and day of week

#### Scenario: Board chat prompt includes user context
- **WHEN** a board chat prompt is rendered with user_context containing location "Berlin, Germany"
- **THEN** the rendered system prompt includes the "User context" block with the location

#### Scenario: Chat prompt without user context (backward compatible)
- **WHEN** a chat prompt is rendered with an empty user_context string
- **THEN** the prompt renders without a "User context" section
