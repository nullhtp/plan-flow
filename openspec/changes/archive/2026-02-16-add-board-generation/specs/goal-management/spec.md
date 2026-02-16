## MODIFIED Requirements

### Requirement: Goal Status State Machine
The Goal model SHALL have a `status` field tracking pipeline progress through ordered states: `input`, `classifying`, `questioning`, `answered`, `generating`, `active`, `completed`, `archived`. M2 uses states through `answered`. M3 enables the `answered` -> `generating` -> `active` transitions when board generation is triggered. Transitions MUST be forward-only within a pipeline run (no skipping states). The `status` field SHALL be a string enum.

#### Scenario: Status transitions during goal creation
- **WHEN** a user creates a goal via `POST /goals`
- **THEN** the status transitions from `input` -> `classifying` -> `questioning` as the AI pipeline processes the goal

#### Scenario: Status transitions during answer submission
- **WHEN** a user submits answers and no follow-up questions are generated
- **THEN** the status transitions to `answered`

#### Scenario: Status remains questioning when follow-ups are generated
- **WHEN** a user submits initial answers and the AI generates follow-up questions
- **THEN** the status remains `questioning` until the follow-up answers are submitted

#### Scenario: Status transitions during board generation
- **WHEN** a user triggers board generation via `POST /goals/:id/generate-board`
- **THEN** the status transitions from `answered` -> `generating` while the AI processes, then to `active` when the board is successfully persisted

#### Scenario: Status reverts on generation failure
- **WHEN** the AI board generation fails (timeout, validation error, provider error)
- **THEN** the goal status reverts to `answered` so the user can retry
