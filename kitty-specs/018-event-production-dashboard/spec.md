# Feature Specification: Event Production Dashboard

**Feature Branch**: `018-event-production-dashboard`
**Created**: 2025-12-12
**Status**: Draft
**Input**: User description: "Mission control view showing production status at a glance"

## Clarifications

### Session 2025-12-12

- Q: Which color should represent the "Exceeded" status? → A: Light green/teal (subtle distinction from complete)

## User Scenarios & Testing

### User Story 1 - View Multi-Event Status Board (Priority: P1)

As a baker, I want to see the production status of all my upcoming events on one screen so that I can understand where each event's preparations stand at a glance.

**Why this priority**: Core value proposition - this is the "mission control" view that answers "Where do I stand?" without drilling into individual events. Like a kitchen order board showing multiple orders in progress.

**Independent Test**: Can be fully tested by creating multiple events with targets, recording varying amounts of production/assembly, and verifying the dashboard displays all events with correct progress indicators.

**Acceptance Scenarios**:

1. **Given** I have three events (Christmas 2025, Easter 2026, Birthday Party), **When** I open the Production Dashboard tab, **Then** I see all three events displayed as separate status cards showing their overall progress.

2. **Given** Christmas 2025 has 5 production targets (3 complete, 2 in progress), **When** I view the dashboard, **Then** the Christmas 2025 card shows aggregated progress (e.g., "3/5 recipes complete, 60%") with a visual progress indicator.

3. **Given** Easter 2026 has no targets set yet, **When** I view the dashboard, **Then** Easter 2026 appears with "No targets set" indicator and a prompt to add targets.

4. **Given** I have events in past, active (current), and future states, **When** I open the dashboard with default filter, **Then** only active and future events are displayed.

5. **Given** one event is 100% complete on all targets, **When** I view the dashboard, **Then** that event card displays a "Complete" visual indicator (color-coded green).

---

### User Story 2 - View Consolidated Progress for Single Event (Priority: P1)

As a baker, I want to see all production and assembly targets for a specific event with their progress so that I can understand exactly what's done and what remains.

**Why this priority**: Enables detailed tracking within the dashboard without navigating to Event Detail window.

**Independent Test**: Can be tested by expanding an event card and verifying all production targets and assembly targets display with correct progress bars and status indicators.

**Acceptance Scenarios**:

1. **Given** I am viewing the Production Dashboard, **When** I click on an event card, **Then** the card expands to show detailed progress for all production targets (recipes) and assembly targets (finished goods).

2. **Given** Christmas 2025 has production target "Sugar Cookies - 4 batches" and I've produced 2 batches, **When** I view the expanded card, **Then** I see "Sugar Cookies: 2/4 batches (50%)" with a half-filled progress bar.

3. **Given** a target has 0 of 4 batches produced, **When** I view progress, **Then** the status indicator shows "Not Started" with gray color coding.

4. **Given** a target has 2 of 4 batches produced, **When** I view progress, **Then** the status indicator shows "In Progress" with yellow/amber color coding.

5. **Given** a target has 4 of 4 batches produced, **When** I view progress, **Then** the status indicator shows "Complete" with green color coding.

6. **Given** a target has 5 of 4 batches produced (exceeded), **When** I view progress, **Then** the status indicator shows "Exceeded" (125%) with light green/teal color coding (subtle distinction from complete).

---

### User Story 3 - View Fulfillment Status Overview (Priority: P1)

As a baker, I want to see a summary of package fulfillment status (pending/ready/delivered) for each event so that I know how many gifts are ready to go.

**Why this priority**: Essential for event day - knowing how many packages are ready vs still pending is critical for delivery planning.

**Independent Test**: Can be tested by assigning packages to event recipients with varying fulfillment statuses and verifying the dashboard displays correct counts.

**Acceptance Scenarios**:

1. **Given** Christmas 2025 has 10 package assignments (4 pending, 4 ready, 2 delivered), **When** I view the dashboard, **Then** I see fulfillment summary "4 pending | 4 ready | 2 delivered" with visual breakdown (e.g., stacked bar or pie segments).

2. **Given** all packages for an event are delivered, **When** I view the fulfillment summary, **Then** I see "All Delivered" with complete indicator.

3. **Given** an event has no package assignments, **When** I view the fulfillment summary, **Then** I see "No packages assigned" indicator.

4. **Given** I want to see which specific packages are pending, **When** I click on the "4 pending" count, **Then** I navigate to the Event Detail window filtered to pending packages (or see an expanded list).

