# Feature Specification: Finished Goods Quantity Specification

**Feature Branch**: `071-finished-goods-quantity-specification`
**Created**: 2026-01-27
**Status**: Draft
**Input**: User description: "see docs/func-spec/F071_quantity_specification.md for feature inputs"

## User Scenarios & Testing

### User Story 1 - Specify Quantities for Event (Priority: P1)

As a user planning an event, I want to specify how many of each finished good to produce, so that I know my production targets and can plan accordingly.

**Why this priority**: This is the core value of the feature. Without quantity specification, users cannot define what they're actually producing for an event. This completes the basic event definition workflow.

**Independent Test**: Can be fully tested by opening an event, entering quantities for available finished goods, saving, and verifying quantities persist. Delivers immediate value by allowing complete event production planning.

**Acceptance Scenarios**:

1. **Given** an event is open with available finished goods displayed, **When** I enter a positive integer (e.g., "24") in a finished good's quantity field, **Then** the value is accepted and displayed in the field.

2. **Given** an event with finished goods displayed, **When** I enter quantities for multiple finished goods and save, **Then** all quantities are persisted to the database.

3. **Given** I enter an invalid value (zero, negative, or non-integer), **When** I try to save or leave the field, **Then** I see an inline validation error and the invalid value is not saved.

---

### User Story 2 - Load Existing Quantities (Priority: P2)

As a user returning to an event I previously worked on, I want to see the quantities I already entered, so that I can continue planning without re-entering data.

**Why this priority**: Essential for usability - users must be able to save work and return to it. Without this, users would need to complete all planning in one session.

**Independent Test**: Can be tested by entering quantities, closing the event, reopening it, and verifying quantities are pre-populated in the correct fields.

**Acceptance Scenarios**:

1. **Given** an event has saved quantities for finished goods, **When** I open that event, **Then** quantity input fields are pre-populated with the saved values.

2. **Given** an event has some finished goods with quantities and some without, **When** I open the event, **Then** FGs with quantities show their values and FGs without quantities show empty fields.

---

### User Story 3 - Modify Quantities (Priority: P3)

As a user whose plans have changed, I want to update the quantities I previously entered, so that my event reflects current production needs.

**Why this priority**: Natural extension of P1 and P2. Users' plans change; they need to adjust quantities without starting over.

**Independent Test**: Can be tested by loading an event with existing quantities, changing values, saving, and verifying the changes persist.

**Acceptance Scenarios**:

1. **Given** an event with a saved quantity of 24 for a finished good, **When** I change it to 36 and save, **Then** the database reflects the new quantity of 36.

2. **Given** an event with a saved quantity for a finished good, **When** I clear the quantity field (empty) and save, **Then** the finished good is removed from the event (no record in event_finished_goods).

3. **Given** an event where I add a quantity to a previously unselected finished good, **When** I save, **Then** a new record is created in event_finished_goods.

---

### Edge Cases

- What happens when user enters leading zeros (e.g., "007")? System accepts and normalizes to integer value (7).
- What happens when user enters decimal values (e.g., "24.5")? System shows validation error - integers only.
- What happens when user pastes text into quantity field? System shows validation error - integers only.
- What happens when a finished good becomes unavailable after quantities were entered? The FG and its quantity are removed (handled by F070 auto-removal logic).
- What happens when user tabs through all fields without entering anything? Empty fields are valid - no quantities saved for those FGs.

## Requirements

### Functional Requirements

- **FR-001**: System MUST display a quantity input field next to each available finished good in the Planning Tab.
- **FR-002**: System MUST accept only positive integers (1 or greater) as valid quantity values.
- **FR-003**: System MUST show inline validation errors when users enter invalid values (zero, negative, non-integer, or non-numeric).
- **FR-004**: System MUST persist quantities to the event_finished_goods table when saved.
- **FR-005**: System MUST load and pre-populate existing quantities when an event is opened.
- **FR-006**: System MUST support modification of quantities after initial entry.
- **FR-007**: System MUST remove the event_finished_goods record when a quantity is cleared (empty field).
- **FR-008**: System MUST replace (not append) quantities when saving - only current non-empty quantities are stored.
- **FR-009**: System MUST validate that referenced finished goods are valid before persisting.
- **FR-010**: System MUST provide logical tab order for efficient data entry across quantity fields.

### Key Entities

- **EventFinishedGood**: Junction table linking events to finished goods with quantities. Key attributes: event_id (FK), finished_good_id (FK), quantity (positive integer). Already exists from F068.
- **FinishedGood**: The product being produced. Referenced by EventFinishedGood. Already exists.
- **Event**: The event being planned. Referenced by EventFinishedGood. Already exists.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can specify quantities for all available finished goods in under 30 seconds per FG (simple numeric entry).
- **SC-002**: 100% of saved quantities are correctly persisted and retrievable on event reload.
- **SC-003**: 100% of invalid quantity entries (zero, negative, non-integer) are rejected with clear error messages.
- **SC-004**: Users can complete the full event definition workflow (recipes + FGs + quantities) without leaving the Planning Tab.

## Assumptions

- The event_finished_goods table already exists with the correct schema (event_id, finished_good_id, quantity) from F068.
- The Planning Tab already displays available finished goods from F070.
- Existing numeric input patterns and validation approaches exist in the codebase to follow.
- PlanningService from F068 provides patterns for CRUD operations to extend.

## Out of Scope

- Bulk quantity entry (copy/paste lists)
- Quantity suggestions based on event attendees or history
- Historical quantity defaults
- Batch calculation (F073 - happens after quantities are set)
- Assembly feasibility checking (F076)
- Maximum quantity limits or confirmation dialogs for large values
