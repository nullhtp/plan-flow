## MODIFIED Requirements

### Requirement: Board Loading State
The system SHALL display a loading state while the board data is being fetched. The loading state SHALL show a centered spinner or placeholder indicating the graph is loading. When the user arrives at a board page via auto-navigation from the generation progress view, the board data SHALL already be persisted and load quickly without a prolonged loading state.

#### Scenario: Board loading state
- **WHEN** a user navigates to `/boards/:boardId` and the data is loading
- **THEN** a loading indicator is displayed

#### Scenario: Board loaded successfully
- **WHEN** the board data finishes loading
- **THEN** the loading indicator is replaced with the actual DAG graph

#### Scenario: Post-generation board load
- **WHEN** a user arrives at the board page via auto-navigation from generation progress
- **THEN** the board data loads from the server (already persisted during generation) and the DAG graph renders promptly