---

### User Story 4 - Filter Events by Date/Status (Priority: P2)

As a baker, I want to filter the event status board by date range or event status so that I can focus on specific time periods or review past events.

**Why this priority**: Default view covers 90% of use cases (active + future). Filtering is useful for planning and review but not essential for daily use.

**Independent Test**: Can be tested by creating events in past, present, and future, then verifying each filter option shows the correct subset.

**Acceptance Scenarios**:

1. **Given** I open the Production Dashboard, **When** I view the filter controls, **Then** I see options for: "Active & Future" (default), "Past Events", "All Events", and a date range picker.

2. **Given** I select "Past Events" filter, **When** the dashboard updates, **Then** only events with event_date before today are displayed.

3. **Given** I select "All Events" filter, **When** the dashboard updates, **Then** all events (past, active, future) are displayed.

4. **Given** I set date range "Dec 1, 2025 - Dec 31, 2025", **When** the dashboard updates, **Then** only events within that date range are displayed.

5. **Given** I change the filter, **When** I close and reopen the dashboard, **Then** the filter resets to default "Active & Future" (filter is session-only, not persisted).

---

### User Story 5 - Quick Actions from Dashboard (Priority: P2)

As a baker, I want to quickly jump to common actions (record production, record assembly, view shopping list, open event detail) from the dashboard so that I can take action without navigating through multiple screens.

**Why this priority**: Convenience feature that improves workflow efficiency but doesn't block core dashboard functionality.

**Independent Test**: Can be tested by clicking each quick action button and verifying it opens the correct dialog or navigates to the correct view.

**Acceptance Scenarios**:

1. **Given** I am viewing an event card on the dashboard, **When** I click "Record Production", **Then** the Record Production dialog opens with this event pre-selected in the event dropdown.

2. **Given** I am viewing an event card, **When** I click "Record Assembly", **Then** the Record Assembly dialog opens with this event pre-selected.

3. **Given** I am viewing an event card, **When** I click "Shopping List", **Then** I navigate to the shopping list view for this event (or a shopping list dialog opens).

4. **Given** I am viewing an event card, **When** I click "Event Detail", **Then** the Event Detail window opens for this event.

5. **Given** I am viewing the dashboard header, **When** I look for global actions, **Then** I see a "Create Event" button that opens the new event dialog.

---

### User Story 6 - Tab Structure Reorganization (Priority: P1)

As a baker, I want the Production Dashboard to be the first/default tab when I open the app so that I immediately see my production status without extra clicks.

**Why this priority**: Core UX requirement - the dashboard must be the landing page to fulfill its "mission control" purpose.

**Independent Test**: Can be tested by launching the application and verifying the Production Dashboard tab is selected by default.

**Acceptance Scenarios**:

1. **Given** I launch the application, **When** the main window loads, **Then** the "Production Dashboard" tab is selected and visible as the first tab.

2. **Given** the existing "Dashboard" tab shows global summary stats, **When** I look for this content, **Then** it is available in a separate "Summary" tab (second tab position).

3. **Given** I switch to another tab and close the application, **When** I relaunch, **Then** the Production Dashboard tab is selected (always starts on dashboard).

4. **Given** I am on the Production Dashboard tab, **When** I look at the tab bar, **Then** tab order is: Production Dashboard, Summary, [other existing tabs...].

---

### Edge Cases

- **No events exist**: Dashboard shows "No events found. Create your first event to get started." with a "Create Event" button.
- **Events exist but no targets set**: Each event card shows "No production/assembly targets set. Add targets to track progress." with link to Event Detail.
- **Event has targets but no production recorded**: All targets show 0% progress with "Not Started" status.
- **Event date is today**: Classified as "Active" - shown in default filter.
- **Multiple events on same date**: All are displayed, sorted by event name alphabetically within the same date.
- **Very long event list**: Dashboard should handle scrolling gracefully; consider pagination or virtual scrolling for 20+ events.
- **Database contains orphaned production runs (event deleted but runs exist)**: These runs had event_id set to NULL during deletion per FR-008 from Feature 016 - they won't appear in dashboard.

---

## Requirements

### Functional Requirements

**Dashboard Core:**
- **FR-001**: System MUST display a Production Dashboard as a new tab in the main window
- **FR-002**: Production Dashboard MUST be the first/default tab when application launches
- **FR-003**: Existing dashboard content (global summary) MUST move to a separate "Summary" tab
- **FR-004**: Dashboard MUST display event status cards for all events matching the current filter

