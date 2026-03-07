## 1. Backend — Document Text Extraction
- [ ] 1.1 Add `pymupdf` and `python-docx` dependencies to `pyproject.toml`
- [ ] 1.2 Create `backend/app/domains/ai/text_extraction.py` with extraction functions for `.txt`, `.md`, `.pdf`, `.docx`
- [ ] 1.3 Add file type validation and size limit (5MB) logic
- [ ] 1.4 Write unit tests for text extraction (each format + error cases)

## 2. Backend — AI Template Generation Node
- [ ] 2.1 Create Pydantic schema `TemplateGenerationOutput` in `backend/app/domains/ai/schemas.py`
- [ ] 2.2 Create prompt file `backend/app/domains/ai/prompts/generate_template.py`
- [ ] 2.3 Create LangGraph node `generate_template_from_text` in `backend/app/domains/ai/nodes/generate_template.py`
- [ ] 2.4 Write tests for the generation node (mocked LLM, diverse input formats)

## 3. Backend — API Endpoints
- [ ] 3.1 Add `generate_template` service method in board template service
- [ ] 3.2 Create `POST /api/templates/generate` endpoint (text input)
- [ ] 3.3 Create `POST /api/templates/generate-from-document` endpoint (file upload)
- [ ] 3.4 Write integration tests for both endpoints (success + error cases)

## 4. Frontend — Template Generation UI
- [ ] 4.1 Add "Generate from Text" tab/section to the templates page
- [ ] 4.2 Build text input area with placeholder guidance
- [ ] 4.3 Build document upload drop zone with file type/size validation
- [ ] 4.4 Implement generation loading state and error handling
- [ ] 4.5 Build template preview component showing generated tasks/dependencies
- [ ] 4.6 Build metadata edit form (title, description, category, visibility) with save action
- [ ] 4.7 Regenerate Orval types/hooks after backend endpoints are ready
