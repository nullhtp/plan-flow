## 1. Backend Data Model & Migration
- [x] 1.1 Create `app/domains/templates/models.py` with TemplateCategory, BoardTemplate, TemplateTask, TemplateTaskDependency, TemplateSubtask SQLModels
- [x] 1.2 Create Alembic migration for all template tables (template_category, board_template, template_task, template_task_dependency, template_subtask) with indexes, constraints, and FK cascades
- [x] 1.3 Add category seed data in the migration (Career, Travel, Health & Fitness, Education, Finance, Home & Living, Projects, Events, Personal Development, Other)
- [x] 1.4 Write unit tests for models (table creation, constraints, cascade deletes)

## 2. Backend Repository Layer
- [x] 2.1 Create `app/domains/templates/repository.py` with TemplateCategoryRepository (list_all, get_by_id, get_by_slug, count_public_by_category)
- [x] 2.2 Add BoardTemplateRepository (create, get_by_id, list_public, list_by_user, search, update, delete) with pagination support
- [x] 2.3 Add TemplateTaskRepository, TemplateTaskDependencyRepository, TemplateSubtaskRepository (bulk create, list by template)
- [x] 2.4 Write repository integration tests

## 3. Backend Service Layer
- [x] 3.1 Create `app/domains/templates/service.py` with template CRUD operations
- [x] 3.2 Implement `create_template_from_board()` — snapshot board structure (tasks, deps, subtasks) into template tables in a single transaction
- [x] 3.3 Implement `create_board_from_template()` — create goal (status: active) + board + copy tasks/deps/subtasks from template in a single transaction
- [x] 3.4 Implement list/search with pagination, category filtering, and visibility filtering
- [x] 3.5 Write service unit tests (mock repositories)

## 4. Backend Schemas & Router
- [x] 4.1 Create `app/domains/templates/schemas.py` with request/response Pydantic models (TemplateCategoryResponse, TemplateListResponse, TemplateDetailResponse, TemplateCreateRequest, TemplateUpdateRequest, CreateBoardFromTemplateRequest, etc.)
- [x] 4.2 Create `app/domains/templates/router.py` with endpoints: GET /categories, POST /, GET /, GET /:id, PATCH /:id, DELETE /:id, POST /:id/create-board
- [x] 4.3 Mount template router in main.py under `/api/templates`
- [x] 4.4 Write API integration tests for all endpoints (auth, ownership, visibility, pagination)

## 5. Frontend Templates Feature Module
- [x] 5.1 Regenerate API client from OpenAPI spec (orval) to pick up new template endpoints
- [x] 5.2 Create `features/templates/` directory structure (components/, hooks/, types.ts)
- [x] 5.3 Create hooks: `use-templates.ts` (list, search, paginate), `use-template-detail.ts`, `use-template-mutations.ts` (create, update, delete, create-board)
- [x] 5.4 Create `use-categories.ts` hook for fetching and caching categories

## 6. Frontend Templates Browse Page
- [x] 6.1 Create `/templates` route with TanStack Router
- [x] 6.2 Build TemplateCard component (title, description, category badge, task count, creator)
- [x] 6.3 Build TemplateGrid component with responsive layout
- [x] 6.4 Build CategoryFilter component (sidebar/top bar with category list)
- [x] 6.5 Build SearchBar component for keyword filtering
- [x] 6.6 Build pagination controls
- [x] 6.7 Add "Public Templates" / "My Templates" tab toggle
- [x] 6.8 Add navigation link to templates page in app header/sidebar

## 7. Frontend Template Detail Page
- [x] 7.1 Create `/templates/:id` route
- [x] 7.2 Build TemplateDetail component showing metadata + task structure preview
- [x] 7.3 Build "Use Template" flow with confirmation dialog and optional title override
- [x] 7.4 Implement board creation from template with redirect to new board

## 8. Frontend Save as Template
- [x] 8.1 Add "Save as Template" button to board view page
- [x] 8.2 Build SaveAsTemplateDialog with title, description, category dropdown, visibility toggle
- [x] 8.3 Integrate with create template API and show success/error feedback
- [x] 8.4 Write component tests for the dialog

## 9. Update Project Conventions
- [x] 9.1 Update `openspec/project.md` business rules to reflect that board creation supports both AI generation and templates
