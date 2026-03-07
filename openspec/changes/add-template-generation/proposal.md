# Change: Add Template Generation from Text, Documents, and URLs

## Why
Currently, templates can only be created by saving an existing board — users must first go through the full AI goal → board generation flow, then save the result. There is no way to directly create a template from external knowledge sources like a checklist document, a how-to article, or a plain-text description. This forces users to re-do work that already exists in other formats.

## What Changes
- Add a new AI pipeline node that generates a full DAG template structure (tasks, dependencies, subtasks, goal node) from user-provided text, uploaded documents (PDF, DOCX, TXT, Markdown), or fetched URL content
- Add a backend endpoint for template generation that accepts text input and/or file uploads and/or a URL, processes the content, and returns a draft template structure for preview
- Add a backend endpoint for document/URL content extraction (parsing uploaded files and fetching URL content)
- Add a "Generate Template" UI flow on the `/templates` page: input form → AI generation → preview/edit → save
- The preview step lets users review and modify the generated structure before saving as a template

## Impact
- Affected specs: `board-templates`, `ai-pipeline`
- Affected code:
  - `backend/app/domains/ai/` — new generation node, prompt, and schemas
  - `backend/app/domains/boards/` — template generation endpoint
  - `frontend/src/features/board/` or new `templates/` feature — generation UI
  - New document parsing utilities in backend
