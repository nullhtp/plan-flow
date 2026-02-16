# git-hooks Specification

## Purpose
Git configuration and hooks. Covers .gitignore rules for the monorepo and pre-commit hooks for linting, formatting, and type checking across both frontend and backend.
## Requirements
### Requirement: Git Ignore Configuration
The repository SHALL include a `.gitignore` file that excludes generated files, dependencies, virtual environments, IDE settings, and OS-specific files for both the Python backend and TypeScript frontend.

#### Scenario: Generated and dependency files are ignored
- **WHEN** a developer runs `git status` after installing dependencies and building
- **THEN** `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, and other generated artifacts do not appear as untracked files

### Requirement: Pre-Commit Hooks
The repository SHALL configure pre-commit hooks that run fast code quality checks (formatting and linting) before each commit.

#### Scenario: Pre-commit hooks reject unformatted code
- **WHEN** a developer attempts to commit Python code that violates Ruff formatting rules
- **THEN** the pre-commit hook fails and the commit is rejected with an error message

#### Scenario: Pre-commit hooks reject frontend lint violations
- **WHEN** a developer attempts to commit TypeScript code that violates Biome rules
- **THEN** the pre-commit hook fails and the commit is rejected with an error message

### Requirement: Makefile Development Commands
The repository SHALL include a Makefile (or equivalent task runner) at the root with common development commands for both backend and frontend.

#### Scenario: Developer uses Makefile for common tasks
- **WHEN** a developer runs `make` without arguments
- **THEN** a list of available targets is displayed including lint, format, type-check, test, and codegen

