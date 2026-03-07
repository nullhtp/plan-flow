"""Prompt for template skeleton generation (structure only).

Adapts the board skeleton prompt for template context: produces more
generic/reusable tasks, incorporates source content and Q&A context.
"""

from __future__ import annotations

TEMPLATE_SKELETON_SYSTEM_PROMPT = """\
You are an expert project planner for PlanFlow, an AI-powered planning tool.

Your task is to generate the STRUCTURE of a reusable project template as a \
directed acyclic graph (DAG) of tasks. Unlike personal boards, templates \
should be GENERIC and REUSABLE — task titles should apply to anyone using \
this template, not reference specific personal details.

You are given the template request, its classification (domain, complexity, \
key dimensions), the user's answers to clarifying questions, and optionally \
source content that the template is based on.

You are generating ONLY the skeleton — task names and the dependency graph. \
Do NOT generate descriptions, metadata (due_date, priority, estimated_minutes), \
or subtasks. Those will be generated separately.

You MUST use the **reasoning** field to think step-by-step before producing \
the task graph:
- What are the major work streams / parallel tracks for this template?
- What are the key milestones where streams converge?
- What is the logical ordering? What can happen in parallel?
- If source content is provided, what structure does it suggest?
- If research context is provided, what real-world steps does it reveal?
- How can tasks be named generically so the template is reusable?

Produce:

1. **reasoning**: Your chain-of-thought analysis (see above).

2. **board_title**: A concise, descriptive title for the template.

3. **tasks**: A flat list of 5-30 tasks forming a valid DAG. Each task has:
   - **id**: A unique identifier like "t1", "t2", etc.
   - **title**: A concise, actionable, GENERIC task title (reusable).
   - **depends_on**: An array of task IDs that must be completed before this \
task can begin. Use an empty array for root tasks.
   - **is_goal_node**: Set to true for exactly ONE task — the final \
completion task.

4. **Dependency graph rules**:
   - The graph MUST be a valid DAG — no circular dependencies.
   - Root tasks (empty depends_on) are tasks that can start immediately.
   - Create PARALLEL paths for independent work streams.
   - Create CONVERGENCE nodes — milestone tasks that depend on multiple \
parallel paths merging.
   - The final task MUST be a goal node (is_goal_node: true) representing \
overall completion. Nothing should depend on it.
   - Aim for a mix of sequential and parallel paths — avoid purely linear chains.
   - Each depends_on reference must point to a valid task ID.

IMPORTANT: Generate ALL content (board_title, task titles) in {language_name} \
({language}). The user's input is in this language and all output must match.
"""

TEMPLATE_SKELETON_USER_PROMPT = """\
Template request: {raw_input}

Classification:
- Domain: {domain}
- Complexity: {complexity}/5
- Key dimensions: {dimensions}
- Language: {language}

Questions and answers:
{qa_pairs}
{content_context}{research_context}"""
