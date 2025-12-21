# Feature Specification: Deferred Packaging Decisions

**Feature Branch**: `026-deferred-packaging-decisions`
**Created**: 2025-12-21
**Status**: Draft
**Input**: User description: "Enable bakers to plan events with generic packaging requirements, deferring specific design selection until assembly time while maintaining cost estimates and inventory awareness."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plan Event with Generic Packaging (Priority: P1)

As a baker planning an event, I want to specify generic packaging requirements (e.g., "Cellophane Bags 6x10") without choosing specific designs, so I can focus on food production decisions first.

**Why this priority**: This is the core enabling capability. Without the ability to select generic packaging at planning time, the entire feature has no value. This establishes the foundation for all other stories.

**Independent Test**: Can be fully tested by creating an event, adding a finished good with generic packaging, and verifying the planning screen shows inventory summary and estimated cost. Delivers immediate planning flexibility.

**Acceptance Scenarios**:

1. **Given** I am defining packaging for a finished good in event planning, **When** I select "Generic product" mode and choose a packaging product, **Then** I see available inventory summary (e.g., "82 bags across 4 designs") and estimated cost based on average price.

2. **Given** I have selected a generic packaging product, **When** I enter a quantity needed, **Then** the system validates availability against total inventory (all designs combined) and shows whether requirements can be fulfilled.

3. **Given** I have saved an event with generic packaging, **When** I reopen the event, **Then** the generic packaging selection is preserved with current inventory summary.

---

### User Story 2 - Assign Specific Materials at Assembly Time (Priority: P2)

As a baker ready to assemble finished goods, I want to assign specific packaging materials from my inventory to fulfill generic requirements, so I can make aesthetic decisions when I'm ready.

**Why this priority**: This is the second half of the core workflow - planning with generic, then assigning specific. Without assignment capability, generic packaging creates orphaned requirements.

**Independent Test**: Can be tested with pre-existing generic packaging requirements by opening assembly definition, selecting specific materials from inventory, and saving assignments.

**Acceptance Scenarios**:

1. **Given** I have a finished good with unassigned generic packaging (e.g., "50 Cellophane Bags 6x10 needed"), **When** I open the assembly definition screen, **Then** I see a list of available specific materials with current inventory counts.

2. **Given** I am assigning materials, **When** I select materials and enter quantities, **Then** I see a running total ("Assigned: 30 / 50 needed") and validation prevents saving unless total matches requirement.

3. **Given** I have assigned specific materials, **When** I view cost estimates, **Then** costs change from "Estimated" to "Actual" based on selected materials.

---

### User Story 3 - View Pending Packaging Decisions on Dashboard (Priority: P3)

As a baker with in-progress productions, I want to see a clear indicator when packaging decisions are pending, so I know which items need attention before assembly.

**Why this priority**: Visibility helps users track their workflow, but the core planning and assignment functions work without this indicator.

**Independent Test**: Can be tested by creating events with unassigned generic packaging and verifying the dashboard displays pending indicators with clickable links to assignment.

**Acceptance Scenarios**:

1. **Given** I have productions with unassigned generic packaging, **When** I view the production dashboard, **Then** I see a visual indicator (icon or badge) on affected items.

2. **Given** I see a pending packaging indicator, **When** I click on it, **Then** I am taken to the packaging assignment screen for that item.

---

### User Story 4 - Generate Shopping List with Generic Packaging (Priority: P3)

As a baker preparing to shop, I want shopping lists to show generic packaging needs (not specific designs), so I can purchase whatever designs are available at the store.

**Why this priority**: Shopping list presentation is a read-only display feature that enhances usability but doesn't block core workflow.

**Independent Test**: Can be tested by generating a shopping list for an event with generic packaging and verifying items display as generic products with estimated costs.

**Acceptance Scenarios**:

1. **Given** I have planned events with generic packaging requirements, **When** I generate a shopping list, **Then** packaging items appear as generic products (e.g., "Cellophane Bags 6x10: 50 needed") not specific designs.

2. **Given** the shopping list shows generic packaging, **When** I view costs, **Then** estimated costs are displayed and labeled as "estimated."

---

### User Story 5 - Handle Assembly with Unassigned Packaging (Priority: P4)

As a baker recording assembly progress, I want to be prompted about unassigned packaging but allowed to proceed anyway, so I can record work and finalize packaging later if needed.

**Why this priority**: This is an edge case handler for real-world flexibility. Core workflow assumes assignment before assembly.

**Independent Test**: Can be tested by attempting to record assembly completion with unassigned generic packaging and verifying prompt appears with bypass option.

**Acceptance Scenarios**:

