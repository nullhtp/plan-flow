## MODIFIED Requirements

### Requirement: Post-Answer Summary View
After the questioning phase is complete (all answers submitted, goal status is `answered`), the system SHALL display a summary view showing the goal title, original input, and all questions with their answers. The summary SHALL include a "Generate Board" button. When the user clicks "Generate Board", the wizard SHALL transition to a new `generating` step that displays the full-screen board generation progress view (see `board-generation-progress` spec). The summary view SHALL be accessible by navigating to the goal's page when it is in `answered` status.

#### Scenario: Summary displayed after questioning complete
- **WHEN** the user completes all answer rounds and the goal status transitions to `answered`
- **THEN** the page displays a summary of the goal, all questions, and all answers

#### Scenario: Generate Board transitions to generation progress
- **WHEN** the user clicks "Generate Board" on the summary view
- **THEN** the wizard transitions to the `generating` step and the full-screen generation progress view appears with an SSE connection to the board generation stream endpoint

#### Scenario: Summary accessible on return visit
- **WHEN** a user navigates to a goal that is in `answered` status
- **THEN** the summary view is displayed with all previously submitted data
