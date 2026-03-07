## Context
Board templates introduce a new domain (`templates`) that interacts with the existing `boards` domain. Templates capture the full structure of a board (tasks, dependencies, subtasks) as a reusable blueprint. Users can create templates from their own boards and browse/use templates created by others. This is a cross-cutting feature spanning backend (new domain, new tables, new endpoints) and frontend (new feature module, new routes).

## Goals / Non-Goals
- Goals:
  - Users can save any board as a reusable template
  - Users can browse templates by category and search by keyword
  - Users can create a board instantly from a template (no AI involvement)
  - Templates support public/private visibility
  - Categories are system-managed (predefined set, expandable)
- Non-Goals:
  - Template versioning (updating a template does not update boards created from it)
  - Template ratings or popularity metrics (future enhancement)
  - AI-enhanced templates (e.g., AI customizing a template based on user context)
  - Template collaboration or co-editing
  - Forking or branching templates

## Decisions

### Separate domain for templates
- Decision: Create `app/domains/templates/` as a new domain rather than adding to `boards/`
- Rationale: Templates are a distinct concern with their own models, CRUD, and visibility logic. Keeps `boards/` focused on active board management. Follows the existing domain-based architecture pattern.
- Alternatives considered: Adding template tables/logic to `boards/` domain — rejected because it would bloat an already large domain and mix template browsing concerns with board execution.

### Template data model mirrors board structure
- Decision: Template stores a denormalized snapshot of the board structure (`template_task`, `template_task_dependency`, `template_subtask`) rather than referencing the original board.
- Rationale: Templates must be independent of the source board — deleting or modifying the original board should not affect the template. Denormalized snapshot is simpler to reason about and avoids cascading issues.
- Alternatives considered: Storing template as a JSON blob — rejected because it makes querying/filtering harder and prevents relational integrity on template tasks.

### System-managed categories
- Decision: Categories are stored in a `template_category` table, seeded with a predefined set, and expandable by system admins (not users). Users select from existing categories when saving a template.
- Rationale: Prevents category proliferation and keeps browsing experience clean. Can be expanded as usage patterns emerge.
- Alternatives considered: Free-form tags — rejected for MVP to avoid tag soup and inconsistent categorization.

### Board creation from template
- Decision: Creating a board from a template creates a new Goal (with status `active`, skipping the questioning flow) and a new Board with tasks/subtasks/dependencies copied from the template. The new board is fully independent of the template.
- Rationale: Boards require a parent goal in the current architecture. Creating a goal ensures consistency with the existing data model and navigation (goals list → board). Skipping to `active` status avoids the AI questioning flow since the template already provides structure.
- Alternatives considered: Creating a board without a goal — rejected because it would break the existing goal→board relationship and require extensive frontend changes.

### Visibility model
- Decision: Templates have a `visibility` field (`private` | `public`). Private templates are only visible to their creator. Public templates are visible to all users in the browse page. The creator can toggle visibility.
- Rationale: Simple two-tier model covers the "save for myself" and "share with others" use cases without introducing complex permission systems.

## Risks / Trade-offs
- **Data duplication**: Templates duplicate board structure. A board with 20 tasks creates 20 template_task records. Acceptable for MVP scale.
- **Category management**: System-managed categories require occasional manual updates. Mitigated by starting with a broad set covering common goal domains.
- **Goal creation side effect**: Creating a board from a template auto-creates a goal. Users might find it odd to see a "goal" they didn't describe. Mitigated by using the template title as the goal title and setting a `source: "template"` marker on the goal.

## Open Questions
- Should there be a limit on the number of templates a user can create? (Suggest: no limit for MVP)
- Should public templates show the creator's username? (Suggest: yes, for attribution)
