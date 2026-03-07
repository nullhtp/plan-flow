## ADDED Requirements

### Requirement: Template Generation Node
The system SHALL include a LangGraph node `generate_template_from_text` that accepts unstructured text and produces a structured DAG of tasks suitable for a board template. The node SHALL: (1) analyze the input text to identify actionable tasks, milestones, and dependencies, (2) organize tasks into a valid DAG with parallel paths where appropriate, convergence nodes for merging work streams, and exactly one goal node as the DAG sink, (3) generate subtasks for complex tasks, (4) infer a suggested title and description from the content if not provided by the user. The output SHALL conform to a Pydantic schema (`TemplateGenerationOutput`) containing: `title` (string), `description` (string), `tasks` (list of task objects with `title`, `description`, `is_goal_node`, `priority`, `estimated_minutes`, `subtasks`, `depends_on`). The node SHALL use structured output enforcement (`.with_structured_output()`) to guarantee valid JSON output.

#### Scenario: Generate DAG from step-by-step text
- **WHEN** the node receives text containing sequential steps like "1. Research 2. Plan 3. Execute 4. Review"
- **THEN** it produces a DAG with tasks in sequence, each depending on the previous, plus a goal node

#### Scenario: Generate DAG from project brief with parallel tracks
- **WHEN** the node receives a project brief mentioning independent work streams (e.g., "frontend development" and "backend development" that converge at "integration testing")
- **THEN** it produces a DAG with parallel paths and a convergence node

#### Scenario: Generate subtasks for complex tasks
- **WHEN** the node encounters a task with multiple sub-items (e.g., "Set up infrastructure: install Docker, configure CI, set up monitoring")
- **THEN** it creates a single task with subtasks for each sub-item

#### Scenario: AI rejects non-actionable content
- **WHEN** the node receives text with no identifiable tasks (e.g., a poem or random text)
- **THEN** it returns an error indicator that the content could not be parsed into tasks

### Requirement: Template Generation Prompt
The system SHALL include a dedicated prompt for the template generation node stored in `backend/app/domains/ai/prompts/`. The prompt SHALL instruct the LLM to: (1) extract actionable tasks from the provided text, (2) identify logical dependencies between tasks, (3) detect parallel work streams and create appropriate convergence points, (4) designate exactly one goal node representing the overall objective, (5) suggest a concise title and description summarizing the template, (6) generate subtasks for tasks that contain multiple sub-steps. The prompt SHALL handle diverse input formats including: numbered lists, bullet points, free-form paragraphs, checklists, project plans, and meeting notes.

#### Scenario: Prompt handles numbered list input
- **WHEN** the input is a numbered list of steps
- **THEN** the LLM produces tasks reflecting the list order with sequential dependencies

#### Scenario: Prompt handles free-form paragraph input
- **WHEN** the input is a multi-paragraph project description without explicit structure
- **THEN** the LLM identifies implicit tasks and dependencies from the narrative

### Requirement: Document Text Extraction
The system SHALL provide a utility module for extracting plain text from uploaded documents. Supported formats and extraction methods: (1) `.txt` — read as UTF-8 text, (2) `.md` — read as UTF-8 text (preserve markdown for AI context), (3) `.pdf` — extract text using `pymupdf` (PyMuPDF), (4) `.docx` — extract text using `python-docx`. The extracted text SHALL be truncated to 50000 characters if the document exceeds that length. The utility SHALL raise a clear error for unsupported file types or corrupted files.

#### Scenario: Extract text from PDF
- **WHEN** a PDF file with 10 pages of text is provided
- **THEN** the utility extracts all text content concatenated by page

#### Scenario: Extract text from DOCX
- **WHEN** a DOCX file with paragraphs and bullet lists is provided
- **THEN** the utility extracts all paragraph text preserving structure

#### Scenario: Corrupted file handling
- **WHEN** a file with a `.pdf` extension but invalid content is provided
- **THEN** the utility raises a descriptive error indicating the file could not be parsed
