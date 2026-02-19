## 1. Extend format_user_meta_block and add resolve_user_context
- [x] 1.1 Add day-of-week computation to `format_user_meta_block()` in `prompts/meta.py` — parse the current_date and compute the English day name (e.g., "Thursday")
- [x] 1.2 Add `resolve_user_context(user_meta: dict | None) -> str` function to `prompts/meta.py` — takes stored user_meta dict, computes current date + day-of-week server-side using stored timezone (via `datetime.now(ZoneInfo(tz))`) and delegates to `format_user_meta_block()`
- [x] 1.3 Write unit tests for `format_user_meta_block()` day-of-week output and `resolve_user_context()` server-side date computation (including cross-timezone edge cases)

## 2. Add user context to classification
- [x] 2.1 Update `classify_goal()` in `nodes/classify.py` to accept optional `user_context: str = ""` parameter and append it to the user prompt
- [x] 2.2 Update `classify_and_generate_questions()` in `service.py` to pass `user_context` to `classify_goal()`
- [x] 2.3 Update `goals/service.py` to call `resolve_user_context()` from the goal's user_meta and pass it through

## 3. Add user context to chat system prompts
- [x] 3.1 Add `{user_context}` placeholder to `TASK_CHAT_SYSTEM_PROMPT` in `prompts/chat.py` (in the Context section, after memory_context)
- [x] 3.2 Add `{user_context}` placeholder to `BOARD_CHAT_SYSTEM_PROMPT` in `prompts/board_chat.py` (in the Context section, after memory_context)

## 4. Add user_context to chat graph states
- [x] 4.1 Add `user_context: str` field to `TaskChatState` in `graphs/chat.py`
- [x] 4.2 Update `respond` node in `graphs/chat.py` to inject `user_context` into the system prompt template
- [x] 4.3 Add `user_context: str` field to `BoardChatState` in `graphs/board_chat.py`
- [x] 4.4 Update `respond` node in `graphs/board_chat.py` to inject `user_context` into the system prompt template

## 5. Update chat endpoints to resolve and pass user context
- [x] 5.1 In `ai/router.py` `task_chat()`: resolve user_context from goal's `ai_context["user_meta"]` via `resolve_user_context()` and pass it to graph invocation
- [x] 5.2 In `ai/router.py` `board_chat()`: resolve user_context from goal's `ai_context["user_meta"]` via `resolve_user_context()` and pass it to graph invocation

## 6. Add user context to subtask action generation
- [x] 6.1 Update `generate_subtask_actions()` in `service.py` to accept optional `user_context: str = ""` parameter
- [x] 6.2 Update the subtask action user prompt (in `prompts/action_suggestions.py` or its caller) to include user_context
- [x] 6.3 Pass user_context through from board generation pipeline and subtask action endpoint

## 7. Verification
- [x] 7.1 Run existing backend tests to confirm no regressions (`pytest`)
- [x] 7.2 Run type checker (`pyright`) to confirm no type errors introduced
- [ ] 7.3 Manual smoke test: create a goal with user_meta and verify the "User context" block (with day-of-week) appears in LLM prompts for classification, questions, board generation, and chat
