## 1. Data Model & Migration
- [x] 1.1 Create PendingAction SQLModel in `app/domains/ai/models.py` (id, user_id, thread_id, tool_name, tool_args, description, status, result, created_at, expires_at)
- [x] 1.2 Create Alembic migration for `pending_action` table with indexes on user_id, thread_id, and (thread_id, status)
- [x] 1.3 Add new config settings to `app/core/config.py`: `TAVILY_API_KEY`, `AI_WEB_SEARCH_MAX_RESULTS`, `AI_CHAT_MODEL`
- [x] 1.4 Add `tavily-python` to backend dependencies in `pyproject.toml`

## 2. Information Retrieval Tools
- [x] 2.1 Create `app/domains/ai/tools/` package with `__init__.py`
- [x] 2.2 Implement retrieval tools in `app/domains/ai/tools/retrieval.py`: get_task_details, get_board_overview, get_blocked_tasks, get_task_dependencies, list_all_tasks, get_board_progress
- [x] 2.3 Write unit tests for each retrieval tool (mock DB session, verify correct data returned)

## 3. Task Mutation Tools
- [x] 3.1 Implement mutation tools in `app/domains/ai/tools/mutations.py`: update_task_field, update_task_status, create_subtask, toggle_subtask, delete_subtask
- [x] 3.2 Implement confirmation logic: tools that require confirmation create PendingAction instead of executing
- [x] 3.3 Write unit tests for mutation tools (verify immediate execution vs. pending action creation, business rule enforcement)

## 4. Board Structure Tools
- [x] 4.1 Implement structure tools in `app/domains/ai/tools/structure.py`: add_task, remove_task, add_dependency, remove_dependency, split_task
- [x] 4.2 Integrate DAG validation into add_task, add_dependency, and split_task tools (reuse existing dag_utils)
- [x] 4.3 Write unit tests for structure tools (DAG validation, goal node protection, confirmation flow)

## 5. Web Search Tool
- [x] 5.1 Implement web search tool in `app/domains/ai/tools/web_search.py` using Tavily
- [x] 5.2 Handle missing API key gracefully (tool not registered)
- [x] 5.3 Write unit tests with mocked Tavily client

## 6. Tool Registry
- [x] 6.1 Implement tool registry in `app/domains/ai/tools/registry.py` with get_task_chat_tools and get_board_chat_tools
- [x] 6.2 Implement context binding (pre-inject task_id, board_id, user_id, db_session into tool closures)
- [x] 6.3 Write unit tests verifying correct tool sets per context and Tavily exclusion when unconfigured

## 7. Chat Response Schema
- [x] 7.1 Add ToolAction and ChatResponse schemas to `app/domains/ai/schemas.py`
- [x] 7.2 Update TaskChatResponse to use ChatResponse schema (backward-compatible: new fields default to empty)

## 8. Confirmation Flow Endpoints
- [x] 8.1 Implement PendingAction CRUD service functions (create, get, confirm, reject, expire)
- [x] 8.2 Implement `POST /api/actions/{action_id}/confirm` endpoint
- [x] 8.3 Implement `POST /api/actions/{action_id}/reject` endpoint
- [x] 8.4 Implement tool execution dispatcher (given tool_name + tool_args, execute the actual mutation)
- [x] 8.5 Write integration tests for confirm/reject flow (happy path, expired, already confirmed, wrong user)

## 9. Task Chat Graph Upgrade
- [x] 9.1 Upgrade `app/domains/ai/graphs/chat.py` to ReAct agent loop with tool binding
- [x] 9.2 Add conditional edge logic (tool call detection -> tool execution -> loop back vs. final response)
- [x] 9.3 Add max iteration guard (10 tool calls per turn)
- [x] 9.4 Update task chat system prompt in `app/domains/ai/prompts/chat.py` with tool usage instructions
- [x] 9.5 Update task chat router endpoint to pass tools to graph and collect ToolAction results
- [x] 9.6 Write integration tests for task chat with tool usage (mock LLM with tool call responses)

## 10. Board Chat Graph & Endpoint
- [x] 10.1 Create `app/domains/ai/graphs/board_chat.py` with ReAct agent loop and board tool set
- [x] 10.2 Create board chat system prompt in `app/domains/ai/prompts/board_chat.py`
- [x] 10.3 Implement `POST /api/boards/{board_id}/chat` endpoint in AI router
- [x] 10.4 Write integration tests for board chat (ownership validation, tool usage, confirmation flow)

## 11. Validation & Cleanup
- [x] 11.1 Regenerate OpenAPI spec and verify new endpoints appear correctly
- [x] 11.2 Run full test suite and fix any regressions
- [x] 11.3 Update docker-compose.yml with new environment variables (TAVILY_API_KEY, AI_CHAT_MODEL) as optional entries
- [x] 11.4 Verify existing task chat endpoint backward compatibility (old clients get response string + empty actions)
