# Change: Add AI-Generated Contextual Actions for Tasks

## Why
Tasks currently have no AI assistance at the point of execution. Users see a static detail panel with manual fields but no intelligent guidance. The AI infrastructure (chat endpoints, tools, pending actions) exists on the backend but has no frontend consumer. Adding contextual AI action buttons per task — generated dynamically based on the task's content and state — gives users one-click access to AI assistance (e.g., "Generate agreement via AI", "Find best options with AI", "Break into subtasks"). This bridges the gap between AI-generated boards and AI-assisted task execution.

## What Changes

### New capabilities
- **ai-task-actions**: A new backend endpoint generates 2–4 contextual AI actions per task using an LLM. Actions are generated on-demand when the user opens a task. The endpoint accepts task context (title, description, status, subtasks, immediate dependencies) and returns a list of action suggestions with labels and pre-filled chat prompts.
- **task-artifacts**: A new data model and API for persistent task artifacts. When the AI produces content (agreements, plans, research summaries, etc.), it is saved as a named markdown artifact on the task. Artifacts are accessible from the task detail panel and persist across sessions.
- **task-chat-ui**: A frontend chat interface in the TaskDetailPanel. AI actions trigger chat messages; the chat displays AI responses, tool actions, pending confirmations, and links to generated artifacts. This is the first frontend consumer of the existing backend chat endpoints.

### Modified capabilities
- **board-ui**: The TaskDetailPanel gains three new sections: AI Actions (contextual buttons at top), Artifacts (persistent content area), and Chat (conversation with the AI). All in a single scrollable panel.
- **board-management**: New Artifact model and CRUD endpoints. New action suggestion endpoint.
- **ai-tools**: A new `save_artifact` tool allowing the AI chat to persist generated content as task artifacts.
- **ai-pipeline**: A new action suggestion generation node/prompt. The task chat system prompt is updated to be aware of artifacts.

## Impact
- Affected specs: `ai-task-actions` (new), `task-artifacts` (new), `task-chat-ui` (new), `board-ui`, `board-management`, `ai-tools`, `ai-pipeline`
- Affected code:
  - Backend: `app/domains/ai/` (new endpoint, new prompt, new tool), `app/domains/boards/` (Artifact model, schemas, repository, service, router)
  - Frontend: `src/features/board/components/TaskDetailPanel.tsx` (major restructure), new components for chat, actions, artifacts
  - Database: new `artifact` table (Alembic migration)
  - API contract: new endpoints, new response schemas (Orval regeneration required)
