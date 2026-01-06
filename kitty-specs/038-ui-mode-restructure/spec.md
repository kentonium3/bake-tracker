# Feature Specification: UI Mode Restructure

**Feature Branch**: `038-ui-mode-restructure`
**Created**: 2026-01-05
**Status**: Draft
**Input**: Restructure application UI from flat 11-tab navigation to 5-mode workflow architecture

## Clarifications

### Session 2026-01-05

- Q: What is the expected implementation scope for the 5 new tabs (Shopping Lists, Purchases, Assembly, Packaging, Event Status)? → A: Full functionality - complete working features
- Q: When the application launches, which mode should be displayed by default? → A: OBSERVE - show status/progress first
- Q: During migration, how should the old flat navigation coexist with the new mode structure? → A: Big-bang - old navigation removed immediately when new modes are ready
- Q: Should the Packages tab be included in F038 (design doc marked it "Phase 3 - deferred")? → A: Yes - include as functional tab

## Overview

Transform the application's flat 11-tab navigation into a 5-mode workflow-oriented architecture. Each mode represents a distinct work activity (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE) with consistent internal layouts and mode-specific dashboards.

**Primary User**: Marianne (non-technical baker)

**Problem Statement**:
- Current flat navigation has no workflow guidance (11 tabs at same level)
- Inconsistent tab layouts force users to relearn each screen
- No visibility into system state without clicking through multiple tabs
- Unclear entry points for common tasks like planning events

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mode-Based Navigation (Priority: P1)

As a baker, I want to switch between work modes so that I can focus on one type of activity at a time without being overwhelmed by unrelated options.

**Why this priority**: Foundation for all other functionality. Without mode switching, no other features work.

**Independent Test**: User can click mode buttons to switch between 5 distinct screens, each showing appropriate content area.

**Acceptance Scenarios**:

1. **Given** application is open, **When** I click "CATALOG" mode button, **Then** I see the CATALOG mode content with its dashboard and tabs
2. **Given** I am in CATALOG mode, **When** I click "PLAN" mode button, **Then** I switch to PLAN mode and see its dashboard and tabs
3. **Given** I am in any mode, **When** I press Ctrl+1 through Ctrl+5, **Then** I switch to the corresponding mode (1=CATALOG, 2=PLAN, 3=SHOP, 4=PRODUCE, 5=OBSERVE)
4. **Given** I switch modes, **When** I return to a previous mode, **Then** I see the same tab I was viewing before (mode state preserved)

---

### User Story 2 - Mode Dashboards Show Status At-a-Glance (Priority: P1)

As a baker, I want to see relevant status information when I enter each mode so that I immediately know what needs attention.

**Why this priority**: Core value proposition - users see status without hunting through tabs.

**Independent Test**: Each mode displays a dashboard with quick stats and recent activity relevant to that mode.

**Acceptance Scenarios**:

1. **Given** I enter CATALOG mode, **When** the dashboard loads, **Then** I see counts of ingredients, products, recipes, finished units, and finished goods
2. **Given** I enter PLAN mode, **When** the dashboard loads, **Then** I see upcoming events with their status indicators
3. **Given** I enter SHOP mode, **When** the dashboard loads, **Then** I see shopping lists by store and inventory alerts for low items
4. **Given** I enter PRODUCE mode, **When** the dashboard loads, **Then** I see today's pending production and assembly checklists
5. **Given** I enter OBSERVE mode, **When** the dashboard loads, **Then** I see event readiness progress (shopping, production, assembly, packaging percentages)

---

### User Story 3 - Consistent Tab Layout (Priority: P2)

As a user, I want all tabs to have the same layout pattern so that I can quickly find actions, search, and data without relearning each screen.

**Why this priority**: Reduces cognitive load and training time. Important but not blocking.

**Independent Test**: Navigate to any tab and verify standard elements appear in consistent positions.

**Acceptance Scenarios**:

1. **Given** I am on any tab, **When** I look for action buttons (Add, Edit, Delete), **Then** I find them in the top-left area
2. **Given** I am on any tab, **When** I look for the refresh button, **Then** I find it in the top-right area
3. **Given** I am on any tab, **When** I look for search and filters, **Then** I find them below the action bar
4. **Given** I am on any tab, **When** I look for the data grid, **Then** I find it in the main content area with consistent styling
5. **Given** I am on any tab, **When** I look for status information, **Then** I find it at the bottom of the tab

---

### User Story 4 - CATALOG Mode for Definitions (Priority: P2)

As a baker setting up my kitchen catalog, I want to manage all my definitions (ingredients, products, recipes, finished goods) in one place.

**Why this priority**: Most stable feature set - builds on existing tabs. Good parallelization candidate.

**Independent Test**: Access and manage all catalog entities from CATALOG mode tabs.

**Acceptance Scenarios**:

