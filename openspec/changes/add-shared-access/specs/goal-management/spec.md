## MODIFIED Requirements

### Requirement: Get Goal Endpoint
The system SHALL expose `GET /api/goals/:id` as an authenticated endpoint that returns the goal's current state including `id`, `title`, `original_input`, `status`, and relevant `ai_context` data (classification, questions, answers). Users SHALL be able to retrieve goals they own (goal.user_id) OR goals where they are a member (via goal_member). The response SHALL include `user_role` (string: `owner`, `editor`, or `viewer`) indicating the authenticated user's permission level.

#### Scenario: Retrieve own goal in questioning status
- **WHEN** an authenticated user requests `GET /api/goals/:id` for their own goal in `questioning` status
- **THEN** the response includes the goal fields, classification summary, current questions, and `user_role` set to `owner`

#### Scenario: Retrieve shared goal as member
- **WHEN** a goal member requests `GET /api/goals/:id` for a goal they are a member of
- **THEN** the response includes the goal fields and `user_role` set to the member's role

#### Scenario: Retrieve another user's goal (not shared)
- **WHEN** user A requests `GET /api/goals/:id` for user B's goal (and A is not a member)
- **THEN** the response status is 404
