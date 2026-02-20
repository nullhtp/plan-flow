from __future__ import annotations

QUESTIONS_SYSTEM_PROMPT = """\
You are an expert planning assistant for PlanFlow.

Given a goal classification (domain, complexity, dimensions), generate \
adaptive questions to gather the information needed to create a \
detailed, actionable kanban board.

{round_instructions}

Each question must include:
- **id**: A unique identifier ({id_format}).
- **text**: The question text, clear and conversational.
- **type**: The form field type: "text", "select", "multiselect", \
or "number".
- **options**: A list of 3-6 selectable options. REQUIRED for ALL \
question types — never null or empty.
- **rationale**: A brief explanation of why this question matters for \
planning (shown to the user as helper text).
- **required**: Whether the question must be answered (default true). \
Set to false only for nice-to-have questions.
- **allow_other**: Whether users can type a custom answer (default true).

CRITICAL — options are required for every question type:
- "select": Provide 3-6 clear choices (e.g., experience levels, \
priorities).
- "multiselect": Provide 3-6 options where multiple may apply \
(e.g., concerns, preferences).
- "text": Provide 3-6 AI-suggested likely answers that the user can \
pick from (e.g., for "What is your main motivation?" suggest \
["Career opportunity", "Better quality of life", "Family reasons", \
"Adventure / new experience"]).
- "number": Provide 3-6 human-readable ranges instead of asking for \
a raw number (e.g., for budget: ["Under $1,000", "$1,000-$3,000", \
"$3,000-$5,000", "$5,000+"], for timeline: ["1-2 months", \
"3-4 months", "5-6 months", "6+ months"]).

The user always has an "Other" text field to type a custom answer, \
so the options don't need to be exhaustive — just cover the most \
common/likely answers.

You MUST also provide a **readiness** assessment:
- **score**: Float 0.0-1.0. How ready is the collected information \
for generating a high-quality board? 0.8+ = ready, <0.4 = significant gaps.
- **covered_dimensions**: Which classification dimensions are covered \
by answers collected so far.
- **uncovered_dimensions**: Which dimensions still lack information.
- **summary**: One sentence describing readiness (in the goal's language).

{deepening_instructions}

Guidelines:
- Ask about the dimensions identified in the classification.
- Keep questions concise and conversational, not formal.
- Aim for the minimum questions needed.
- For simple goals (complexity 1-2), lean toward 3-4 questions.
- For complex goals (complexity 4-5), lean toward 5-7 questions.
- IMPORTANT: Generate ALL question text, options, rationale, and \
readiness summary in the language specified below. Respond in \
{language_name} ({language}).
"""

QUESTIONS_USER_PROMPT = """\
Goal: {raw_input}

Classification:
- Domain: {domain}
- Complexity: {complexity}/5
- Key dimensions: {dimensions}
- Language: {language}
{qa_history}{user_context}{memory_context}"""

# ── Round-specific instruction fragments ──

INITIAL_ROUND_INSTRUCTIONS = """\
Generate 3-7 adaptive questions for the user. This is the initial round — \
no previous answers have been collected yet."""

INITIAL_ID_FORMAT = 'e.g., "q1", "q2"'

FOLLOW_UP_ROUND_INSTRUCTIONS = """\
Generate 2-4 follow-up questions. This is round {round_num} — the user \
has already answered questions in previous rounds. Focus on deepening \
understanding and filling gaps."""

FOLLOW_UP_ID_FORMAT = (
    'prefixed with round number, e.g., "r{round_num}q1", "r{round_num}q2"'
)

DEEPENING_INSTRUCTIONS = """\
Progressive deepening rules (follow-up rounds):
- Do NOT repeat topics already covered in previous rounds.
- Drill deeper into partially covered dimensions based on previous answers.
- If a dimension is fully covered, explore new or adjacent dimensions.
- Ask more specific questions informed by what the user already told you.
- Generate only 2-4 questions per follow-up round to keep it lightweight."""

NO_DEEPENING_INSTRUCTIONS = ""


def build_system_prompt(
    language: str,
    language_name: str,
    round_num: int,
) -> str:
    """Build the question generation system prompt for a specific round."""
    if round_num == 1:
        round_instructions = INITIAL_ROUND_INSTRUCTIONS
        id_format = INITIAL_ID_FORMAT
        deepening_instructions = NO_DEEPENING_INSTRUCTIONS
    else:
        round_instructions = FOLLOW_UP_ROUND_INSTRUCTIONS.format(round_num=round_num)
        id_format = FOLLOW_UP_ID_FORMAT.format(round_num=round_num)
        deepening_instructions = DEEPENING_INSTRUCTIONS

    return QUESTIONS_SYSTEM_PROMPT.format(
        language=language,
        language_name=language_name,
        round_instructions=round_instructions,
        id_format=id_format,
        deepening_instructions=deepening_instructions,
    )


def format_qa_history(rounds: list[dict]) -> str:
    """Format Q&A history from rounds data for prompt injection.

    For rounds > 5, early rounds are summarized to manage prompt size.
    """
    if not rounds:
        return ""

    answered_rounds = [r for r in rounds if r.get("answers")]
    if not answered_rounds:
        return ""

    lines: list[str] = []
    lines.append("\nPrevious questions and answers:")

    total = len(answered_rounds)

    for r in answered_rounds:
        round_num = r.get("round", 0)
        questions = r.get("questions", [])
        answers = r.get("answers", {})

        # For large histories, summarize early rounds
        if total > 5 and round_num <= total - 2:
            # Summarize: just list dimension coverage
            covered = []
            for q in questions:
                qid = q.get("id", "")
                if answers.get(qid):
                    covered.append(q.get("text", "")[:60])
            if covered:
                lines.append(
                    f"\n[Round {round_num} summary: "
                    f"answered {len(covered)} questions "
                    f"covering: {', '.join(covered)}]"
                )
        else:
            # Full detail for recent rounds
            lines.append(f"\n--- Round {round_num} ---")
            for q in questions:
                qid = q.get("id", "")
                text = q.get("text", "")
                answer = answers.get(qid, "(not answered)")
                lines.append(f"Q ({qid}): {text}\nA: {answer}")

    return "\n".join(lines)
