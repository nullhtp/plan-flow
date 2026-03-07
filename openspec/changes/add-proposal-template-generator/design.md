## Context
Users currently can only create templates by saving existing boards. This change adds AI-powered template generation from unstructured text and document uploads, creating a new entry point for template creation. It introduces a new AI node, document parsing dependencies, and a file upload endpoint.

## Goals / Non-Goals
- Goals:
  - Allow users to generate structured board templates from pasted text or uploaded documents
  - Support common document formats (TXT, MD, PDF, DOCX)
  - Produce valid DAG structures with dependencies, parallel paths, and a goal node
  - Provide a review/edit step before saving the generated template
- Non-Goals:
  - OCR for scanned/image-based PDFs (text-based extraction only)
  - Real-time collaborative editing of generated templates
  - Support for spreadsheet formats (CSV, XLSX)
  - Template generation from images or screenshots

## Decisions
- **Reuse existing template persistence**: The generated output maps directly to the existing `BoardTemplate`, `TemplateTask`, `TemplateTaskDependency`, and `TemplateSubtask` models — no new tables needed.
- **Single AI node, two entry points**: Both text and document endpoints extract text first, then share the same `generate_template_from_text` LangGraph node. This avoids duplicating AI logic.
- **Document parsing libraries**: Use `pymupdf` for PDF (fast, no external dependencies) and `python-docx` for DOCX. Both are well-maintained and lightweight.
- **Text truncation at 50K characters**: Prevents excessive token usage and LLM timeouts. Most project documents fit well within this limit.
- **Draft-then-save flow**: The AI generates the template structure, but the user reviews and edits metadata before persisting. This avoids creating low-quality templates from misunderstood input.

## Risks / Trade-offs
- **LLM quality variability** → Mitigated by structured output enforcement (Pydantic schema) and DAG validation before persistence. Invalid DAGs are rejected.
- **Large document processing time** → Mitigated by 50K character limit and 20-second LLM timeout. The endpoint returns a clear error on timeout rather than hanging.
- **PDF text extraction quality** → PyMuPDF handles most text-based PDFs well but will not extract text from scanned images. This is documented as a non-goal.

## Open Questions
- Should we add a "regenerate" button in the UI for users unhappy with the first AI result?
- Should generated templates be marked with a `source: "ai-generated"` metadata field for analytics?
