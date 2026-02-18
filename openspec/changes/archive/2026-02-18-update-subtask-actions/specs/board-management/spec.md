## MODIFIED Requirements

### Requirement: Subtask Data Model
The system SHALL store subtasks as database records with the following fields: `id` (UUID primary key), `task_id` (FK to Task), `title` (string), `completed` (boolean, default false), `position` (varchar(50), fractional index string for ordering), `action_label` (varchar(60), nullable, short button text for AI action), `action_icon` (varchar(20), nullable, semantic icon category), `action_prompt` (text, nullable, max 500 chars, prompt to send to task chat), `created_at`, and `updated_at`. Subtasks SHALL be returned ordered by `position` ascending (lexicographic sort) within their parent task. Subtasks are single-level only — no nested subtasks. The action fields (`action_label`, `action_icon`, `action_prompt`) represent an optional AI-generated action button for the subtask. When all three are null, the subtask has no AI action available.

#### Scenario: Subtask created for a task
- **WHEN** a user creates a subtask with title "Research visa requirements" for a task
- **THEN** a Subtask record is created with `completed` set to false, a fractional index `position`, and null action fields

#### Scenario: Subtask ordering within task
- **WHEN** a task has 3 subtasks with fractional index positions
- **THEN** subtasks are returned in lexicographic position order

#### Scenario: Subtask with AI action
- **WHEN** the enrichment pipeline generates a subtask "Draft rental agreement" with an AI action
- **THEN** the Subtask record has `action_label: "Generate agreement draft"`, `action_icon: "generate"`, `action_prompt: "Generate a rental agreement draft based on the task context"`

#### Scenario: Subtask without AI action
- **WHEN** the enrichment pipeline generates a subtask "Sign documents at notary"
- **THEN** the Subtask record has `action_label: null`, `action_icon: null`, `action_prompt: null`

## ADDED Requirements

### Requirement: Subtask Action Fields Migration
The system SHALL include an Alembic migration that adds three nullable columns to the `subtask` table: `action_label` (varchar(60)), `action_icon` (varchar(20)), and `action_prompt` (text). The migration SHALL be non-destructive — existing subtask records retain their current data with null action fields.

#### Scenario: Migration adds action columns
- **WHEN** the Alembic migration runs
- **THEN** the `subtask` table has new nullable columns `action_label`, `action_icon`, and `action_prompt`
- **AND** existing subtask records have null values for all three new columns
