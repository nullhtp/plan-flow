# Change: Add Template Generation from Text and Documents

## Why
Currently, board templates can only be created by saving an existing board. Users who have a plan described in text (e.g., a project brief, a checklist document, meeting notes, or a pasted list of steps) have no way to turn that into a reusable template without first manually creating a board. Adding AI-powered template generation from text or uploaded documents removes this friction and unlocks a powerful new creation path.

## What Changes
- Add a new API endpoint `POST /api/templates/generate` that accepts raw text or a document file and uses the AI pipeline to produce a structured board template (tasks, dependencies, subtasks)
- Add a new LangGraph node for parsing unstructured text/documents into a DAG-shaped task structure
- Support two input modes: **plain text** (pasted content) and **document upload** (PDF, DOCX, TXT, Markdown)
- Add a frontend "Generate from Text" flow on the templates page with a text input area and file upload option
- The generated template is returned as a draft for the user to review, edit metadata (title, description, category, visibility), and confirm before saving

## Impact
- Affected specs: `board-templates`, `ai-pipeline`
- Affected code: `backend/app/domains/ai/` (new node + prompt), `backend/app/domains/boards/` (template service), `frontend/src/features/board/` (template UI)
