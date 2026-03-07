## 1. Backend: Template Classification & Question Pipeline

- [x] 1.1 Add template classification prompt module (`prompts/generate_template_questions.py`) that adapts classification for template context — supports both description-based and content-based inputs
- [x] 1.2 Add `classify_template_content` AI service function that runs the classification pipeline on template input (description text or extracted content), returns classification output (domain, complexity, confidence, dimensions, language)
- [x] 1.3 Add `generate_template_questions` AI service function that generates 3-7 questions based on template classification output and optional source content context
- [x] 1.4 Add `generate_template_follow_up_questions` AI service function for a single follow-up round (2-4 questions), capped at 1 follow-up round total
- [x] 1.5 Add template question/readiness Pydantic schemas (`TemplateClassifyResponse`, `TemplateQuestionSchema`, `TemplateAnswerSubmission`, `TemplateReadinessSchema`) in `domains/templates/schemas.py`

## 2. Backend: Template Classification & Question Endpoints

- [x] 2.1 Add `POST /api/templates/classify` endpoint — accepts `{ input_type: "describe" | "text" | "file" | "url", content: string, title?: string }`, runs classification, returns questions + classification data. For file/URL inputs, content is the pre-extracted text.
- [x] 2.2 Add `POST /api/templates/answers` endpoint — accepts round answers + template session context (classification, previous Q&A), generates follow-up questions (max 1 follow-up round) + readiness assessment, returns next questions or signals "ready"
- [x] 2.3 Add template session state management — store classification + Q&A rounds in a lightweight server-side or client-side session (no database table needed; use a signed JWT or pass full context in request body)

## 3. Backend: Streaming Template Generation Pipeline

- [x] 3.1 Add `generate_template_stream` async generator function in AI service that mirrors `generate_board_stream`: research -> skeleton -> review -> parallel enrichment, using template-specific prompts and incorporating Q&A context + source content
- [x] 3.2 Add template-specific skeleton prompt that generates template-appropriate tasks (more generic/reusable than personal board tasks), incorporating the source content and Q&A answers
- [x] 3.3 Add `POST /api/templates/generate/stream` SSE endpoint — accepts template session context (classification, Q&A rounds, source content, title), streams generation events (same event types as board generation: `research_started`, `research_progress`, `research_complete`, `skeleton_ready`, `task_enriched`, `generation_complete`, `generation_error`)
- [x] 3.4 Refactor `generate_board_stream` and `generate_template_stream` to share common research/enrichment logic where possible (avoid code duplication)

## 4. Backend: Save Generated Template with Full Structural Edits

- [x] 4.1 Modify `POST /api/templates/save-generated` to accept the full edited template structure including added/removed tasks and modified dependencies from the DAG editor
- [x] 4.2 Add DAG validation for user-edited template structure (handle edge cases: disconnected nodes, missing goal node, cycles introduced by manual edits)
- [x] 4.3 Add optional `create_board` boolean flag to `save-generated` that also creates a board from the saved template in the same transaction

## 5. Frontend: Template Generation Page & Input Step

- [x] 5.1 Create `/templates/generate` route and page component with multi-step wizard (input -> questions -> generating -> preview)
- [x] 5.2 Build input step with 4 tabs: "Describe" (textarea + example suggestions like goal input), "Text" (textarea for pasting content), "Document" (file upload), "URL" (URL input)
- [x] 5.3 Add content extraction integration for Document and URL tabs (reuse existing `useExtractContent` hook)
- [x] 5.4 Add classification submission — on "Continue" from any tab, call `POST /api/templates/classify` and transition to questions step
- [x] 5.5 Remove `GenerateTemplateDialog` component and update `/templates` page to navigate to `/templates/generate` instead of opening the dialog

## 6. Frontend: Template Question Flow

- [x] 6.1 Build template question form using shared question field components (`shared/components/question-fields/`) with `compact` mode
- [x] 6.2 Implement growing form pattern with max 2 rounds (initial + 1 follow-up) — reuse `DynamicQuestionForm` patterns but with round cap
- [x] 6.3 Add readiness indicator and sticky generate footer (reuse `ReadinessIndicator` and `GenerateFooter` components or patterns)
- [x] 6.4 Add "Generate Template" button in footer that triggers the streaming generation step
- [x] 6.5 Add template-specific question hooks (`useTemplateClassify`, `useTemplateSubmitAnswers`)

## 7. Frontend: Template Generation Progress View

- [x] 7.1 Reuse `BoardGenerationProgress` component and `useBoardGenerationStream` hook with configurable SSE URL pointing to `POST /api/templates/generate/stream`
- [x] 7.2 Pass `onComplete` callback that transitions to the preview step (instead of navigating to a board page)
- [x] 7.3 Store streaming generation results (tasks, edges, subtasks) in local state for the preview step

## 8. Frontend: DAG Board Preview with Structural Editing

- [x] 8.1 Create `TemplatePreviewBoard` component that renders `DagView` with template data from local state (not API-backed)
- [x] 8.2 Adapt `DagView` to accept a `mode` prop (`"board" | "template-preview"`) — in template-preview mode, data comes from props/local state instead of API queries
- [x] 8.3 Add "Add Task" control that creates a new unconnected task node in the DAG
- [x] 8.4 Enable edge creation via React Flow connection handles (drag from source to target to create dependency)
- [x] 8.5 Enable edge deletion (click edge -> delete, or right-click context menu)
- [x] 8.6 Enable task deletion via TaskDetailPanel or context menu (with dependency cleanup)
- [x] 8.7 Adapt `TaskDetailPanel` for template-preview mode — edit title, description, subtasks (add/remove/edit), priority, estimated_minutes. No status field since template tasks are always `not_started`.
- [x] 8.8 Add real-time DAG validation feedback — warn user if edits create cycles or leave no goal node

## 9. Frontend: Save & Create Board Actions

- [x] 9.1 Add save footer with "Save Template" primary button and "Also create a board from this template" checkbox
- [x] 9.2 Add template metadata fields in the save step (title, description, category dropdown, visibility toggle) — pre-filled from AI suggestions
- [x] 9.3 Integrate with `POST /api/templates/save-generated` (with optional `create_board` flag)
- [x] 9.4 On successful save: navigate to template detail page, or to the new board if "create board" was checked

## 10. Testing & Validation

- [x] 10.1 Backend: Add integration tests for template classification endpoint
- [x] 10.2 Backend: Add integration tests for template answers endpoint (round 1 + follow-up)
- [x] 10.3 Backend: Add integration tests for streaming template generation SSE endpoint
- [x] 10.4 Backend: Add unit tests for template DAG validation with user edits (cycles, disconnected nodes, missing goal node)
- [x] 10.5 Frontend: Add component tests for template generation page wizard flow
- [x] 10.6 Frontend: Add component tests for template DAG preview editing (add/remove tasks, edges)
- [x] 10.7 Verify existing template CRUD functionality still works (list, detail, save from board, use template)
