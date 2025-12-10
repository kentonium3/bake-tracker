# Feature Specification: Production & Assembly Recording UI

**Feature Branch**: `014-production-assembly-recording`
**Created**: 2025-12-10
**Status**: Draft
**Input**: User description: "Add UI components for recording batch production and assembly operations"

## Clarifications

### Session 2025-12-10

- Q: How should the detail view be displayed when selecting a FinishedUnit/FinishedGood from the list? → A: Modal dialog over the list view

## User Scenarios & Testing

### User Story 1 - Record Batch Production (Priority: P1)

As a baker, I want to record when I make batches of a recipe so that my ingredient inventory is automatically updated and I can track production history.

**Why this priority**: This is the core workflow - without production recording, the inventory system cannot track what has been made and consumed. This directly enables FIFO accuracy for ingredients.

**Independent Test**: Can be fully tested by selecting a FinishedUnit, entering batch count and yield, and verifying ingredient inventory decreases while FinishedUnit inventory increases.

**Acceptance Scenarios**:

1. **Given** I am viewing a FinishedUnit detail view with associated recipe, **When** I click "Record Production", **Then** a dialog opens showing availability check results for all required ingredients.

2. **Given** the Record Production dialog is open and all ingredients show sufficient inventory (green), **When** I enter batch count (e.g., 2), adjust actual yield if needed, and click Confirm, **Then** the production is recorded, ingredient inventory is consumed via FIFO, and FinishedUnit inventory increases by actual yield.

3. **Given** the Record Production dialog shows insufficient inventory for one or more ingredients (red), **When** I try to confirm, **Then** the Confirm button is disabled and I see which ingredients are missing and by how much.

4. **Given** I have just recorded production, **When** I view the FinishedUnit detail, **Then** the inventory count reflects the new quantity immediately.

---

### User Story 2 - View Production Availability (Priority: P1)

As a baker, I want to see "Can I make this?" availability status before recording production so I know if I have enough ingredients.

**Why this priority**: Directly supports the production workflow - users need visibility before committing to avoid failed operations.

**Independent Test**: Can be tested by opening the Record Production dialog for any FinishedUnit and verifying color-coded ingredient availability display.

**Acceptance Scenarios**:

1. **Given** I open the Record Production dialog for a FinishedUnit, **When** the dialog loads, **Then** I see a list of all required ingredients with current availability status (green=sufficient, red=insufficient).

2. **Given** I change the batch count in the dialog, **When** the count changes, **Then** the availability status updates to reflect the new ingredient requirements.

3. **Given** an ingredient has partial availability (e.g., need 500g, have 300g), **When** I view availability, **Then** I see both the needed amount and available amount clearly displayed.

---

### User Story 3 - Record Assembly (Priority: P2)

As a baker, I want to record when I assemble gift packages so that my FinishedUnit and packaging inventory is automatically updated.

**Why this priority**: Completes the production workflow by enabling package assembly tracking. Depends on FinishedUnits existing from production.

**Independent Test**: Can be tested by selecting a FinishedGood, entering quantity to assemble, and verifying component inventory (FinishedUnits and packaging) decreases while FinishedGood inventory increases.

**Acceptance Scenarios**:

1. **Given** I am viewing a FinishedGood detail view with defined components, **When** I click "Record Assembly", **Then** a dialog opens showing availability check results for all required components (FinishedUnits and packaging).

2. **Given** the Record Assembly dialog is open and all components show sufficient inventory, **When** I enter quantity to assemble and click Confirm, **Then** the assembly is recorded, component inventory is consumed, and FinishedGood inventory increases.

3. **Given** the Record Assembly dialog shows insufficient inventory for one or more components, **When** I view the dialog, **Then** I see which components are missing and the Confirm button is disabled.

---

### User Story 4 - View Production History (Priority: P2)

As a baker, I want to view production history for a FinishedUnit so I can see when batches were made, how many, and at what cost.

**Why this priority**: Provides operational visibility and supports cost analysis. Not blocking for core production workflow.

**Independent Test**: Can be tested by viewing a FinishedUnit that has production runs and verifying history table displays correct data.

**Acceptance Scenarios**:

1. **Given** I am viewing a FinishedUnit detail view, **When** the view loads, **Then** I see a production history section showing past production runs.

2. **Given** production history exists for this FinishedUnit, **When** I view the history, **Then** each entry shows date, batch count, actual yield, and total cost.

3. **Given** no production history exists, **When** I view the history section, **Then** I see an appropriate empty state message.

---

### User Story 5 - View Assembly History (Priority: P2)

As a baker, I want to view assembly history for a FinishedGood so I can see when assemblies were created and at what cost.

**Why this priority**: Provides operational visibility for assembly operations. Parallel to production history.

**Independent Test**: Can be tested by viewing a FinishedGood that has assembly runs and verifying history table displays correct data.

**Acceptance Scenarios**:

1. **Given** I am viewing a FinishedGood detail view, **When** the view loads, **Then** I see an assembly history section showing past assembly runs.

2. **Given** assembly history exists for this FinishedGood, **When** I view the history, **Then** each entry shows date, quantity assembled, and total cost.

---

### User Story 6 - Production Dashboard Overview (Priority: P3)

As a baker, I want a Production Dashboard tab showing recent production and assembly activity so I can see what has been made recently.

**Why this priority**: Convenience feature for overview - individual detail views already provide this information.

**Independent Test**: Can be tested by navigating to Production tab and verifying recent runs are displayed with timestamps.

