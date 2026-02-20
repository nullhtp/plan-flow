## 1. Backend: Add `update_artifact` tool
- [x] 1.1 Add `make_update_artifact(db, board_id, user_id, thread_id)` factory in `tools/mutations.py` — accepts `artifact_id`, `title`, `content`; validates artifact exists and belongs to user's board; replaces content immediately; returns success/failure dict
- [x] 1.2 Add `updated_at` to `ArtifactResponse` schema in `boards/schemas.py` (nullable datetime)
- [x] 1.3 Write unit test for `update_artifact` tool (success, not found, wrong board)

## 2. Backend: Register `fetch_url_content` and new tools in registry
- [x] 2.1 Import `make_fetch_url_content` from `tools/url_fetch.py` in `tools/registry.py`
- [x] 2.2 Add `make_fetch_url_content()` to `get_task_chat_tools()` tool list
- [x] 2.3 Add `make_fetch_url_content()` to `get_board_chat_tools()` tool list
- [x] 2.4 Add `make_update_artifact()` to `get_task_chat_tools()` tool list
- [x] 2.5 Add `make_update_artifact()` to `get_board_chat_tools()` tool list
- [x] 2.6 Add `make_save_artifact()` to `get_board_chat_tools()` tool list (currently missing — requires passing a `task_id` parameter or adjusting the factory for board context)

## 3. Backend: Increase tool iteration limit
- [x] 3.1 Change `MAX_TOOL_ITERATIONS` from 10 to 15 in `graphs/base.py`

## 4. Backend: Update system prompts for smart mode + artifact quality
- [x] 4.1 Rewrite `TASK_CHAT_SYSTEM_PROMPT` in `prompts/chat.py`:
  - Add "smart mode" instructions: concise chat responses (1-3 sentences) when saving artifacts; full inline responses only for simple Q&A
  - Add artifact quality guidelines: proper markdown structure, thorough coverage, actionable content
  - Add `update_artifact` tool usage instructions
  - Add `fetch_url_content` tool usage instructions (already partially present, expand)
  - Keep existing sections: subtask action flow, quick-replies, language matching
- [x] 4.2 Update `BOARD_CHAT_SYSTEM_PROMPT` in `prompts/board_chat.py`:
  - Add "smart mode" instructions matching task chat
  - Add `save_artifact` and `update_artifact` tool instructions with `task_id` guidance
  - Add `fetch_url_content` tool usage instructions
  - Add artifact quality guidelines

## 5. Frontend: Handle `update_artifact` action in chat hook
- [x] 5.1 Update `use-task-chat.ts` to invalidate artifacts query cache when `update_artifact` tool action is executed (alongside existing `save_artifact` check)
- [x] 5.2 Regenerate Orval types if `ArtifactResponse` schema changed (to include `updated_at`)

## 6. Testing & Validation
- [ ] 6.1 Manually test task chat: verify concise responses for research/plan requests, verify artifact is auto-created
- [ ] 6.2 Manually test task chat: verify `update_artifact` works when asking to revise an existing artifact
- [ ] 6.3 Manually test task chat: verify `fetch_url_content` works when sharing a URL
- [ ] 6.4 Manually test board chat: verify `save_artifact` and `update_artifact` work with task_id specification
- [ ] 6.5 Verify tool iteration limit allows 15 iterations without premature cutoff
- [ ] 6.6 Run existing backend tests to ensure no regressions
