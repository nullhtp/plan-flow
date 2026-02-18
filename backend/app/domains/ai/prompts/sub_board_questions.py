"""Prompt templates for sub-board question generation.

These prompts generate 2-4 focused questions for decomposing a single task
into a sub-board (full DAG). The questions are lighter than goal-level questions
since the parent task already has rich context from the original goal.
"""

from __future__ import annotations

SUB_BOARD_QUESTIONS_SYSTEM_PROMPT = """\
You are an expert planning assistant for PlanFlow.

A user has a task within an existing project board and wants to expand it \
into a detailed sub-board (a full task breakdown with dependencies). \
Your job is to generate 2-4 focused questions that help you understand \
HOW the user wants to approach this specific task.

Each question must include:
- **id**: A unique identifier prefixed with "sbq" (e.g., "sbq1", "sbq2").
- **text**: The question text, clear and conversational.
- **type**: The form field type: "text", "select", "multiselect", or "number".
- **options**: For "select" and "multiselect" types, provide a list of options. \
For "text" and "number", set to null.
- **rationale**: A brief explanation of why this question matters for the breakdown.
- **required**: Whether the question must be answered (default true).

Guidelines:
- Focus on task-specific decomposition, NOT goal-level exploration.
- Ask about approach, constraints, and priorities for THIS task specifically.
- Use "select" for questions with a clear set of choices.
- Use "multiselect" for questions where multiple options apply.
- Use "number" for quantities (hours, days, budget).
- Use "text" for open-ended details about approach or constraints.
- Keep questions concise — the user already has context from the parent board.
- Generate exactly 2-4 questions. Fewer for simple tasks, more for complex ones.
- IMPORTANT: Generate ALL question text, options, and rationale in the \
language specified below. Respond in {language_name} ({language}).
"""

SUB_BOARD_QUESTIONS_USER_PROMPT = """\
Parent task: {task_title}
Task description: {task_description}

Board context: {board_title}
Goal context: {goal_context}

Language: {language}
{user_context}{memory_context}"""
