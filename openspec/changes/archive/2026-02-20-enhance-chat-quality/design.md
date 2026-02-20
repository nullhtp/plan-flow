## Context

The task chat AI currently produces long inline responses that mix conversational text with substantive content (research, plans, comparisons). This makes chat hard to scan and the valuable content gets lost in the conversation history. The artifact system exists but the AI doesn't use it proactively enough. Additionally, two useful tools are either unregistered (`fetch_url_content`) or missing (`update_artifact`), and the tool iteration limit is too low for thorough multi-step research.

This change spans the AI tools layer, system prompts, graph configuration, and the frontend artifact refresh logic.

## Goals / Non-Goals

- Goals:
  - Make chat messages concise (1-3 sentences for substantial content, longer only for simple Q&A)
  - Make artifacts comprehensive, well-structured, and thorough
  - Register `fetch_url_content` in both task and board chat tool sets
  - Add `update_artifact` tool to both task and board chat tool sets
  - Add `save_artifact` to board chat (currently task-only)
  - Increase tool iteration limit from 10 to 15
  - Update system prompts to enforce the "smart mode" pattern

- Non-Goals:
  - Adding new artifact content types (staying with markdown only)
  - Adding partial/section-level artifact editing (full replace only)
  - Changing the artifact data model beyond what's needed for updates
  - Adding user-created artifacts via the chat

## Decisions

### Smart Mode Response Pattern
- **Decision**: The AI should automatically decide between inline response and artifact based on content type and length. Substantial, reusable content (>~200 words, or document-like: plans, research, comparisons, templates, checklists, agreements) gets saved as an artifact with a short summary in chat. Simple Q&A and brief guidance stays inline.
- **Rationale**: This gives the best UX — users get fast, scannable chat messages while substantive content is persisted and viewable in full-screen. No manual "save this" step needed.
- **Alternative considered**: Always require explicit user request to save artifacts — rejected because it adds friction and most users won't think to ask.

### Update Artifact Tool Design
- **Decision**: `update_artifact(artifact_id, title, content)` — full content replacement. Both `title` and `content` are required parameters (title can stay the same or change). Executes immediately without confirmation.
- **Rationale**: Full replace is simpler to implement and reason about. The AI always has the complete new content in its context. Append-only would be fragile (duplications, formatting issues). Section-level editing adds complexity with minimal benefit.
- **Alternative considered**: Append-only mode — rejected because it leads to duplicate content and broken formatting when the AI wants to revise sections.

### Board Chat Gets Artifact Tools
- **Decision**: Add `save_artifact` and `update_artifact` to board chat. Both tools require a `task_id` parameter when called from board chat context (since there's no implicit current task). The board chat tool versions accept `task_id` as a parameter.
- **Rationale**: Board-level conversations often involve cross-task planning and research. Being able to save artifacts on specific tasks from the board chat context is valuable.

### Tool Iteration Limit
- **Decision**: Increase from 10 to 15.
- **Rationale**: Multi-step research (web search → fetch URL → save artifact) can consume 3-5 tool calls per research item. With 10, the AI often hits the limit mid-research. 15 gives enough headroom for thorough work without excessive cost risk.
- **Alternative considered**: No limit — rejected due to cost risk with runaway tool loops.

## Risks / Trade-offs

- **Artifact overuse**: The AI might save artifacts too aggressively for content that's better inline. → Mitigated by clear prompt guidelines on when to use artifacts vs inline responses.
- **Token cost increase**: More tool iterations and more detailed artifacts mean more tokens. → Mitigated by the 15-iteration cap and the fact that artifacts replace long inline responses (net token count similar).
- **Board chat artifact complexity**: Board chat needs `task_id` for artifact tools, adding a parameter the AI must figure out. → Mitigated by prompt instructions to use `list_all_tasks` first if needed.

## Open Questions

- None remaining (all resolved via user Q&A).
