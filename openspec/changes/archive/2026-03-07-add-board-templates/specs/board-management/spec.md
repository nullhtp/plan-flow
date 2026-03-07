## ADDED Requirements

### Requirement: Board Creation from Template
The system SHALL support creating a board from a template as an alternative to AI generation. When a board is created from a template, a Goal record SHALL be created with `status: active` (skipping the questioning and generation flow), `ai_context` containing `{"source": "template", "template_id": "<template_id>"}`, and `title` matching the template title or a user-provided override. A Board record SHALL be created linked to the goal with tasks, dependencies, and subtasks copied from the template. All tasks SHALL have `status: not_started`, all subtasks SHALL have `completed: false`. The template-created board SHALL behave identically to an AI-generated board for all subsequent operations (task updates, sub-board creation, chat, etc.). This updates the previous convention that board generation is purely dynamic — templates provide an alternative creation path.

#### Scenario: Board created from template has correct goal status
- **WHEN** a board is created from a template
- **THEN** the associated goal has `status: active` and does not go through the questioning or generating flow

#### Scenario: Template-created board supports all board operations
- **WHEN** a board is created from a template
- **THEN** the user can update tasks, create sub-boards, use task chat, and perform all operations available on AI-generated boards

#### Scenario: Template-created board has source metadata
- **WHEN** a board is created from a template with ID "abc-123"
- **THEN** the goal's `ai_context` contains `{"source": "template", "template_id": "abc-123"}`
