# Change: Improve Template Generation Flow

## Why
The current template generation flow is a shallow, dialog-based experience: paste content, wait for a single LLM call, edit a flat task list, save. It lacks the adaptive questioning, research pipeline, streaming progress, and visual DAG preview that make board creation engaging and high-quality. Aligning template generation with the board creation flow will produce better templates and a more consistent user experience.

## What Changes
- **Replace the dialog-based generation flow with a full-page experience** at `/templates/generate` that mirrors the goal creation wizard
- **Add a "Describe" input tab** alongside the existing Text/Document/URL tabs, letting users describe what template they want in natural language (like goal input)
- **Add adaptive question flow** after content/description input: AI analyzes the input, classifies it, and generates 3-7 questions with max 2 follow-up rounds, readiness indicator, and sticky generate footer
- **Add content analysis for non-describe inputs**: for text/document/URL inputs, AI first extrazes and analyzes the content, then generates clarifying questions about it before generating the template
- **Convert template generation to SSE streaming** with the same multi-step pipeline as board generation (research -> skeleton -> review -> parallel enrichment) and real-time progress view
- **Replace the flat task list preview with a React Flow DAG board view** after generation, reusing the existing DagView component and TaskDetailPanel for editing
- **Enable full structural editing** in the board preview: edit task titles/descriptions/subtasks, add/remove tasks, modify dependency connections (all manual, no AI chat)
- **Add dual save action**: "Save as Template" (primary) with an option to also create a board immediately
- **Remove the GenerateTemplateDialog** component entirely

## Impact
- Affected specs: `board-templates`, `ai-pipeline`, `board-generation-progress`, `goal-input-ui`
- Affected code:
  - **Backend**: `domains/ai/service.py` (new template classification + question pipeline), `domains/ai/nodes/` (template classification/questions nodes), `domains/ai/prompts/` (template-specific prompts), `domains/templates/router.py` (new SSE endpoint, classification endpoint, question endpoints), `domains/templates/service.py` (template question flow state management)
  - **Frontend**: New `/templates/generate` route and page, template question form (reusing shared question components), template generation progress view (reusing BoardGenerationProgress), template board preview (reusing DagView + TaskDetailPanel in template mode), removal of `GenerateTemplateDialog`
  - **Shared**: Question field components already extracted to `shared/components/question-fields/`
