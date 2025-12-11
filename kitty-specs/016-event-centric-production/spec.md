# Feature Specification: Event-Centric Production Model

**Feature Branch**: `016-event-centric-production`
**Created**: 2025-12-10
**Status**: Draft
**Priority**: CRITICAL (Structural Fix)
**Input**: Architecture gap analysis - ProductionRun/AssemblyRun lack event attribution

## Problem Statement

The current architecture cannot answer "How much have I made FOR Christmas 2025?" because ProductionRun and AssemblyRun have no `event_id` foreign key. When production is recorded, it cannot be attributed to a specific event.

**Impact**:
- Cannot track event progress ("Am I on track for Christmas?")
- Cannot show planned vs actual in reports
- Cannot support multi-event planning (Christmas + Easter overlap)
- Package fulfillment status not tracked

**Design Document**: `docs/design/schema_v0.6_design.md`

---

## User Scenarios & Testing

### User Story 1 - Link Production to Event (Priority: P1)

As a baker, I want to record production for a specific event so that I can track how much I've made toward my holiday commitments.

**Why this priority**: Core requirement - without event linkage, all subsequent progress tracking is impossible.

**Independent Test**: Can be tested by recording production with an event selected, then querying production runs filtered by event_id.

**Acceptance Scenarios**:

1. **Given** I am recording production for a recipe, **When** the Record Production dialog opens, **Then** I see an optional "For Event" dropdown listing active events (plus "None - standalone" option).

2. **Given** I select "Christmas 2025" from the event dropdown and confirm production, **When** the production is recorded, **Then** the ProductionRun record has event_id set to the Christmas 2025 event.

3. **Given** I select "None - standalone" (or leave blank), **When** the production is recorded, **Then** the ProductionRun record has event_id = NULL.

4. **Given** I want to record production for an event that doesn't exist yet, **When** I view the event dropdown, **Then** I see only existing events (must create event first in Events tab).

---

### User Story 2 - Link Assembly to Event (Priority: P1)

As a baker, I want to record assembly for a specific event so that I can track how many gift packages I've assembled toward my holiday commitments.

**Why this priority**: Parallel to production linkage - required for complete event attribution.

**Independent Test**: Can be tested by recording assembly with an event selected, then querying assembly runs filtered by event_id.

**Acceptance Scenarios**:

1. **Given** I am recording assembly for a FinishedGood, **When** the Record Assembly dialog opens, **Then** I see an optional "For Event" dropdown listing active events.

2. **Given** I select "Christmas 2025" and confirm assembly, **When** the assembly is recorded, **Then** the AssemblyRun record has event_id set to Christmas 2025.

3. **Given** I select no event, **When** the assembly is recorded, **Then** the AssemblyRun record has event_id = NULL.

---

### User Story 3 - Set Production Targets for Event (Priority: P1)

As a baker, I want to set production targets for an event so that I know how many batches of each recipe I need to make.

**Why this priority**: Targets enable progress tracking. Without targets, "progress" is undefined.

**Independent Test**: Can be tested by navigating to Event detail, adding targets, and verifying they persist in EventProductionTarget table.

**Acceptance Scenarios**:

1. **Given** I am viewing an Event detail window, **When** I navigate to the "Targets" tab, **Then** I see two sections: "Production Targets" (recipes) and "Assembly Targets" (finished goods).

2. **Given** I click "Add Production Target", **When** the dialog opens, **Then** I can select a Recipe and specify target batch count.

3. **Given** I add a target "Chocolate Chip Cookies - 4 batches", **When** I save, **Then** the target appears in the Production Targets list and persists in the database.

4. **Given** a production target already exists for a recipe, **When** I try to add another target for the same recipe, **Then** the system prevents duplicate and offers to edit existing target.

5. **Given** I select an existing target, **When** I click "Edit", **Then** I can modify the target batch count or delete the target.

---

### User Story 4 - Set Assembly Targets for Event (Priority: P1)

As a baker, I want to set assembly targets for an event so that I know how many of each gift package I need to assemble.

**Why this priority**: Parallel to production targets - required for assembly progress tracking.

**Independent Test**: Can be tested by adding assembly targets and verifying they persist in EventAssemblyTarget table.

**Acceptance Scenarios**:

1. **Given** I am on the Event Targets tab, **When** I click "Add Assembly Target", **Then** I can select a FinishedGood and specify target quantity.

2. **Given** I add a target "Cookie Gift Box - 10 units", **When** I save, **Then** the target appears in the Assembly Targets list.

3. **Given** an assembly target already exists for a finished good, **When** I try to add a duplicate, **Then** the system prevents it and offers to edit existing.

---

### User Story 5 - View Production Progress (Priority: P1)

As a baker, I want to see my production progress for an event so that I know if I'm on track to fulfill my commitments.

**Why this priority**: Primary user value - answers "where do I stand for Christmas?"

**Independent Test**: Can be tested by setting targets, recording production attributed to the event, and verifying progress display updates correctly.

