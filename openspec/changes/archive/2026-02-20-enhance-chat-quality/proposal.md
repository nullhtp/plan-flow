# Change: Enhance task chat quality — concise messages, detailed artifacts, more tools

## Why
The current task chat AI tends to produce long inline responses even when the content would be better served as a persistent artifact. Artifacts need to be more thorough, well-structured, and comprehensive. Additionally, two useful tools are missing from the chat: URL page fetching (already coded but not registered) and artifact updating (can only create, not revise). The tool iteration limit (10) is too restrictive for multi-step research tasks.

## What Changes
- **Chat response style**: Update system prompts to enforce a "smart mode" — short conversational replies for simple questions, automatic artifact creation for substantial content (plans, research, comparisons, checklists, agreements). The chat message should summarize what was done in 1-3 sentences and reference the saved artifact.
- **Artifact quality**: Update system prompts with explicit instructions for artifact structure — proper headings, tables, bullet points, thorough coverage, actionable output. Artifacts should be comprehensive documents, not abbreviated summaries.
- **Register `fetch_url_content` tool**: The tool already exists in `tools/url_fetch.py` but is not registered in either `get_task_chat_tools()` or `get_board_chat_tools()`. Register it in both.
- **Add `update_artifact` tool**: New mutation tool that replaces the content of an existing artifact. Executes immediately (non-destructive — previous content is overwritten, not deleted). Available in both task and board chat.
- **Add `save_artifact` to board chat**: Currently only available in task chat. Add it to board chat so the AI can create artifacts on specific tasks from the board-level conversation.
- **Increase tool iteration limit**: Raise `MAX_TOOL_ITERATIONS` from 10 to 15 to allow more thorough multi-step research and complex tool chains.
- **Update `Tool Confirmation Flow`**: Add `save_artifact`, `update_artifact`, and `fetch_url_content` to the immediate-execution list.

## Impact
- Affected specs: `ai-tools`, `ai-pipeline`, `task-chat-ui`, `task-artifacts`
- Affected code:
  - `backend/app/domains/ai/tools/registry.py` — register `fetch_url_content` and `update_artifact` in both tool sets, add `save_artifact` to board chat
  - `backend/app/domains/ai/tools/mutations.py` — add `make_update_artifact()` factory
  - `backend/app/domains/ai/prompts/chat.py` — rewrite for concise messages + detailed artifacts
  - `backend/app/domains/ai/prompts/board_chat.py` — add artifact and URL fetch instructions
  - `backend/app/domains/ai/graphs/base.py` — change `MAX_TOOL_ITERATIONS` from 10 to 15
  - `frontend/src/features/ai-chat/hooks/use-task-chat.ts` — handle `update_artifact` action refresh
