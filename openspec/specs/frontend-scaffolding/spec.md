# frontend-scaffolding Specification

## Purpose
TBD - created by archiving change setup-project-foundation. Update Purpose after archive.
## Requirements
### Requirement: Vite React TypeScript Application
The frontend SHALL be a React 19 application scaffolded with Vite and TypeScript in strict mode.

#### Scenario: Development server starts
- **WHEN** a developer runs the Vite dev server
- **THEN** the application compiles without errors and is accessible in a browser

### Requirement: TanStack Router Configuration
The frontend SHALL configure TanStack Router with type-safe routing and at least one root route that renders a placeholder page.

#### Scenario: Root route renders
- **WHEN** a user navigates to the root URL
- **THEN** a placeholder page is displayed

### Requirement: TanStack Query Configuration
The frontend SHALL configure a TanStack Query (React Query) client provider at the application root with sensible defaults.

#### Scenario: Query client is available
- **WHEN** any component in the application uses the `useQuery` hook
- **THEN** it has access to the configured QueryClient instance

### Requirement: Shadcn UI Initialization
The frontend SHALL initialize Shadcn/ui with Tailwind CSS v4 integration and include at least one installed component to validate the setup.

#### Scenario: Shadcn component renders correctly
- **WHEN** a Shadcn/ui component (e.g., Button) is used in the application
- **THEN** it renders with the expected Tailwind-based styles

### Requirement: Frontend Linting and Formatting
The frontend SHALL use Biome for linting and formatting, configured in `biome.json`.

#### Scenario: Biome checks pass on scaffolded code
- **WHEN** a developer runs `biome check` in the frontend directory
- **THEN** no lint errors or formatting violations are reported

### Requirement: Frontend Type Checking
The frontend SHALL have TypeScript configured in strict mode (`strict: true` in `tsconfig.json`) with all source files passing type checks.

#### Scenario: TypeScript type checking passes
- **WHEN** a developer runs `tsc --noEmit` in the frontend directory
- **THEN** no type errors are reported

### Requirement: Frontend Test Runner
The frontend SHALL include Vitest configured as the test runner with at least one placeholder test that passes.

#### Scenario: Vitest runs successfully
- **WHEN** a developer runs `vitest run` in the frontend directory
- **THEN** at least one test passes and the exit code is 0