**Acceptance Scenarios**:

1. **Given** I have production targets set for an event, **When** I view the Targets tab, **Then** each target shows: Recipe name, Target batches, Produced batches, Progress percentage, and visual progress bar.

2. **Given** I have produced 2 of 4 target batches for Chocolate Chip Cookies, **When** I view progress, **Then** I see "2/4 batches (50%)" with half-filled progress bar.

3. **Given** I have met or exceeded a target (e.g., 5/4 batches), **When** I view progress, **Then** I see "5/4 batches (125%)" with a completed checkmark indicator and different color (green/complete).

4. **Given** I have not started production on a target, **When** I view progress, **Then** I see "0/4 batches (0%)" with empty progress bar.

5. **Given** production runs exist for this event, **When** progress is calculated, **Then** only runs with matching event_id are counted (standalone runs excluded).

---

### User Story 6 - View Assembly Progress (Priority: P1)

As a baker, I want to see my assembly progress for an event so that I know how many gift packages I still need to assemble.

**Why this priority**: Parallel to production progress - required for complete event tracking.

**Independent Test**: Can be tested by setting assembly targets, recording assemblies for the event, and verifying progress display.

**Acceptance Scenarios**:

1. **Given** I have assembly targets set for an event, **When** I view the Targets tab, **Then** each target shows: FinishedGood name, Target quantity, Assembled quantity, Progress percentage.

2. **Given** I have assembled 6 of 10 Cookie Gift Boxes, **When** I view progress, **Then** I see "6/10 (60%)" with progress bar.

3. **Given** I have exceeded target, **When** I view progress, **Then** I see over-completion indicator (e.g., "12/10 (120%)") with checkmark.

---

### User Story 7 - Track Package Fulfillment Status (Priority: P2)

As a baker, I want to track the status of each package assignment so that I know which gifts are pending, ready, or delivered.

**Why this priority**: Enables fulfillment workflow - useful but not blocking for core progress tracking.

**Independent Test**: Can be tested by changing fulfillment status on package assignments and verifying persistence.

**Acceptance Scenarios**:

1. **Given** I am viewing package assignments for an event, **When** the list displays, **Then** each assignment shows a "Status" column with current value (Pending/Ready/Delivered).

2. **Given** a package has status "Pending", **When** I click on the Status dropdown, **Then** I can only select "Ready" (next sequential status).

3. **Given** a package has status "Ready", **When** I click on the Status dropdown, **Then** I can only select "Delivered" (next sequential status).

4. **Given** a package has status "Delivered", **When** I view the Status dropdown, **Then** no further changes are allowed (final state).

5. **Given** I change status from "Pending" to "Ready", **When** I view the list, **Then** the status updates immediately and persists to database.

---

### User Story 8 - Event Progress Summary (Priority: P2)

As a baker, I want to see an overall progress summary for an event so that I can quickly assess my status.

**Why this priority**: Convenience aggregation of progress data - individual progress already available.

**Independent Test**: Can be tested by setting targets and recording production/assembly, then verifying summary calculations.

**Acceptance Scenarios**:

1. **Given** I am viewing an Event, **When** I look at the Summary tab, **Then** I see overall progress metrics including: Production Complete (X of Y recipes at target), Assembly Complete (X of Y finished goods at target), Packages by status (Pending/Ready/Delivered counts).

2. **Given** all production targets are met, **When** I view summary, **Then** "Production Complete" shows a green checkmark.

3. **Given** some production targets are incomplete, **When** I view summary, **Then** "Production Complete" shows "3 of 5 recipes complete" with partial indicator.

---

### Edge Cases

- **Existing production records after migration**: ProductionRun/AssemblyRun records get event_id = NULL (standalone production).
- **Event deletion with attributed production**: RESTRICTED - cannot delete event if any ProductionRun or AssemblyRun is attributed to it.
- **Recipe deletion with production target**: RESTRICTED - must remove target first before deleting recipe.
- **FinishedGood deletion with assembly target**: RESTRICTED - must remove target first before deleting finished good.
- **Target set to zero or negative**: System rejects - target must be positive integer (> 0).
- **Over-production**: Allowed and displayed as >100% (e.g., "125%").
- **Same production attributed to multiple events**: Not allowed - single event_id FK per run.
- **Fulfillment status skip**: Not allowed - must follow sequential workflow (pending -> ready -> delivered).

---

## Requirements

### Functional Requirements

**Schema Requirements:**
- **FR-001**: ProductionRun MUST have nullable event_id FK to Event
- **FR-002**: AssemblyRun MUST have nullable event_id FK to Event
- **FR-003**: EventProductionTarget MUST enforce unique constraint on (event_id, recipe_id)
- **FR-004**: EventAssemblyTarget MUST enforce unique constraint on (event_id, finished_good_id)
- **FR-005**: EventRecipientPackage MUST have fulfillment_status field with values: pending, ready, delivered
- **FR-006**: Target batch counts and quantities MUST be positive integers (> 0)
- **FR-007**: Deleting an Event MUST cascade delete its targets (EventProductionTarget, EventAssemblyTarget)
- **FR-008**: Deleting an Event MUST be RESTRICTED if any ProductionRun or AssemblyRun references it
- **FR-009**: Deleting a Recipe MUST be RESTRICTED if EventProductionTarget references it
- **FR-010**: Deleting a FinishedGood MUST be RESTRICTED if EventAssemblyTarget references it

