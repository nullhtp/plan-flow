## MODIFIED Requirements

### Requirement: Board List on Home Page
The system SHALL display the authenticated user's dashboard on the index page (`/`) using a tabbed layout with two top-level tabs: **Boards** and **Templates**. The tabs SHALL use the Shadcn Tabs component (Radix-based) for proper accessibility and semantics. The active tab SHALL be persisted in the URL via a `tab` search parameter (e.g., `/?tab=templates`) so that direct linking and browser navigation work. The default tab SHALL be "Boards" when no `tab` parameter is present.

**Boards tab**: SHALL display boards in a responsive card grid with a secondary toggle between "My Boards" and "Shared with Me" views (using the same button-toggle pattern as the public/my toggle in the Templates tab). The default secondary view SHALL be "My Boards". In the "My Boards" view, the first card in the grid SHALL be a "Create Board" card -- a visually distinct card with a "+" icon and label (e.g., "+ New Board") styled as an actionable placeholder at the same size as board cards. Clicking the creation card SHALL navigate to `/goals/new`. Remaining cards SHALL be `BoardCard` components showing board title, goal summary, task progress, and creation date. Clicking a board card SHALL navigate to `/boards/:boardId`. If the user has no boards, only the "+" creation card SHALL be displayed (no separate empty state message needed since the "+" card serves as the call-to-action). In the "Shared with Me" view, boards shared with the user (fetched via `GET /api/boards?shared=true`) SHALL be displayed in the same card grid layout. No creation card SHALL appear in this view. If no shared boards exist, a message like "No shared boards yet" SHALL be displayed.

**Templates tab**: SHALL embed the full templates gallery previously at `/templates`, including: public/my templates toggle (as a secondary toggle within the tab, using the same button-toggle pattern as the Boards tab), category filter, search input, pagination, and template cards in a grid. The first card in the template grid SHALL be a "Create Template" card -- a visually distinct card with a "+" icon and label (e.g., "+ Create Template") at the same size as template cards. Clicking the creation card SHALL navigate to `/templates/generate`. The "+" creation card SHALL appear in both "Public Templates" and "My Templates" sub-views.

The dashboard header SHALL be simplified: PlanFlow logo/text on the left, and a user dropdown menu on the right. The user dropdown SHALL display the user's email or avatar and contain menu items for "Settings" (navigates to `/settings`) and "Log out" (triggers logout). The "New Goal", "Templates", and standalone "Settings" / "Log out" buttons SHALL be removed from the header.

#### Scenario: Home page shows tabbed layout with Boards default
- **WHEN** an authenticated user visits `/`
- **THEN** the page displays two tabs: "Boards" (active by default) and "Templates", with the Boards tab showing the "My Boards" secondary view containing a "+" creation card as the first item followed by board cards

#### Scenario: Create Board card navigates to goal creation
- **WHEN** a user clicks the "+" creation card in the Boards tab "My Boards" view
- **THEN** the browser navigates to `/goals/new`

#### Scenario: My Boards view with no boards shows only creation card
- **WHEN** an authenticated user with no boards views the "My Boards" secondary view
- **THEN** only the "+" creation card is displayed in the grid

#### Scenario: Shared with Me view shows shared boards
- **WHEN** a user toggles to the "Shared with Me" secondary view within the Boards tab and has 2 shared boards
- **THEN** the view shows 2 board cards with no creation card

#### Scenario: Shared with Me view empty state
- **WHEN** a user toggles to the "Shared with Me" secondary view and has no shared boards
- **THEN** a message "No shared boards yet" is displayed

#### Scenario: Templates tab shows template gallery with creation card
- **WHEN** a user clicks the "Templates" tab
- **THEN** the tab content shows the template gallery with a "+" creation card as the first item, public/my toggle, category filter, search, and template cards

#### Scenario: Templates creation card navigates to generate wizard
- **WHEN** a user clicks the "+" creation card in the Templates tab
- **THEN** the browser navigates to `/templates/generate`

#### Scenario: Tab state persisted in URL
- **WHEN** a user clicks the "Templates" tab
- **THEN** the URL updates to `/?tab=templates`

#### Scenario: Direct link to tab
- **WHEN** a user navigates to `/?tab=templates`
- **THEN** the "Templates" tab is active

#### Scenario: Simplified header with user dropdown
- **WHEN** an authenticated user views the dashboard
- **THEN** the header shows the PlanFlow logo on the left and a user dropdown on the right containing "Settings" and "Log out" options

#### Scenario: Navigate to settings from dropdown
- **WHEN** a user opens the dropdown and clicks "Settings"
- **THEN** the browser navigates to `/settings`

#### Scenario: Log out from dropdown
- **WHEN** a user opens the dropdown and clicks "Log out"
- **THEN** the user is logged out and redirected to the login page

## ADDED Requirements

### Requirement: Creation Card Component
The system SHALL provide a reusable `CreationCard` component that renders a card-sized actionable placeholder with a "+" icon and a configurable label. The card SHALL match the dimensions of sibling cards in the grid (e.g., same height as `BoardCard` or `TemplateCard`). The card SHALL have a dashed border, a subtle hover effect (e.g., background tint or border color change), and a pointer cursor. The card SHALL accept an `onClick` handler or `href` for navigation. The card SHALL be used as the first item in both the My Boards grid and the Templates grid.

#### Scenario: Creation card renders with label
- **WHEN** a `CreationCard` is rendered with label "+ New Board"
- **THEN** the card displays a "+" icon centered above the label text, with a dashed border and consistent size with adjacent cards

#### Scenario: Creation card hover effect
- **WHEN** a user hovers over a creation card
- **THEN** the card displays a subtle visual feedback (e.g., background tint change or border color change) with a pointer cursor

#### Scenario: Creation card click triggers navigation
- **WHEN** a user clicks a creation card configured with href="/goals/new"
- **THEN** the browser navigates to `/goals/new`

### Requirement: User Dropdown Menu
The system SHALL provide a `UserDropdown` component in the dashboard header that displays the authenticated user's email and, when clicked, opens a dropdown menu with options: "Settings" (navigates to `/settings`) and "Log out" (triggers the logout mutation and redirects to login). The dropdown SHALL use Shadcn's DropdownMenu component (Radix-based) for proper accessibility. The trigger SHALL display the user's email or a user avatar icon.

#### Scenario: User dropdown displays email
- **WHEN** the dashboard header renders
- **THEN** the user dropdown trigger shows the authenticated user's email

#### Scenario: Dropdown opens with menu items
- **WHEN** a user clicks the dropdown trigger
- **THEN** a menu appears with "Settings" and "Log out" items

#### Scenario: Settings navigation from dropdown
- **WHEN** a user selects "Settings" from the dropdown
- **THEN** the browser navigates to `/settings`

#### Scenario: Log out from dropdown
- **WHEN** a user selects "Log out" from the dropdown
- **THEN** the logout mutation is triggered and the user is redirected to the login page
