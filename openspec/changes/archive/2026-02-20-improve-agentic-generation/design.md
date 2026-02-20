## Context
The current AI pipeline (classify → questions → skeleton → enrichment) makes no external web requests during generation. Web search (Tavily) is only available in the chat ReAct agents. Goals about real-world topics (relocation, regulations, market research) produce generic plans based solely on LLM training data. The prompts use direct structured output without reasoning steps or examples, leading to lower quality outputs.

This design introduces research capabilities into the generation pipeline while preserving the existing structured output pattern for actual generation steps.

## Goals / Non-Goals

- Goals:
  - Add web research to all generation pipeline stages (classification, questions, skeleton, enrichment)
  - Add URL content extraction for deeper research from search results
  - Add a skeleton review/revision step using gathered research context
  - Improve prompt quality with chain-of-thought and few-shot examples
  - Stream research progress to the user via SSE events
  - Make research budget configurable with a hard ceiling
  - Maintain backward compatibility when Tavily is not configured (graceful degradation)

- Non-Goals:
  - Converting the pipeline to a full ReAct agent loop (keep structured output for generation)
  - Adding self-critique/quality scoring (users refine via board chat)
  - Replacing Tavily with another search provider
  - Adding document/file upload capabilities
  - Multi-model cost optimization per pipeline stage (separate concern)

## Decisions

### Decision 1: Research as a dedicated pipeline node, not inline in each stage
Each generation step (questions, skeleton, enrichment) needs research context, but running separate research per step would be slow and redundant. Instead:
- A single `research` node runs BEFORE skeleton generation, gathering broad context
- The research results are passed as context to all downstream nodes
- Question generation gets a lighter "pre-research" call (1-2 queries) focused on understanding the domain
- Enrichment receives the full research context plus can do 1-2 targeted queries per task if needed

**Alternatives considered:**
- Inline research in each node: Slower, redundant queries, harder to manage budget
- Single research for everything: Misses task-specific details during enrichment
- Full ReAct loop: Too complex, unpredictable latency, harder to stream progress

### Decision 2: URL content extraction via httpx + readability extraction
Add a lightweight URL fetcher that:
1. Fetches the page with httpx (async, with timeout)
2. Extracts readable content using a Python readability library (e.g., `readabilipy` or `trafilatura`)
3. Truncates to a configurable max length (e.g., 4000 chars) to fit in LLM context
4. Caches results in-memory for the duration of a generation to avoid re-fetching

This is NOT a full browser — no JavaScript rendering, no interactive pages. It handles static HTML content which covers most informational pages.

**Alternatives considered:**
- Full headless browser (Playwright): Too heavy, slow, complex dependency
- Tavily's extract endpoint: Would add vendor lock-in and cost
- No page fetching: Limits research to search snippets only

### Decision 3: Multi-query research strategy with LLM-generated queries
The research node uses the LLM to generate 3-8 search queries from the goal context (not just the raw input), then executes them in parallel via Tavily. This produces diverse, targeted results vs. a single generic search.

Flow:
1. LLM generates search queries based on goal + classification + answers
2. Queries executed in parallel via Tavily
3. Results deduplicated by URL
4. Top results ranked by relevance score
5. Top N URLs fetched for full content extraction
6. Research context compiled into a structured summary

### Decision 4: Skeleton revision loop (review-only, no extra research)
After initial skeleton generation:
1. A review LLM call receives: the skeleton, the research context, the goal context
2. It produces: a critique (issues found) and an optional revised skeleton
3. If the revision changes the skeleton, the new skeleton replaces the original
4. Only one revision pass — no iterative loop

This catches obvious gaps (missing steps, wrong ordering) without adding unbounded latency.

### Decision 5: Chain-of-thought via structured output with reasoning field
Rather than free-text CoT, add an optional `reasoning` field to structured output schemas. The LLM is instructed to think through its approach in this field before producing the actual output. The `reasoning` field is logged but not sent to the user.

### Decision 6: Research budget management
- `AI_MAX_RESEARCH_QUERIES` env var (default: 15) sets hard ceiling per generation
- Research node tracks query count and stops when budget exhausted
- Budget split: ~2 queries for pre-research (questions), ~8 for main research (skeleton), ~5 reserved for enrichment
- The split is advisory — the agent can redistribute within the total budget

## Risks / Trade-offs

- **Latency increase** → Research adds 3-10 seconds to generation. Mitigated by: parallel query execution, SSE progress events keeping user informed, and research running concurrently where possible.
- **Cost increase** → More Tavily API calls + more LLM tokens (research context in prompts). Mitigated by: configurable budget ceiling, graceful degradation when Tavily unavailable.
- **URL fetch reliability** → Some pages block bots, have CAPTCHAs, or require JS. Mitigated by: timeout handling, graceful fallback to search snippets, not treating fetch failures as errors.
- **Prompt size growth** → CoT + few-shot + research context increases token usage. Mitigated by: truncating research context to fit, summarizing when context exceeds limits.
- **Research relevance** → LLM-generated queries may not always be relevant. Mitigated by: using classification + answers for query generation (not just raw input), relevance scoring of results.

## Open Questions
- Exact readability extraction library choice (`trafilatura` is well-maintained, `readabilipy` is lighter) — decide during implementation based on dependency size and quality.
- Whether to cache research results in the database for reuse across regenerations of the same goal, or keep in-memory only.