**Service Requirements:**
- **FR-011**: BatchProductionService.record_batch_production() MUST accept optional event_id parameter
- **FR-012**: AssemblyService.record_assembly() MUST accept optional event_id parameter
- **FR-013**: EventService MUST provide set_production_target(event_id, recipe_id, target_batches, notes) method
- **FR-014**: EventService MUST provide set_assembly_target(event_id, finished_good_id, target_quantity, notes) method
- **FR-015**: EventService MUST provide get_production_progress(event_id) returning list of progress records
- **FR-016**: EventService MUST provide get_assembly_progress(event_id) returning list of progress records
- **FR-017**: Progress calculation MUST only count runs where event_id matches (exclude NULL/other events)
- **FR-018**: EventService MUST provide update_fulfillment_status(erp_id, status) method
- **FR-019**: Fulfillment status updates MUST enforce sequential workflow (pending -> ready -> delivered only)
- **FR-020**: EventService MUST provide get_packages_by_status(event_id, status) method
- **FR-021**: EventService MUST provide delete_production_target(event_id, recipe_id) method
- **FR-022**: EventService MUST provide delete_assembly_target(event_id, finished_good_id) method

**UI Requirements:**
- **FR-023**: Record Production dialog MUST include optional Event selector dropdown ordered by event_date ascending (nearest upcoming first)
- **FR-024**: Record Assembly dialog MUST include optional Event selector dropdown ordered by event_date ascending (nearest upcoming first)
- **FR-025**: Event Detail window MUST include Targets tab with Production and Assembly target lists
- **FR-026**: Targets tab MUST display progress (produced/target, percentage, visual bar) for each target
- **FR-027**: Package assignments view MUST display fulfillment status column with sequential dropdown
- **FR-028**: Event Summary tab MUST display overall progress metrics

**Import/Export Requirements:**
- **FR-029**: Export MUST include EventProductionTarget and EventAssemblyTarget entities
- **FR-030**: Export MUST include event_name in ProductionRun and AssemblyRun records
- **FR-031**: Export MUST include fulfillment_status in EventRecipientPackage records
- **FR-032**: Import MUST resolve event_name references to event_id
- **FR-033**: Import MUST handle NULL event_name (standalone production)

### Key Entities

- **ProductionRun**: Extended with nullable event_id FK to Event
- **AssemblyRun**: Extended with nullable event_id FK to Event
- **EventProductionTarget**: NEW - Links Event to Recipe with target_batches (unique per event+recipe)
- **EventAssemblyTarget**: NEW - Links Event to FinishedGood with target_quantity (unique per event+finished_good)
- **EventRecipientPackage**: Extended with fulfillment_status (pending/ready/delivered)
- **FulfillmentStatus**: NEW enum - pending, ready, delivered

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of production/assembly runs can be optionally linked to an event via event_id
- **SC-002**: Users can set production targets for an event in under 60 seconds per recipe
- **SC-003**: Users can view production progress (produced vs target) within 2 clicks from event list
- **SC-004**: Progress percentages are calculated correctly (produced_batches / target_batches * 100)
- **SC-005**: Over-production is displayed correctly (> 100% when actual exceeds target)
- **SC-006**: Fulfillment status changes persist immediately without page refresh
- **SC-007**: Fulfillment status enforces sequential workflow (cannot skip from pending to delivered)
- **SC-008**: Migration preserves all existing ProductionRun/AssemblyRun data with event_id = NULL
- **SC-009**: Import/export round-trip preserves all event-production relationships

---

## Out of Scope

- **Auto-calculated targets from package assignments**: User Story 9 (Suggest Targets) is deferred to a future feature. Users must set targets manually.
- **Non-sequential fulfillment status changes**: Status must follow pending -> ready -> delivered workflow.
- **Reporting dashboards**: Feature 016+ will add reports using the event-production linkage created here.

---

## Dependencies

- **Requires**: Features 013 (BatchProductionService, AssemblyService) - COMPLETE
- **Requires**: Feature 014 (Production UI dialogs) - COMPLETE
- **Blocks**: Feature 016+ (Reporting) - Cannot show accurate event reports without event linkage

---

## Clarifications

### Session 2025-12-10

- Q: In the Event selector dropdown (Record Production/Assembly dialogs), how should active events be ordered? → A: Most recent event_date first (nearest upcoming)

---

## Assumptions

- Events already exist in the system before production/assembly is attributed to them
- The existing Event Detail window can accommodate a new "Targets" tab
- Package assignments already exist via EventRecipientPackage from prior features
