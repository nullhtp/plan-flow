## Context

User context (timezone, locale, current date, location, device type) is currently only injected into the board generation pipeline. Chat endpoints, classification, and subtask action generation receive no environmental context. This is a cross-cutting change touching all AI call sites.

## Goals / Non-Goals

- Goals:
  - Every LLM invocation receives a standardized "User context" block
  - Add day-of-week to the context block
  - Chat endpoints derive context server-side from goal's stored `user_meta` — no API changes
  - Classification node receives user context for time-sensitive goal understanding
- Non-Goals:
  - Changing the `TaskChatRequest`/`BoardChatRequest` API schemas
  - Adding new context fields beyond day-of-week (e.g., active board count, user preferences)
  - Changing how user_meta is collected on the frontend

## Decisions

### 1. Server-side context resolution for chat endpoints

- **Decision**: Chat endpoints resolve user context from the goal's stored `user_meta` (already persisted in `goal.ai_context["user_meta"]`). Current date is computed server-side using the stored timezone.
- **Alternatives considered**:
  - *Frontend sends user_meta with each chat message*: More accurate (captures timezone changes) but requires API schema changes and frontend work. Rejected for now — timezone rarely changes mid-session.
  - *Hybrid (frontend sends, backend supplements)*: Unnecessary complexity for the same result.
- **Rationale**: The goal's `user_meta` is already captured at goal creation time with accurate timezone, locale, location, and device. The only field that changes over time is `current_datetime`, which we compute server-side from the stored timezone. This avoids any API or frontend changes.

### 2. Day-of-week addition

- **Decision**: Add day-of-week (e.g., "Thursday") to `format_user_meta_block()` output, computed from the current date and stored timezone.
- **Rationale**: Helps the AI reason about scheduling, urgency, and deadline proximity without having to infer the day from the date string.

### 3. Centralized context resolution helper

- **Decision**: Add a `resolve_user_context()` helper in `prompts/meta.py` that takes a `user_meta` dict (from `goal.ai_context`) and returns the formatted context string with server-computed current date and day-of-week.
- **Rationale**: Avoids duplicating date computation logic across router.py and service.py. All call sites use one function.

### 4. Context injection into chat graph state

- **Decision**: Add a `user_context` field to `TaskChatState` and `BoardChatState`. The `respond` node includes it in the system prompt via a new `{user_context}` placeholder.
- **Alternatives considered**:
  - *Bake context into the system prompt at the router level*: Would work but makes the system prompt construction less consistent — some templates would have `{user_context}` and some wouldn't.
- **Rationale**: Consistent with how `memory_context` is already handled — passed as state, injected into the prompt template by the `respond` node.

### 5. Classification context

- **Decision**: Pass `user_context` string to `classify_goal()` and include it in the classification user prompt (not system prompt).
- **Rationale**: Classification system prompt defines the schema/instructions. User context is input data, so it belongs in the user message alongside the goal text.

## Risks / Trade-offs

- **Stale context in long chat sessions**: If a user chats across midnight, the date will be stale until the next chat message triggers a fresh computation. Acceptable — the context is recomputed on every chat invocation (every HTTP request), so it will be fresh each turn.
- **Missing user_meta**: Some goals created before the user_meta feature may have `None` for `ai_context["user_meta"]`. The `resolve_user_context()` helper will gracefully return an empty string in this case, matching existing `format_user_meta_block()` behavior.

## Open Questions

None — all decisions are straightforward extensions of existing patterns.