**Acceptance Scenarios**:

1. **Given** I navigate to the Production tab, **When** the tab loads, **Then** I see two sections: Recent Production Runs and Recent Assembly Runs.

2. **Given** production runs exist within the last 30 days, **When** I view the Production tab, **Then** I see those runs listed with recipe name, date, batches, and yield.

3. **Given** I want to record new production or assembly, **When** I click the navigation link in the Production tab, **Then** I am taken to the FinishedUnits or FinishedGoods list view.

---

### User Story 7 - FinishedUnit Detail View (Priority: P1)

As a baker, I want a FinishedUnit detail view that shows complete information including inventory, costs, and production history so I can manage individual items.

**Why this priority**: Required entry point for production recording. The existing view needs updates to integrate with Feature 013 services.

**Independent Test**: Can be tested by selecting any FinishedUnit and verifying all detail sections render correctly.

**Acceptance Scenarios**:

1. **Given** I select a FinishedUnit from the list, **When** the detail view opens, **Then** I see: display name, recipe link, inventory count, unit cost, and production history.

2. **Given** I am viewing a FinishedUnit detail, **When** I click "Record Production", **Then** the production recording dialog opens for this item.

---

### User Story 8 - FinishedGood Detail View (Priority: P2)

As a baker, I want a FinishedGood detail view that shows complete information including inventory, composition, and assembly history so I can manage gift packages.

**Why this priority**: Required entry point for assembly recording. This view is currently missing from the application.

**Independent Test**: Can be tested by selecting any FinishedGood and verifying all detail sections render correctly.

**Acceptance Scenarios**:

1. **Given** I select a FinishedGood from the list, **When** the detail view opens, **Then** I see: display name, inventory count, total cost, composition (components), and assembly history.

2. **Given** I am viewing a FinishedGood detail, **When** I click "Record Assembly", **Then** the assembly recording dialog opens for this item.

---

### Edge Cases

- What happens when production is attempted with zero batches? System should validate and reject.
- What happens when yield is set to zero? System should allow (for failed batches) but warn user.
- How does system handle decimal packaging quantities? Uses Decimal precision from FIFO service.
- What happens if a FinishedUnit has no associated recipe? Record Production button should be disabled with tooltip explanation.
- What happens if a FinishedGood has no defined components? Record Assembly button should be disabled with tooltip explanation.
- What happens if production is recorded while another user is editing inventory? Transaction atomicity from Feature 013 handles this.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a Record Production dialog accessible from FinishedUnit detail view
- **FR-002**: System MUST display ingredient availability check results before production confirmation with color coding (green=sufficient, red=insufficient)
- **FR-003**: System MUST allow users to specify batch count and optionally adjust actual yield before confirming production
- **FR-004**: System MUST call BatchProductionService.record_batch_production() when production is confirmed
- **FR-005**: System MUST update displayed inventory counts immediately after successful production recording
- **FR-006**: System MUST provide a Record Assembly dialog accessible from FinishedGood detail view
- **FR-007**: System MUST display component availability check (FinishedUnits and packaging) before assembly confirmation
- **FR-008**: System MUST call AssemblyService.record_assembly() when assembly is confirmed
- **FR-009**: System MUST display production history for a FinishedUnit showing date, batches, yield, and cost
- **FR-010**: System MUST display assembly history for a FinishedGood showing date, quantity, and cost
- **FR-011**: System MUST provide a Production Dashboard tab with recent production runs (last 30 days)
- **FR-012**: System MUST provide navigation links from Production Dashboard to FinishedUnits and FinishedGoods list views
- **FR-013**: System MUST disable Confirm button when availability check shows insufficient inventory
- **FR-014**: System MUST display clear error messages when recording fails (e.g., concurrent modification)
- **FR-015**: System MUST provide FinishedUnit detail view as a modal dialog with inventory, costs, recipe link, and production history
- **FR-016**: System MUST provide FinishedGood detail view as a modal dialog with inventory, costs, composition, and assembly history
- **FR-017**: System MUST allow optional notes field when recording production or assembly

### Key Entities

- **FinishedUnit**: Individual consumable items produced from recipes (e.g., "Sugar Cookie"). Has inventory_count, unit_cost, and recipe association.
- **FinishedGood**: Assembled gift packages containing FinishedUnits and packaging (e.g., "Holiday Cookie Box"). Has inventory_count, total_cost, and composition.
- **ProductionRun**: Record of a batch production event with recipe, batches, yield, cost, and consumption ledger.
- **AssemblyRun**: Record of an assembly event with components consumed and FinishedGoods produced.
- **Composition**: Bill of materials linking FinishedGood to its components (FinishedUnits, nested FinishedGoods, packaging products).

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can complete a production recording workflow (open dialog, check availability, confirm) in under 30 seconds
- **SC-002**: Users can complete an assembly recording workflow in under 30 seconds
- **SC-003**: 100% of production recordings correctly update both ingredient inventory and FinishedUnit inventory atomically
- **SC-004**: 100% of assembly recordings correctly update component inventory and FinishedGood inventory atomically
- **SC-005**: Users can view production history for any FinishedUnit within 2 clicks from the list view
- **SC-006**: Users can view assembly history for any FinishedGood within 2 clicks from the list view
- **SC-007**: Availability check results display within 1 second of dialog open or manual refresh
- **SC-008**: Inventory counts refresh automatically after recording without manual page refresh