1. **Given** I am in CATALOG mode, **When** I click "Ingredients" tab, **Then** I see my ingredients list with hierarchy display
2. **Given** I am in CATALOG mode, **When** I click "Products" tab, **Then** I see my products list with brand/pricing info
3. **Given** I am in CATALOG mode, **When** I click "Recipes" tab, **Then** I see my recipes list
4. **Given** I am in CATALOG mode, **When** I click "Finished Units" tab, **Then** I see individual items from recipes
5. **Given** I am in CATALOG mode, **When** I click "Finished Goods" tab, **Then** I see assemblies and gift bundles
6. **Given** I click "Add" on any CATALOG tab, **When** I fill the form and save, **Then** the new item appears in the list

---

### User Story 5 - OBSERVE Mode for Progress Tracking (Priority: P2)

As a baker preparing for events, I want to see my progress across all workflow stages so that I know if I'm on track.

**Why this priority**: Key differentiator - existing Summary tab gets enhanced. Good parallelization candidate.

**Independent Test**: View event readiness with progress percentages for each stage.

**Acceptance Scenarios**:

1. **Given** I have an upcoming event, **When** I view OBSERVE mode dashboard, **Then** I see that event with progress bars for shopping, production, assembly, and packaging
2. **Given** I am in OBSERVE mode, **When** I click "Event Status" tab, **Then** I see detailed per-event progress
3. **Given** I am in OBSERVE mode, **When** I click "Dashboard" tab, **Then** I see overall activity summary and quick stats
4. **Given** shopping is complete for an event, **When** I view event readiness, **Then** shopping shows 100% with checkmark indicator

---

### User Story 6 - PRODUCE Mode for Execution (Priority: P3)

As a baker during production days, I want to see what I need to make today and track my progress through production, assembly, and packaging.

**Why this priority**: Core workflow but depends on existing production functionality working correctly.

**Independent Test**: View and complete production, assembly, and packaging checklists.

**Acceptance Scenarios**:

1. **Given** I have planned production, **When** I view PRODUCE mode dashboard, **Then** I see pending batches to make
2. **Given** production is complete, **When** I view assembly checklist, **Then** I see which bundles can be assembled
3. **Given** assembly is complete, **When** I view packaging checklist, **Then** I see which packages are ready for final packaging
4. **Given** I check off a production item, **When** I complete it, **Then** the dashboard updates to show completion

---

### User Story 7 - SHOP Mode for Inventory (Priority: P3)

As a baker preparing to shop, I want to see what I need to buy organized by store and track my purchases.

**Why this priority**: Depends on shopping list generation and purchase tracking features. May need new tabs.

**Independent Test**: View shopping lists and record purchases.

**Acceptance Scenarios**:

1. **Given** I have events with ingredient needs, **When** I view SHOP mode, **Then** I see shopping lists organized by store
2. **Given** I am in SHOP mode, **When** I click "Purchases" tab, **Then** I can record new purchases
3. **Given** I am in SHOP mode, **When** I click "Inventory" (My Pantry) tab, **Then** I see current inventory status
4. **Given** inventory is low on an item, **When** I view SHOP dashboard, **Then** I see an alert for that item

---

### User Story 8 - PLAN Mode for Event Planning (Priority: P3)

As a baker planning for events, I want to define what I'm making and when, and see the calculated production requirements.

**Why this priority**: Events tab exists but Planning Workspace is new. Dependencies on other features.

**Independent Test**: Create events and view production plan calculations.

**Acceptance Scenarios**:

1. **Given** I am in PLAN mode, **When** I click "Events" tab, **Then** I see my events list with status
2. **Given** I have an event with bundle requirements, **When** I view the Planning Workspace, **Then** I see calculated batch counts
3. **Given** I create a new event, **When** I define its requirements, **Then** the production plan preview updates

---

### Edge Cases

- What happens when switching modes while a form is open with unsaved changes? (Show confirmation dialog)
- How does the system handle loading dashboards with large data sets? (Progressive loading, show loading indicator)
- What happens if a tab fails to load? (Show error message, allow retry)
- How are keyboard shortcuts handled when focus is in a text field? (Standard text editing takes precedence)
- What happens when user has no data yet? (Show helpful empty states with guidance)

## Requirements *(mandatory)*

### Functional Requirements

**Mode Navigation**
- **FR-001**: System MUST display 5 mode buttons (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE) in a horizontal bar
- **FR-002**: System MUST highlight the currently active mode
- **FR-003**: System MUST support keyboard shortcuts Ctrl+1 through Ctrl+5 for mode switching
- **FR-004**: System MUST preserve tab selection when switching between modes and returning
- **FR-005**: System MUST default to OBSERVE mode on application launch

