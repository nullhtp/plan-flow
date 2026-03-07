## 1. Backend Data Model & Migration
- [ ] 1.1 Create `app/domains/templates/models.py` with TemplateCategory, BoardTemplate, TemplateTask, TemplateTaskDependency, TemplateSubtask SQLModels
- [ ] 1.2 Create Alembic migration for all template tables (template_category, board_template, template_task, template_task_dependency, template_subtask) with indexes, constraints, and FK cascades
- [ ] 1.3 Add category seed data in the migration (Career, Travel, Health & Fitness, Education, Finance, Home & Living, Projects, Events, Personal Development, Other)
- [ ] 1.4 Write unit tests for models (table creation, constraints, cascade deletes)

## 2. Backend Repository Layer
- [ ] 2.1 Create `app/domains/templates/repository.py` with TemplateCategoryRepository (list_all, get_by_id, get_by_slug, count_public_by_category)
- [ ] 2.2 Add BoardTemplateRepository (create, get_by_id, list_public, list_by_user, search, update, delete) with pagination support
- [ ] 2.3 Add TemplateTaskRepository, TemplateTaskDependencyRepository, TemplateSubtaskRepository (bulk create, list by template)
- [ ] 2.4 Write repository integration tests

## 3. Backend Service Layer
- [ ] 3.1 Create `app/domains/templates/service.py` with template CRUD operations
- [ ] 3.2 Implement `create_template_from_board()` — snapshot board structure (tasks, deps, subtasks) into template tables in a single transaction
- [ ] 3.3 Implement `create_board_from_template()` — create goal (status: active) + board + copy tasks/deps/subtasks from template in a single transaction
- [ ] 3.4 Implement list/search with pagination, category filtering, and visibility filtering
- [ ] 3.5 Write service unit tests (mock repositories)

## 4. Backend Schemas & Router
- [ ] 4.1 Create `app/domains/templates/schemas.py` with request/response Pydantic models (TemplateCategoryResponse, TemplateListResponse, TemplateDetailResponse, TemplateCreateRequest, TemplateUpdateRequest, CreateBoardFromTemplateRequest, etc.)
- [ ] 4.2 Create `app/domains/templates/router.py` with endpoints: GET /categories, POST /, GET /, GET /:id, PATCH /:id, DELETE /:id, POST /:id/create-board
- [ ] 4.3 Mount template router in main.py under `/api/templates`
- [ ] 4.4 Write API integration tests for all endpoints (auth, ownership, visibility, pagination)

## 5. Frontend Templates Feature Module
- [ ] 5.1 Regenerate API client from OpenAPI spec (orval) to pick up new template endpoints
- [ ] 5.2 Create `features/templates/` directory structure (components/, hooks/, types.ts)
- [ ] 5.3 Create hooks: `use-templates.ts` (list, search, paginate), `use-template-detail.ts`, `use-template-mutations.ts` (create, update, delete, create-board)
- [ ] 5.4 Create `use-categories.ts` hook for fetching and caching categories

## 6. Frontend Templates Browse Page
- [ ] 6.1 Create `/templates` route with TanStack Router
- [ ] 6.2 Build TemplateCard component (title, description, category badge, task count, creator)
- [ ] 6.3 Build TemplateGrid component with responsive layout
- [ ] 6.4 Build CategoryFilter component (sidebar/top bar with category list)
- [ ] 6.5 Build SearchBar component for keyword filtering
- [ ] 6.6 Build pagination controls
- [ ] 6.7 Add "Public Templates" / "My Templates" tab toggle
- [ ] 6.8 Add navigation link to templates page in app header/sidebar

## 7. Frontend Template Detail Page
- [ ] 7.1 Create `/templates/:id` route
- [ ] 7.2 Build TemplateDetail component showing metadata + task structure preview
- [ ] 7.3 Build "Use Template" flow with confirmation dialog and optional title override
- [ ] 7.4 Implement board creation from template with redirect to new board

## 8. Frontend Save as Template
- [ ] 8.1 Add "Save as Template" button to board view page
- [ ] 8.2 Build SaveAsTemplateDialog with title, description, category dropdown, visibility toggle
- [ ] 8.3 Integrate with create template API and show success/error feedback
- [ ] 8.4 Write component tests for the dialog

## 9. Update Project Conventions
- [ ] 9.1 Update `openspec/project.md` business rules to reflect that board creation supports both AI generation and templates
