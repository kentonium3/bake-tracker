# Feature Specification: Event Reporting & Production Dashboard

**Feature Branch**: `017-event-reporting-production`
**Created**: 2025-12-11
**Status**: Draft
**Input**: User description: "Shopping list CSV export, Event summary reports (planned vs actual), Cost analysis views, Recipient history reports, Dashboard enhancements - Production Dashboard as default, Summary tab for other info"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Production Dashboard as Default View (Priority: P1)

When the user opens the application, they need to immediately see production status - what needs to be made, what's been done, and overall event progress. The current "Dashboard" tab shows static summary info that's less actionable than real-time production status.

**Why this priority**: This is the most frequently accessed view during active baking season. Users need at-a-glance production status, not static counts. Making this the default landing experience maximizes daily productivity.

**Independent Test**: Can be fully tested by launching the app and verifying the Production Dashboard appears first, with event progress visible. Delivers immediate production awareness.

**Acceptance Scenarios**:

1. **Given** application is launched, **When** main window opens, **Then** Production Dashboard tab is selected by default (not old Dashboard)
2. **Given** Production Dashboard is displayed, **When** an event has production/assembly targets set, **Then** progress bars show produced vs target for each recipe/finished good
3. **Given** user is on Production Dashboard, **When** they want summary stats (ingredient count, inventory value, etc.), **Then** a "Summary" tab is available showing that information

---

### User Story 2 - Event Progress Overview (Priority: P1)

The user needs to see "Where do I stand for Christmas 2025?" at a glance - how many batches of each recipe have been made vs targets, how many finished goods assembled vs needed, and overall package readiness.

**Why this priority**: Core production tracking - answers the fundamental question users ask daily during baking season.

**Independent Test**: Select an event with targets, verify progress bars and percentages are accurate based on linked ProductionRun/AssemblyRun records.

**Acceptance Scenarios**:

1. **Given** Production Dashboard is displayed, **When** event selector dropdown is present, **Then** user can select an event to view its progress
2. **Given** event "Christmas 2025" has targets (4 batches Sugar Cookies, 2 batches Snickerdoodles), **When** 2 batches Sugar Cookies recorded for that event, **Then** progress shows "2/4 (50%)" for Sugar Cookies
3. **Given** event has assembly targets, **When** assemblies recorded for that event, **Then** assembly progress shows produced vs target with percentage
4. **Given** event has no targets set, **When** event is selected, **Then** display shows "No production targets set" with link to add targets

---

### User Story 3 - Shopping List CSV Export (Priority: P2)

The user goes shopping and needs a printed or phone-accessible list of ingredients needed for an event. They want to export the shopping list to CSV for printing or import into other apps.

**Why this priority**: Simple, high-value utility that enables offline access to shopping data. Builds on existing shopping list calculation (Feature 007).

**Independent Test**: Click export button on event shopping list, verify CSV file is created with correct ingredient data.

**Acceptance Scenarios**:

1. **Given** user is viewing an event's shopping list, **When** they click "Export CSV" button, **Then** file save dialog appears with suggested filename "christmas-2025-shopping-list.csv"
2. **Given** shopping list has 10 ingredients, **When** CSV is exported, **Then** file contains header row + 10 data rows with columns: Ingredient, Quantity, Unit, Preferred Brand, Est. Cost
3. **Given** ingredient has no preferred brand, **When** CSV is exported, **Then** brand column shows empty value (not "None" or error)

---

### User Story 4 - Event Summary Report (Priority: P2)

After an event, the user wants to review what was planned vs what actually happened - did they make all planned items? What was actual vs estimated cost? This enables better planning for next year.

**Why this priority**: Planning improvement tool. Answers "How did Christmas 2025 actually go?" for next year's planning.

**Independent Test**: View event summary, verify planned vs actual numbers are accurately displayed from database records.

**Acceptance Scenarios**:

1. **Given** event "Christmas 2025" is complete, **When** user views Event Summary tab/report, **Then** report shows: recipes planned vs produced, finished goods planned vs assembled, packages planned vs delivered
2. **Given** event had production target of 4 batches Sugar Cookies, **When** 5 batches were actually produced, **Then** summary shows "Planned: 4, Actual: 5 (125%)"
3. **Given** event had estimated ingredient cost of $150, **When** actual consumption records totaled $142, **Then** summary shows "Est. Cost: $150.00, Actual: $142.00, Variance: -$8.00"

---

### User Story 5 - Cost Analysis View (Priority: P3)

The user wants to understand cost breakdown for an event - what did each recipe cost to produce, what was total ingredient spend, and how does this compare to estimates?

**Why this priority**: Financial awareness. Important for budgeting but less urgent than production tracking.

**Independent Test**: View cost analysis for an event, verify costs match sum of ProductionConsumption and AssemblyConsumption records.

**Acceptance Scenarios**:

