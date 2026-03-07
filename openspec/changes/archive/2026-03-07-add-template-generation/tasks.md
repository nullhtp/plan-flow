## 1. Backend: Content Extraction
- [x] 1.1 Add document parsing utilities (`backend/app/domains/ai/content_extraction.py`) — PDF (`pypdf`), DOCX (`python-docx`), TXT, Markdown parsing
- [x] 1.2 Add URL content fetcher using `httpx` with timeout, HTML→text conversion (`trafilatura` — already a project dependency, used instead of beautifulsoup4 + html2text for DRY)
- [x] 1.3 Add `POST /api/templates/extract-content` endpoint — accepts file upload (multipart) or URL, validates file type/size, returns extracted text
- [x] 1.4 Add Pydantic schemas for extraction request/response (`ContentExtractionResponse`)
- [x] 1.5 Add dependencies to `pyproject.toml`: `pypdf`, `python-docx` (beautifulsoup4 + html2text replaced by existing `trafilatura`)

## 2. Backend: AI Template Generation
- [x] 2.1 Create Pydantic output schema `TemplateGenerationOutput` with nested `TemplateGenTaskOutput` in `backend/app/domains/ai/schemas.py`
- [x] 2.2 Create template generation prompt in `backend/app/domains/ai/prompts/generate_template.py`
- [x] 2.3 Add `generate_template_from_content()` as a simple structured output LLM call in `backend/app/domains/ai/service.py` (no LangGraph node needed — KISS)
- [x] 2.4 Add DAG validation for generated template (reuse `dag_utils.py` Kahn's algorithm via `_validate_template_dag`)
- [x] 2.5 Add AI service method `generate_template_from_content()` in `backend/app/domains/ai/service.py`

## 3. Backend: Template Save & API Endpoints
- [x] 3.1 Add `POST /api/templates/generate` endpoint — accepts content + optional title, calls AI service, returns draft template
- [x] 3.2 Add `POST /api/templates/save-generated` endpoint — accepts edited draft, validates DAG, persists as BoardTemplate with tasks/deps/subtasks
- [x] 3.3 Add Pydantic schemas for generate and save-generated requests/responses in `backend/app/domains/templates/schemas.py`
- [x] 3.4 Register new routes in template router (placed before `/{template_id}` to avoid path conflicts)

## 4. Frontend: Template Generation UI
- [x] 4.1 Add "Generate Template" button on `/templates` page header
- [x] 4.2 Create `GenerateTemplateDialog` multi-step dialog with three input tabs (Text, Document, URL)
- [x] 4.3 Implement document upload with file type validation and size limit feedback
- [x] 4.4 Implement URL input with extraction loading state
- [x] 4.5 Create template preview/edit step — editable task list with titles, descriptions, subtasks, and dependency visualization
- [x] 4.6 Add title, description, category, and visibility fields to preview step
- [x] 4.7 Wire save action to `POST /api/templates/save-generated` and handle success/error states
- [x] 4.8 Create custom hooks for new endpoints in `use-template-generation.ts` (manual hooks following existing customFetch pattern)

## 5. Testing
- [x] 5.1 Backend unit tests for content extraction (TXT, MD parsing, size limits, truncation, unsupported types)
- [x] 5.2 Backend integration tests for extraction endpoint (file upload, unsupported type, no input)
- [x] 5.3 Backend integration tests for generate endpoint (mocked LLM, content too short)
- [x] 5.4 Backend integration tests for save-generated endpoint (valid save, cycle rejection, missing goal node)
- [x] 5.5 Frontend component tests for GenerateTemplateDialog (render, tabs, disabled states)