1. **Given** I am recording assembly for a recipe with unassigned packaging, **When** I attempt to complete, **Then** I see a prompt about unassigned packaging with options to "Quick Assign," go to "Assembly Details," or "Record Assembly Anyway."

2. **Given** I choose "Record Assembly Anyway," **When** assembly is recorded, **Then** the event is flagged for later packaging reconciliation.

---

### User Story 6 - Modify Packaging During Assembly (Priority: P4)

As a baker who discovers my cookies don't fit the planned boxes, I want to change packaging requirements during assembly, so I can adapt to real-world situations.

**Why this priority**: This is an edge case for plan modifications. Core workflow assumes requirements are stable.

**Independent Test**: Can be tested by opening assembly definition, removing a packaging requirement, adding a different one, and verifying costs and inventory recalculate.

**Acceptance Scenarios**:

1. **Given** I am in assembly definition with assigned packaging, **When** I modify the BOM (remove boxes, add bags), **Then** the system recalculates costs and checks inventory availability for new requirements.

2. **Given** I have modified packaging requirements, **When** I save changes, **Then** previous assignments are cleared and new generic requirements appear for assignment.

---

### Edge Cases

- **Insufficient inventory at assignment**: When planning used 50 bags but only 45 remain at assembly time, system shows shortage warning ("Available: 45 / 50 needed") and allows partial assignment with flagged shortage.

- **Re-assignment before completion**: User can reopen assignment screen and change selections any time before assembly completion, with cost estimates updating accordingly.

- **Shopping after planning, before assignment**: When user purchases generic packaging (e.g., "6x10 bags"), they must choose specific design at purchase. Generic requirement's availability totals update to reflect new inventory.

- **Zero inventory for generic product**: When no materials exist for a generic product, planning shows "0 available" warning but still allows requirement creation for shopping purposes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to choose between "Specific material" and "Generic product" when adding packaging to a finished good.

- **FR-002**: System MUST display inventory summary for generic products showing total quantity and breakdown by design (e.g., "82 bags: Snowflakes (30), Holly (25), Stars (20), Snowmen (7)").

- **FR-003**: System MUST calculate and display estimated cost for generic packaging based on average price across available materials in inventory.

- **FR-004**: System MUST clearly label costs as "Estimated" for unassigned generic packaging and "Actual" for assigned specific materials.

- **FR-005**: System MUST provide an assignment interface where users can select specific materials and quantities to fulfill generic requirements.

- **FR-006**: System MUST validate that total assigned quantity equals total required quantity before saving assignments.

- **FR-007**: System MUST display visual indicators on the production dashboard for items with pending packaging decisions.

- **FR-008**: System MUST generate shopping lists with generic packaging represented abstractly (product type and quantity), not as specific designs.

- **FR-009**: System MUST prompt users about unassigned packaging when recording assembly completion, with option to proceed anyway.

- **FR-010**: System MUST flag events where assembly was recorded with unassigned packaging for later reconciliation.

- **FR-011**: System MUST allow users to modify packaging requirements (add/remove) during assembly, with automatic recalculation of costs and availability.

- **FR-012**: System MUST persist generic packaging selections and their assignment status across sessions.

### Key Entities

- **PackagingRequirement**: Represents a packaging need for a finished good. Links to either a specific material (existing behavior) or a generic product (new behavior). Tracks assignment status and quantity needed.

- **PackagingAssignment**: Junction between a PackagingRequirement and specific inventory items. Records which materials fulfill the requirement and in what quantities.

- **GenericProduct**: Represents a packaging product type (e.g., "Cellophane Bags 6x10") without design specificity. Groups specific materials that can fulfill the same requirement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete event packaging planning in the same time or faster than current specific-material-only workflow.

- **SC-002**: 100% of generic packaging requirements can be fulfilled by any combination of available specific materials of the same product type.

- **SC-003**: Cost estimates for generic packaging are within 15% of actual costs when materials are assigned (accounting for price variation between designs).

- **SC-004**: Users can identify all pending packaging decisions from the dashboard within 5 seconds.

- **SC-005**: Shopping lists generated with generic packaging are comprehensible without knowledge of specific designs in inventory.

- **SC-006**: Users can complete packaging assignment for a finished good in under 1 minute.

- **SC-007**: System prevents assembly recording without packaging assignment unless user explicitly bypasses.

## Assumptions

- Packaging products have a hierarchical relationship: generic products group specific materials (designs).
- Price variation between designs of the same product type is typically small (within 15%).
- Users understand the distinction between planning (generic) and execution (specific).
- The existing Product model or a related entity can represent the generic/specific relationship.
- Dashboard already exists and can be extended with pending indicators.
