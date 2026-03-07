## 1. Backend: Content Extraction
- [ ] 1.1 Add document parsing utilities (`backend/app/domains/ai/content_extraction.py`) — PDF (`pypdf`), DOCX (`python-docx`), TXT, Markdown parsing
- [ ] 1.2 Add URL content fetcher using `httpx` with timeout, HTML→text conversion (`beautifulsoup4` + `html2text`)
- [ ] 1.3 Add `POST /api/templates/extract-content` endpoint — accepts file upload (multipart) or URL, validates file type/size, returns extracted text
- [ ] 1.4 Add Pydantic schemas for extraction request/response (`ContentExtractionResponse`)
- [ ] 1.5 Add dependencies to `pyproject.toml`: `pypdf`, `python-docx`, `beautifulsoup4`, `html2text`

## 2. Backend: AI Template Generation
- [ ] 2.1 Create Pydantic output schema `TemplateGenerationOutput` with nested `TemplateTaskOutput` in `backend/app/domains/ai/schemas.py`
- [ ] 2.2 Create template generation prompt in `backend/app/domains/ai/prompts/`
- [ ] 2.3 Create LangGraph node `generate_template` in `backend/app/domains/ai/nodes/generate_template.py`
- [ ] 2.4 Add DAG validation for generated template (reuse `dag_utils.py` Kahn's algorithm)
- [ ] 2.5 Add AI service method `generate_template_from_content()` in `backend/app/domains/ai/service.py`

## 3. Backend: Template Save & API Endpoints
- [ ] 3.1 Add `POST /api/templates/generate` endpoint — accepts content + optional title, calls AI service, returns draft template
- [ ] 3.2 Add `POST /api/templates/save-generated` endpoint — accepts edited draft, validates DAG, persists as BoardTemplate with tasks/deps/subtasks
- [ ] 3.3 Add Pydantic schemas for generate and save-generated requests/responses
- [ ] 3.4 Register new routes in template router

## 4. Frontend: Template Generation UI
- [ ] 4.1 Create `TemplateGenerateButton` component on `/templates` page
- [ ] 4.2 Create multi-step generation dialog/modal with three input tabs (Text, Document, URL)
- [ ] 4.3 Implement document upload with file type validation and size limit feedback
- [ ] 4.4 Implement URL input with extraction loading state
- [ ] 4.5 Create template preview/edit step — editable task list with titles, descriptions, subtasks, and dependency visualization
- [ ] 4.6 Add title, description, category, and visibility fields to preview step
- [ ] 4.7 Wire save action to `POST /api/templates/save-generated` and handle success/error states
- [ ] 4.8 Generate Orval hooks for new endpoints

## 5. Testing
- [ ] 5.1 Backend unit tests for content extraction (PDF, DOCX, TXT, MD parsing)
- [ ] 5.2 Backend unit tests for URL content fetching (mock HTTP responses)
- [ ] 5.3 Backend integration tests for extraction endpoint (file upload, URL, error cases)
- [ ] 5.4 Backend tests for template generation with mocked LLM responses (schema validation, DAG validation)
- [ ] 5.5 Backend integration tests for generate and save-generated endpoints
- [ ] 5.6 Frontend component tests for generation dialog steps and form validation
