.DEFAULT_GOAL := help

.PHONY: help lint format type-check test codegen export-openapi check

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Backend ──────────────────────────────────────────────

lint-backend: ## Run backend linting (ruff)
	cd backend && uv run ruff check .

format-backend: ## Run backend formatting (ruff)
	cd backend && uv run ruff format .

format-check-backend: ## Check backend formatting (ruff)
	cd backend && uv run ruff format --check .

type-check-backend: ## Run backend type checking (pyright)
	cd backend && uv run pyright

test-backend: ## Run backend tests (pytest)
	cd backend && uv run pytest

# ── Frontend ─────────────────────────────────────────────

lint-frontend: ## Run frontend linting (biome)
	cd frontend && pnpm run lint

format-frontend: ## Run frontend formatting (biome)
	cd frontend && pnpm run format

format-check-frontend: ## Check frontend formatting (biome)
	cd frontend && pnpm run format:check

type-check-frontend: ## Run frontend type checking (tsc)
	cd frontend && pnpm run type-check

test-frontend: ## Run frontend tests (vitest)
	cd frontend && pnpm run test

# ── Combined ─────────────────────────────────────────────

lint: lint-backend lint-frontend ## Run all linters

format: format-backend format-frontend ## Run all formatters

type-check: type-check-backend type-check-frontend ## Run all type checkers

test: test-backend test-frontend ## Run all tests

check: lint format-check-backend format-check-frontend type-check test ## Run all checks (CI equivalent)

# ── Code Generation ──────────────────────────────────────

export-openapi: ## Export OpenAPI spec from backend
	cd backend && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../frontend/openapi.json

codegen: export-openapi ## Generate TypeScript API client from OpenAPI spec
	cd frontend && pnpm run codegen
