## Context
Users want to create reusable templates from existing knowledge — text descriptions, project documents, how-to articles. Currently the only path to a template is: create a goal → answer questions → generate board → save board as template. This proposal adds a direct path: provide content → AI generates template → preview/edit → save.

## Goals / Non-Goals
- Goals:
  - Accept plain text, file uploads (PDF, DOCX, TXT, MD), and URLs as input sources
  - Generate full DAG structure (tasks, dependencies, subtasks, goal node) matching existing board-generation quality
  - Allow preview and editing before saving
  - Reuse existing DAG validation and template persistence logic
- Non-Goals:
  - Real-time collaborative editing of generated templates
  - Batch generation from multiple documents at once
  - OCR for scanned/image-based PDFs (text-based extraction only)
  - Template versioning or diff tracking

## Decisions

### Two-phase API (extract → generate) over single endpoint
- **Decision**: Separate content extraction (`/extract-content`) from AI generation (`/generate`) rather than a single upload-and-generate endpoint
- **Rationale**: Allows the frontend to show extraction progress separately, supports retry of just the AI generation without re-uploading, and keeps concerns clean (parsing vs AI)
- **Alternatives considered**: Single endpoint accepting file + generating in one request — rejected because it couples file handling with LLM calls, making error handling and retries harder

### Reuse board generation DAG patterns
- **Decision**: The template generation node outputs the same flat-task-with-depends_on structure used by board generation, validated by the same Kahn's algorithm
- **Rationale**: Consistency with existing patterns, no new DAG format to maintain, and generated templates are structurally identical to board-saved templates
- **Alternatives considered**: Simplified tree structure — rejected because it loses the parallel-path and convergence-node capabilities that make PlanFlow's DAGs valuable

### Client-side preview editing (not server round-trips)
- **Decision**: The preview/edit step operates entirely on the client side — users edit the draft JSON in the browser, then submit the final version to save
- **Rationale**: Faster editing experience, no server calls per edit, and the save endpoint validates the final structure anyway
- **Alternatives considered**: Server-side editing with PATCH calls — rejected as over-engineered for a preview step

### New dependencies for document parsing
- **Decision**: Use `pypdf` for PDF, `python-docx` for DOCX, `beautifulsoup4` + `html2text` for URL/HTML content
- **Rationale**: These are well-maintained, lightweight libraries. `pypdf` is pure Python (no system deps). `python-docx` is the standard for DOCX parsing. `beautifulsoup4` + `html2text` handle messy HTML well.
- **Alternatives considered**: `pdfplumber` (heavier, more features than needed), `unstructured` (too heavy for MVP), `trafilatura` for URL extraction (good but less widely used)

## Risks / Trade-offs
- **Large document content** → LLM context limits: mitigated by truncating extracted content to 50,000 characters with a warning to the user
- **URL fetching reliability** → some sites block scraping: mitigated by clear error messages and encouraging text paste as fallback
- **LLM output quality varies** → generated DAG may not be ideal: mitigated by the preview/edit step where users can fix the structure before saving
- **New dependencies** → increased backend footprint: mitigated by choosing lightweight, well-maintained packages

## Open Questions
- Should we add a "regenerate" button in the preview step to retry AI generation with the same content?
- Should we limit the number of template generations per user (rate limiting) to control AI costs?