**Mode Dashboards**
- **FR-006**: Each mode MUST display a dashboard at the top with mode-specific summary information
- **FR-007**: CATALOG dashboard MUST show counts of ingredients, products, recipes, finished units, finished goods
- **FR-008**: PLAN dashboard MUST show upcoming events with status indicators
- **FR-009**: SHOP dashboard MUST show shopping lists by store and inventory alerts
- **FR-010**: PRODUCE dashboard MUST show pending production, assembly checklist, and packaging checklist
- **FR-011**: OBSERVE dashboard MUST show event readiness with progress percentages

**Consistent Tab Layout**
- **FR-012**: All tabs MUST follow StandardTabLayout pattern with: action bar, search/filters, data grid, status bar
- **FR-013**: Action buttons MUST appear in top-left of every tab
- **FR-014**: Refresh button MUST appear in top-right of every tab
- **FR-015**: Search and filter controls MUST appear below action bar
- **FR-016**: Data grid MUST use consistent styling across all tabs
- **FR-017**: Status bar MUST appear at bottom of every tab

**CATALOG Mode Tabs**
- **FR-018**: CATALOG mode MUST contain tabs: Ingredients, Products, Recipes, Finished Units, Finished Goods, Packages
- **FR-019**: All existing tab functionality MUST be preserved after migration

**PLAN Mode Tabs**
- **FR-020**: PLAN mode MUST contain tabs: Events, Planning Workspace
- **FR-021**: Planning Workspace MUST show calculated batch requirements for events

**SHOP Mode Tabs**
- **FR-022**: SHOP mode MUST contain tabs: Shopping Lists, Purchases, Inventory (My Pantry)
- **FR-023**: Shopping Lists tab MUST organize items by store

**PRODUCE Mode Tabs**
- **FR-024**: PRODUCE mode MUST contain tabs: Production Runs, Assembly, Packaging, Recipients
- **FR-025**: Assembly tab MUST show checklist of assembleable finished goods
- **FR-026**: Packaging tab MUST show checklist of items ready for final packaging

**OBSERVE Mode Tabs**
- **FR-027**: OBSERVE mode MUST contain tabs: Dashboard, Event Status, Reports
- **FR-028**: Event Status tab MUST show per-event progress tracking
- **FR-028a**: Reports tab is a placeholder for future functionality (reports not yet defined)

**Migration Requirements**
- **FR-029**: System MUST migrate all 12 existing tabs to new mode structure
- **FR-030**: System MUST maintain all existing tab functionality during and after migration
- **FR-031**: Old flat navigation MUST be removed immediately when all modes are complete (big-bang replacement, no parallel navigation period)

### Key Entities

- **Mode**: A top-level navigation container representing a work activity (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE)
- **Mode Dashboard**: A summary widget showing mode-specific status information and quick actions
- **Tab**: A content area within a mode for managing specific entity types or workflows
- **StandardTabLayout**: A consistent layout pattern applied to all tabs

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can find the entry point for common tasks (add recipe, check inventory, view event progress) in under 5 seconds
- **SC-002**: Users correctly identify which mode to use for a given activity on first attempt 90% of the time
- **SC-003**: Users can see current system status (upcoming events, inventory alerts, production progress) without clicking through tabs
- **SC-004**: All tabs display with consistent layout - action buttons, search, filters, and data grid in same positions
- **SC-005**: Mode dashboards display relevant summary data within 1 second of mode selection
- **SC-006**: All existing functionality (CRUD operations, filtering, searching) continues to work after migration
- **SC-007**: Primary user (Marianne) prefers new navigation over old flat tabs in usability testing
- **SC-008**: New users can complete "plan an event" workflow without guidance using mode navigation

### Parallelization Opportunities

The following work can be safely parallelized:
- **CATALOG mode** and **OBSERVE mode** are independent - different tabs, no shared state
- **Base classes** (BaseMode, StandardTabLayout) must complete first, then modes can parallelize
- **Tab refactoring** within each mode can parallelize across tabs (e.g., Ingredients tab and Products tab simultaneously)
- **Dashboard development** can parallelize across modes once base classes exist
- **New tabs** (Shopping Lists, Purchases, Assembly, Packaging, Event Status) can develop in parallel

## Assumptions

- Existing tab implementations are functional and only need layout refactoring, not logic changes
- Finished Goods tab already exists (may need rename/clarification)
- All 5 new tabs (Shopping Lists, Purchases, Assembly, Packaging, Event Status) will be fully functional within this feature
- Packages tab in CATALOG mode will be fully functional (not deferred)
- Planning Workspace will include automatic batch calculation functionality
- Shopping Lists tab will include auto-generation from events
- Assembly and Packaging tabs will include checklist functionality (Phase 2 minimal - simple checklists, not full inventory transactions)

## Dependencies

- No database schema changes required (UI-only reorganization)
- Existing service layer remains unchanged
- CustomTkinter framework continues to be used
