## ADDED Requirements

### Requirement: Template Generation AI Node
The system SHALL provide a LangGraph node `generate_template` that accepts a text input (up to 50,000 characters) and produces a structured template output. The node SHALL use structured output enforcement via a Pydantic schema (`TemplateGenerationOutput`) containing: `suggested_title` (string), `suggested_description` (string), `suggested_category_slug` (string), and `tasks` (list of `TemplateTaskOutput` with `title`, `description`, `is_goal_node`, `subtasks` list, and `depends_on` list of task indices). The node SHALL instruct the LLM to: (1) analyze the input content and identify discrete actionable steps, (2) determine logical dependencies between steps, (3) structure them as a DAG with parallel paths where applicable, convergence nodes where paths merge, and exactly one goal node as the final sink. The node SHALL use the same LLM model tier as board generation. The prompt SHALL be stored in `backend/app/domains/ai/prompts/`.

#### Scenario: Generate template from descriptive text
- **WHEN** the node receives "Steps to relocate to a new city: research neighborhoods, find an apartment, set up utilities, change address, pack belongings, hire movers, move in"
- **THEN** the output contains tasks for each step with logical dependencies (e.g., "find an apartment" depends on "research neighborhoods"; "move in" depends on "pack belongings" and "hire movers") and a goal node

#### Scenario: Generate template from document content
- **WHEN** the node receives extracted content from a project management PDF with phases and milestones
- **THEN** the output maps document phases to task groups with dependencies reflecting the document's ordering and milestone convergence points

#### Scenario: Output conforms to Pydantic schema
- **WHEN** template generation completes
- **THEN** the output is validated against `TemplateGenerationOutput` schema with no parsing errors

#### Scenario: Content with no clear structure
- **WHEN** the node receives vague or unstructured text like "I want to be healthier"
- **THEN** the node still produces a reasonable template with common health-related tasks and dependencies, using its knowledge to fill gaps

### Requirement: Template Generation Prompt
The system SHALL store the template generation system prompt in `backend/app/domains/ai/prompts/`. The prompt SHALL instruct the LLM to: (1) extract actionable tasks from the provided content, (2) preserve the user's original language and terminology, (3) create dependency edges that reflect logical ordering and prerequisites, (4) identify tasks that can run in parallel, (5) add convergence nodes where multiple parallel paths must complete before proceeding, (6) create exactly one goal node that represents the overall completion, (7) suggest an appropriate category from the available list, and (8) generate a concise title and description for the template. The prompt SHALL include the list of available category slugs for category suggestion.

#### Scenario: Prompt preserves user terminology
- **WHEN** the input content uses domain-specific terms (e.g., "sprint planning", "retrospective")
- **THEN** the generated task titles preserve those terms rather than substituting generic alternatives

#### Scenario: Prompt includes category options
- **WHEN** the template generation prompt is rendered
- **THEN** it includes the list of valid category slugs so the LLM can suggest an appropriate one