1. **Given** event has production runs recorded, **When** user views Cost Analysis, **Then** cost breakdown shows: per-recipe cost (sum of production consumption costs), per-finished-good cost (sum of assembly consumption costs)
2. **Given** recipe "Sugar Cookies" had 2 production runs, **When** cost analysis is displayed, **Then** shows total cost for Sugar Cookies = sum of both runs' total_cost
3. **Given** no production has occurred for an event, **When** cost analysis is viewed, **Then** shows estimated costs based on current ingredient prices

---

### User Story 6 - Recipient History (Priority: P3)

The user wants to see what packages a specific recipient has received over time - "What did Aunt Martha get last year?" for planning this year's gifts.

**Why this priority**: Planning aid for personalization. Nice-to-have but not critical for production workflow.

**Independent Test**: View recipient detail, see list of all packages received across all events.

**Acceptance Scenarios**:

1. **Given** recipient "Aunt Martha" exists, **When** user views recipient detail, **Then** history section shows all EventRecipientPackage records with: event name, package name, quantity, delivery status
2. **Given** Aunt Martha received packages in Christmas 2024 and Easter 2025, **When** viewing history, **Then** both events appear sorted by date descending
3. **Given** recipient has no package history, **When** viewing history, **Then** shows "No package history" message

---

### Edge Cases

- What happens when event has targets but no production/assembly runs? Display 0% progress, not error.
- How does system handle production runs NOT linked to any event? Show in "Unassigned Production" section.
- What happens when CSV export fails (disk full, permissions)? Show user-friendly error with suggested action.
- How does cost analysis handle deleted ingredients? Use cost_at_time from consumption records.
- What happens when event has 0 targets? Show helpful message with link to set targets.

## Requirements *(mandatory)*

### Functional Requirements

**Dashboard Restructuring**
- **FR-001**: System MUST display Production Dashboard as the default/first tab when application launches
- **FR-002**: System MUST provide a "Summary" tab containing: ingredient count, recipe count, inventory value, finished good count, bundle count (moved from old Dashboard)
- **FR-003**: Production Dashboard MUST include event selector dropdown to filter progress by event
- **FR-004**: Production Dashboard MUST display production progress (recipes: batches produced vs target) with progress bars
- **FR-005**: Production Dashboard MUST display assembly progress (finished goods: quantity assembled vs target) with progress bars
- **FR-006**: System MUST show "No targets set" message with action link when event has no production/assembly targets

**Shopping List Export**
- **FR-007**: System MUST provide "Export CSV" button on event shopping list view
- **FR-008**: CSV export MUST include columns: Ingredient, Quantity Needed, Unit, Preferred Brand, Estimated Cost
- **FR-009**: CSV export MUST use event-slug-shopping-list.csv as default filename
- **FR-010**: System MUST handle export errors gracefully with user notification

**Event Summary Reports**
- **FR-011**: System MUST display planned vs actual for production targets (batches)
- **FR-012**: System MUST display planned vs actual for assembly targets (quantity)
- **FR-013**: System MUST display planned vs actual for package delivery (count by status)
- **FR-014**: System MUST calculate and display cost variance (estimated vs actual)

**Cost Analysis**
- **FR-015**: System MUST display per-recipe production costs from ProductionConsumption records
- **FR-016**: System MUST display per-finished-good assembly costs from consumption records
- **FR-017**: System MUST show total event cost (sum of all production + assembly costs)
- **FR-018**: Cost analysis MUST use cost_at_time from consumption records (not current prices)

**Recipient History**
- **FR-019**: Recipient detail view MUST display package history across all events
- **FR-020**: Package history MUST show: event name, package name, quantity, fulfillment status, date
- **FR-021**: Package history MUST be sorted by event date descending (most recent first)

### Key Entities *(existing - no new tables)*

- **ProductionRun**: Links to Event via event_id (Feature 016), has total_cost, num_batches, actual_yield
- **AssemblyRun**: Links to Event via event_id (Feature 016), has total_cost, quantity
- **EventProductionTarget**: Target batches per recipe per event
- **EventAssemblyTarget**: Target quantity per finished good per event
- **EventRecipientPackage**: Package assignments with fulfillment_status
- **ProductionConsumption**: Ingredient consumption per production run with cost_at_time
- **AssemblyFinishedUnitConsumption/AssemblyPackagingConsumption**: Component consumption per assembly run

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Production Dashboard loads in < 2 seconds with event progress displayed
- **SC-002**: CSV export completes successfully and file is readable in Excel/Google Sheets
- **SC-003**: Progress percentages match manual calculation (produced / target * 100)
- **SC-004**: Cost totals match sum of individual consumption record costs
- **SC-005**: All existing tests continue to pass (680+ tests)
- **SC-006**: New service methods have >80% test coverage
- **SC-007**: User can answer "Where do I stand for [Event]?" within 5 seconds of opening app