**Event Status Board:**
- **FR-005**: Each event card MUST display: event name, event date, overall production progress, overall assembly progress, and fulfillment status summary
- **FR-006**: Event cards MUST show aggregated progress as both count (X/Y complete) and percentage
- **FR-007**: Event cards MUST be expandable to show individual target details
- **FR-008**: Dashboard MUST update automatically when production/assembly is recorded elsewhere in the app

**Progress Visualization:**
- **FR-009**: Progress bars MUST use color-coded status indicators: gray (not started, 0%), yellow/amber (in progress, 1-99%), green (complete, 100%), light green/teal (exceeded, >100%)
- **FR-010**: Status text MUST display: "Not Started", "In Progress", "Complete", or "Exceeded" based on progress percentage
- **FR-011**: Exceeded status (>100%) MUST be treated as neutral, not warning or error
- **FR-012**: Progress calculations MUST use existing EventService.get_production_progress() and get_assembly_progress() methods

**Fulfillment Status:**
- **FR-013**: Dashboard MUST display package fulfillment counts by status (pending, ready, delivered) for each event
- **FR-014**: Fulfillment summary MUST use existing EventService.get_event_overall_progress() method
- **FR-015**: Clicking a fulfillment status count SHOULD navigate to Event Detail with that status filtered

**Event Filtering:**
- **FR-016**: Dashboard MUST default to showing active (today or earlier with future date) and future events
- **FR-017**: Dashboard MUST provide filter options: "Active & Future" (default), "Past Events", "All Events"
- **FR-018**: Dashboard MUST provide date range picker for custom filtering (from date, to date)
- **FR-019**: Filter state MUST NOT persist across application restarts (resets to default)

**Quick Actions:**
- **FR-020**: Each event card MUST provide quick action buttons: Record Production, Record Assembly, Shopping List, Event Detail
- **FR-021**: Quick action "Record Production" MUST open Record Production dialog with event pre-selected
- **FR-022**: Quick action "Record Assembly" MUST open Record Assembly dialog with event pre-selected
- **FR-023**: Dashboard header MUST include "Create Event" button

**Performance:**
- **FR-024**: Dashboard MUST load and display within 2 seconds for up to 50 events with targets

### Key Entities

- **Event**: Existing entity - dashboard displays events filtered by date/status
- **EventProductionTarget**: Existing entity - aggregated for production progress display
- **EventAssemblyTarget**: Existing entity - aggregated for assembly progress display
- **EventRecipientPackage**: Existing entity - aggregated for fulfillment status counts
- **ProductionRun**: Existing entity - progress calculated from runs linked to event
- **AssemblyRun**: Existing entity - progress calculated from runs linked to event

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Baker can see overall status of all active/future events within 2 seconds of launching the app
- **SC-002**: Production Dashboard displays as the default first tab on application launch
- **SC-003**: Status indicators correctly display all four states: Not Started (0%), In Progress (1-99%), Complete (100%), Exceeded (>100%)
- **SC-004**: Color coding is applied consistently: gray for not started, yellow/amber for in progress, green for complete, light green/teal for exceeded
- **SC-005**: Fulfillment counts (pending/ready/delivered) match actual EventRecipientPackage data for each event
- **SC-006**: Date filtering correctly shows only events matching the selected criteria
- **SC-007**: Quick action buttons successfully open correct dialogs with event pre-selected
- **SC-008**: Dashboard gracefully handles edge cases (no events, no targets, exceeded production)

---

## Out of Scope

- **Dashboard customization**: No user-configurable card layouts, column arrangements, or saved views
- **Real-time collaboration**: No live updates from other users (single-user desktop app)
- **Push notifications**: No alerts when targets are met or events approach
- **Print/export dashboard view**: Dashboard is view-only, use existing CSV exports for data export
- **Drag-and-drop event ordering**: Events sorted by date, not user-arrangeable

---

## Dependencies

- **Requires**: Feature 016 (Event-Centric Production Model) - COMPLETE - provides EventService methods for progress tracking
- **Requires**: Feature 017 (Reporting & Event Planning) - COMPLETE - provides dashboard tab infrastructure
- **No blocking dependencies for future features**

---

## Assumptions

- The existing tab infrastructure in the main window supports adding/reordering tabs
- EventService progress methods (get_production_progress, get_assembly_progress, get_event_overall_progress) are performant for dashboard use
- CustomTkinter supports the required visual components (progress bars, expandable cards, color coding)
- The existing Record Production and Record Assembly dialogs can accept an event parameter for pre-selection
