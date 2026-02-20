# Change: Improve Generation Flows with Agentic Research and Better Prompts

## Why
The current board generation pipeline produces weak results because it operates in a vacuum — no web research informs classification, question generation, or board creation. The AI generates task DAGs based solely on the user's answers and its training data, with no access to real-world information (pricing, regulations, timelines, local knowledge). Additionally, the prompts lack chain-of-thought reasoning and few-shot examples, reducing output quality. This change introduces a research-augmented, agentic generation pipeline that gathers relevant external knowledge before and during generation, and adds a self-review step after skeleton generation.

## What Changes
- **Research node**: Add a dedicated research step to the generation pipeline that runs web searches (Tavily) and URL content extraction before skeleton generation, question generation, and task enrichment
- **URL content extraction**: Add a new tool/utility that fetches and extracts readable text from URLs found in search results, giving the AI access to full article content
- **Multi-query research strategy**: The research node generates multiple search queries from the goal context, executes them in parallel, deduplicates and ranks results
- **Skeleton revision loop**: After initial skeleton generation, a review step critiques the skeleton against gathered research context and optionally revises it (no additional research during review)
- **Prompt improvements**: Add chain-of-thought reasoning instructions and few-shot examples to classification, question generation, board skeleton, and enrichment prompts
- **Research SSE events**: Stream research progress to the frontend (`research_started`, `research_progress`, `research_complete`) so users see what the AI is investigating
- **Configurable research budget**: `AI_MAX_RESEARCH_QUERIES` env var with sensible default caps the total number of search queries per generation
- **Research context injection**: All downstream pipeline nodes receive the gathered research context alongside existing user/memory context

## Impact
- Affected specs: `ai-pipeline`, `ai-tools`, `board-generation-progress`
- Affected code:
  - `backend/app/domains/ai/nodes/` — new `research.py` node, modified `generate_board.py`, `questions.py`, `enrich_task.py`, `classify.py`
  - `backend/app/domains/ai/service.py` — orchestration changes for research steps and revision loop
  - `backend/app/domains/ai/tools/web_search.py` — extract shared search utility for pipeline use
  - `backend/app/domains/ai/tools/` — new `url_fetch.py` tool
  - `backend/app/domains/ai/prompts/` — all prompt modules updated with CoT and few-shot examples
  - `backend/app/domains/ai/schemas.py` — new research output schemas
  - `backend/app/core/config.py` — new settings
  - `frontend/src/features/board/hooks/` — updated SSE hook for new event types
  - `frontend/src/features/board/components/` — updated progress UI for research phase
