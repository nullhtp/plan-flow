"""Research query generation prompt and context formatting utilities."""

from __future__ import annotations

from app.core.config import settings
from app.domains.ai.research import ResearchContext

RESEARCH_QUERIES_SYSTEM_PROMPT = """\
You are a research strategist for PlanFlow, an AI-powered planning tool.

Your task is to generate diverse, targeted web search queries that will \
gather actionable information needed to create a high-quality project plan \
for the user's goal.

You MUST use the **reasoning** field to think step-by-step about your \
research strategy before listing queries:
- What are the key knowledge gaps that web research could fill?
- What domain-specific information would make the plan more accurate?
- What locale-specific details (regulations, costs, timelines) are needed?

Then generate 3-8 search queries that:
1. Cover different aspects of the goal (don't repeat the same topic)
2. Mix locale-specific queries (in the user's language if searching for \
local info) with universal/technical queries (in English)
3. Prioritize queries that fill knowledge gaps NOT covered by the user's \
answers
4. Include specific years, locations, or technical terms for better results
5. Avoid overly broad queries like "how to move" — be specific

Examples of good queries for a "relocate from Berlin to Lisbon" goal:
- "cost of living Lisbon vs Berlin 2026"
- "Portugal NIF tax number application process"
- "Lisbon neighborhoods expats families 2026"
- "Berlin to Lisbon shipping furniture cost"
- "Portugal D7 visa requirements EU citizens"
"""

RESEARCH_QUERIES_USER_PROMPT = """\
Goal: {raw_input}

Classification:
- Domain: {domain}
- Complexity: {complexity}/5
- Key dimensions: {dimensions}
- Language: {language}

User's answers to questions:
{qa_pairs}
{user_context}{memory_context}

Generate {query_count} targeted search queries for this goal."""


def format_research_context(context: ResearchContext) -> str:
    """Format research results into a prompt-injectable text block.

    Returns a formatted block with search results and extracted content,
    truncated to the configured max length. Returns empty string if no results.
    """
    if not context.results:
        return ""

    max_chars = settings.ai_research_context_max_chars
    lines: list[str] = []
    lines.append(
        f"\nResearch findings ({len(context.results)} sources "
        f"from {context.queries_used} searches):"
    )

    char_count = len(lines[0])

    for r in context.results:
        # If we have full extracted content for this URL, use it
        full_content = context.fetched_contents.get(r.url)

        if full_content:
            snippet = full_content[:500]
            entry = f"\n- [{r.title}]({r.url})\n  {snippet}"
        else:
            snippet = r.content[:300] if r.content else ""
            entry = f"\n- [{r.title}]({r.url})\n  {snippet}"

        if char_count + len(entry) > max_chars:
            lines.append("\n... (additional results truncated)")
            break

        lines.append(entry)
        char_count += len(entry)

    return "\n".join(lines)
