## ADDED Requirements

### Requirement: Templates Tab Browse Simplification in Simple Mode

While Simple mode is enabled, the Templates tab SHALL show only public templates
and SHALL hide its advanced browsing controls: the Public/My Templates
visibility toggle SHALL NOT be rendered and template listing SHALL be forced to
`visibility=public`, and the keyword search input and the category filter SHALL
NOT be rendered. The template grid (with direct create-board-from-template
selection) and pagination SHALL remain. While Simple mode is disabled, the
Templates tab SHALL render the full browsing controls (Public/My Templates
toggle, keyword search, and category filter) unchanged.

#### Scenario: Public-only templates with no filters in Simple mode

- **WHEN** a user with Simple mode enabled opens the Templates tab
- **THEN** only public templates are listed, and the Public/My Templates toggle,
  the keyword search input, and the category filter are not rendered

#### Scenario: Listing forced to public in Simple mode

- **WHEN** the Templates tab loads in Simple mode
- **THEN** the templates list request uses `visibility=public`
- **AND** the user has no control to switch to a "My Templates" view

#### Scenario: Grid and pagination remain in Simple mode

- **WHEN** a user with Simple mode enabled browses more public templates than fit
  on one page
- **THEN** the template grid and pagination controls are still shown

#### Scenario: Full browsing controls when Simple mode is off

- **WHEN** a user with Simple mode disabled opens the Templates tab
- **THEN** the Public/My Templates toggle, the keyword search input, and the
  category filter are all rendered
