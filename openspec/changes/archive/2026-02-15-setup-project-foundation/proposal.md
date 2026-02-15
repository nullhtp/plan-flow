# Change: Set up monorepo, tooling, and dev infrastructure

## Why
PlanFlow has no codebase yet. Every future milestone (auth, AI pipeline, board UI, etc.) depends on a working monorepo with configured tooling, local dev environment, and CI. This change establishes the foundation so that all subsequent work starts from a buildable, lintable, testable, and containerized project.

## What Changes
- Initialize monorepo with `/frontend` and `/backend` directories
- Scaffold FastAPI backend with domain-based structure, SQLModel, Alembic, PostgreSQL connection, Ruff, and Pyright
- Scaffold React 19 + TypeScript frontend with Vite, TanStack Router, TanStack Query, Shadcn/ui, Tailwind CSS v4, and Biome
- Set up OpenAPI code generation pipeline (FastAPI auto-generates spec, Orval generates TypeScript client + hooks)
- Create Docker Compose for local development (frontend, backend, PostgreSQL)
- Configure GitHub Actions CI (lint, format, type check, test runner)
- Set up Git infrastructure (.gitignore, pre-commit hooks via lint-staged)

## Impact
- Affected specs: none (no existing specs — all new capabilities)
- Affected code: entire repository (greenfield)
- This is M0 from the roadmap — all subsequent milestones depend on it
