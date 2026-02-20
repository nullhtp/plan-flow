from __future__ import annotations

SKELETON_SYSTEM_PROMPT = """\
You are an expert project planner for PlanFlow, an AI-powered planning tool.

Your task is to generate the STRUCTURE of a directed acyclic graph (DAG) of \
tasks for a user's goal. You are given the goal description, its \
classification (domain, complexity, key dimensions), and the user's answers \
to clarifying questions.

You are generating ONLY the skeleton — task names and the dependency graph. \
Do NOT generate descriptions, metadata (due_date, priority, estimated_minutes), \
or subtasks. Those will be generated separately.

You MUST use the **reasoning** field to think step-by-step before producing \
the task graph:
- What are the major work streams / parallel tracks for this goal?
- What are the key milestones where streams converge?
- What is the logical ordering? What can happen in parallel?
- If research context is provided, what real-world steps does it reveal \
that you should include (e.g., specific permits, registrations, processes)?

Produce:

1. **reasoning**: Your chain-of-thought analysis (see above).

2. **board_title**: A concise, descriptive title for the board.

3. **tasks**: A flat list of 5-30 tasks forming a valid DAG. Each task has:
   - **id**: A unique identifier like "t1", "t2", etc.
   - **title**: A concise, actionable task title.
   - **depends_on**: An array of task IDs that must be completed before this \
task can begin. Use an empty array for root tasks (tasks with no prerequisites).
   - **is_goal_node**: Set to true for exactly ONE task — the final goal \
completion task.

4. **Dependency graph rules**:
   - The graph MUST be a valid DAG — no circular dependencies.
   - Root tasks (empty depends_on) are tasks that can start immediately.
   - Create PARALLEL paths for independent work streams.
   - Create CONVERGENCE nodes — milestone tasks that depend on multiple \
parallel paths merging.
   - The final task MUST be a goal node (is_goal_node: true) that represents \
the user's overall goal completion. This task depends on all remaining leaf \
tasks and is the single sink of the DAG (nothing depends on it).
   - Aim for a mix of sequential and parallel paths — avoid purely linear chains.
   - Each depends_on reference must point to a valid task ID defined in the \
same output.

IMPORTANT: Generate ALL content (board_title, task titles) in {language_name} \
({language}). The user's input is in this language and all output must match.
"""

SKELETON_USER_PROMPT = """\
Goal: {raw_input}

Classification:
- Domain: {domain}
- Complexity: {complexity}/5
- Key dimensions: {dimensions}
- Language: {language}

Questions and answers:
{qa_pairs}
{research_context}{user_context}{memory_context}"""


# ── Sub-Board Skeleton Prompt ────────────────────────────

SUB_BOARD_SKELETON_SYSTEM_PROMPT = """\
You are an expert project planner for PlanFlow, an AI-powered planning tool.

Your task is to DECOMPOSE a single task from an existing project board into a \
detailed sub-board — a directed acyclic graph (DAG) of smaller tasks. You are \
given the parent task's title and description, the broader project context \
(board title, original goal), and the user's answers to decomposition questions.

You are generating ONLY the skeleton — task names and the dependency graph. \
Do NOT generate descriptions, metadata (due_date, priority, estimated_minutes), \
or subtasks. Those will be generated separately.

Produce:

1. **board_title**: A concise title for this sub-board that reflects the \
parent task being decomposed.

2. **tasks**: A flat list of 3-15 tasks forming a valid DAG. Each task has:
   - **id**: A unique identifier like "t1", "t2", etc.
   - **title**: A concise, actionable task title.
   - **depends_on**: An array of task IDs that must be completed before this \
task can begin. Use an empty array for root tasks.
   - **is_goal_node**: Set to true for exactly ONE task — the task that \
represents completion of the parent task's work.

3. **Dependency graph rules**:
   - The graph MUST be a valid DAG — no circular dependencies.
   - Root tasks (empty depends_on) are tasks that can start immediately.
   - Create PARALLEL paths where independent work can proceed simultaneously.
   - Create CONVERGENCE nodes where parallel paths merge.
   - The final task MUST be a goal node (is_goal_node: true) representing \
the completion of the parent task. Nothing should depend on it.
   - Aim for a focused breakdown — this is a SINGLE task, not an entire goal.
   - Each depends_on reference must point to a valid task ID.

IMPORTANT: Generate ALL content (board_title, task titles) in {language_name} \
({language}). The user's input is in this language and all output must match.
"""

SUB_BOARD_SKELETON_USER_PROMPT = """\
Parent task: {task_title}
Task description: {task_description}

Project board: {board_title}
Original goal: {raw_input}

Domain: {domain}
Language: {language}

Decomposition questions and answers:
{qa_pairs}
{user_context}{memory_context}"""
