# Feature Specification: Event-Centric Production Model

**Feature Branch**: `015-event-centric-production`
**Created**: 2025-12-10
**Status**: Draft
**Priority**: CRITICAL (Structural Fix)
**Input**: Architecture gap analysis during Feature 015 (Reporting) discovery phase

## Problem Statement

The current architecture conflates three distinct concerns:

| Concern | Question | Current Status |
|---------|----------|----------------|
| Definition | What IS a Cookie Gift Box? | ✅ FinishedGood + Composition |
| Inventory | How many EXIST globally? | ✅ inventory_count |
| Commitment | How many are FOR Christmas 2025? | ❌ **MISSING** |

**Root Cause:** `ProductionRun` and `AssemblyRun` have no `event_id` foreign key. When production is recorded, it cannot be attributed to a specific event.

**Impact:**
- Cannot track event progress ("Am I on track for Christmas?")
- Cannot show planned vs actual in reports
- Cannot support multi-event planning (Christmas + Easter overlap)
- Package fulfillment status not tracked

**Design Document:** `docs/design/schema_v0.6_design.md`

---

## User Scenarios & Testing

### User Story 1 - Link Production to Event (Priority: P1)

As a baker, I want to record production for a specific event so that I can track how much I've made toward my holiday commitments.

**Why this priority**: Core requirement - without event linkage, all subsequent progress tracking is impossible.

**Independent Test**: Can be tested by recording production with an event selected, then querying production runs filtered by event_id.

**Acceptance Scenarios**:

1. **Given** I am recording production for a FinishedUnit, **When** the Record Production dialog opens, **Then** I see an optional "For Event" dropdown listing active events (plus "None - standalone" option).

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

3. **Given** I have exceeded target, **When** I view progress, **Then** I see over-completion indicator (e.g., "12/10 (120%) ✓").

---

### User Story 7 - Track Package Fulfillment Status (Priority: P2)

As a baker, I want to track the status of each package assignment so that I know which gifts are pending, ready, or delivered.

**Why this priority**: Enables fulfillment workflow - useful but not blocking for core progress tracking.

**Independent Test**: Can be tested by changing fulfillment status on package assignments and verifying persistence.

**Acceptance Scenarios**:

1. **Given** I am viewing package assignments for an event, **When** the list displays, **Then** each assignment shows a "Status" column with current value (Pending/Ready/Delivered).

2. **Given** I click on the Status dropdown for an assignment, **When** I select a new status, **Then** the status updates immediately and persists to database.

3. **Given** multiple assignments exist, **When** I view the assignments list, **Then** I can filter by status (e.g., "Show only Pending").

4. **Given** I mark a package as "Delivered", **When** viewing event summary, **Then** the delivered count increases.

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

### User Story 9 - Suggest Targets from Package Assignments (Priority: P3)

As a baker, I want the system to suggest production targets based on my package assignments so that I don't have to calculate requirements manually.

**Why this priority**: Nice-to-have automation - manual target setting already works.

**Independent Test**: Can be tested by creating package assignments, invoking suggestion, and verifying reasonable target values.

**Acceptance Scenarios**:

1. **Given** I have package assignments for an event, **When** I click "Suggest Targets", **Then** the system calculates required batches/quantities based on compositions and displays suggestions.

2. **Given** suggestions are displayed, **When** I click "Accept Suggestions", **Then** targets are created from the suggestions (or existing targets are updated).

3. **Given** I have existing targets, **When** suggestions are calculated, **Then** the system shows "Current: 4, Suggested: 6" for comparison.

---

### Edge Cases

- What happens to existing ProductionRun/AssemblyRun records after migration? They get event_id = NULL (standalone).
- What happens if an event is deleted that has production attributed to it? Cascade strategy: ProductionRun/AssemblyRun retain their data but event_id becomes NULL (SET NULL on delete).
- What happens if a recipe is deleted that has a production target? Restrict delete - must remove target first.
- What happens if target is set to 0? System should reject (target must be > 0).
- What happens if user records more than target? Allow - track as over-production with 100%+ progress.
- Can targets be negative? No - constraint enforces positive values.
- Can the same production run be attributed to multiple events? No - single event_id FK.

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
- **FR-008**: Deleting an Event MUST SET NULL on ProductionRun.event_id and AssemblyRun.event_id (not cascade delete runs)
- **FR-009**: Deleting a Recipe MUST be restricted if EventProductionTarget references it
- **FR-010**: Deleting a FinishedGood MUST be restricted if EventAssemblyTarget references it

**Service Requirements:**
- **FR-011**: BatchProductionService.record_batch_production() MUST accept optional event_id parameter
- **FR-012**: AssemblyService.record_assembly() MUST accept optional event_id parameter
- **FR-013**: EventService MUST provide set_production_target(event_id, recipe_id, target_batches, notes) method
- **FR-014**: EventService MUST provide set_assembly_target(event_id, finished_good_id, target_quantity, notes) method
- **FR-015**: EventService MUST provide get_production_progress(event_id) returning list of progress records
- **FR-016**: EventService MUST provide get_assembly_progress(event_id) returning list of progress records
- **FR-017**: Progress calculation MUST only count runs where event_id matches (exclude NULL/other events)
- **FR-018**: EventService MUST provide update_fulfillment_status(erp_id, status) method
- **FR-019**: EventService MUST provide get_packages_by_status(event_id, status) method

**UI Requirements:**
- **FR-020**: Record Production dialog MUST include optional Event selector dropdown
- **FR-021**: Record Assembly dialog MUST include optional Event selector dropdown
- **FR-022**: Event Detail window MUST include Targets tab with Production and Assembly target lists
- **FR-023**: Targets tab MUST display progress (produced/target, percentage, visual bar) for each target
- **FR-024**: Package assignments view MUST display fulfillment status column with editable dropdown
- **FR-025**: Event Summary tab MUST display overall progress metrics

**Import/Export Requirements:**
- **FR-026**: Export MUST include EventProductionTarget and EventAssemblyTarget entities
- **FR-027**: Export MUST include event_name in ProductionRun and AssemblyRun records
- **FR-028**: Export MUST include fulfillment_status in EventRecipientPackage records
- **FR-029**: Import MUST resolve event_name references to event_id
- **FR-030**: Import MUST handle NULL event_name (standalone production)

### Key Entities

- **ProductionRun**: Extended with nullable event_id FK
- **AssemblyRun**: Extended with nullable event_id FK
- **EventProductionTarget**: NEW - Links Event to Recipe with target_batches
- **EventAssemblyTarget**: NEW - Links Event to FinishedGood with target_quantity
- **EventRecipientPackage**: Extended with fulfillment_status (pending/ready/delivered)
- **FulfillmentStatus**: NEW enum - pending, ready, delivered

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of production/assembly runs can be optionally linked to an event via event_id
- **SC-002**: Users can set production targets for an event in under 60 seconds per recipe
- **SC-003**: Users can view production progress (produced vs target) within 2 clicks from event list
- **SC-004**: Progress percentages are calculated correctly (produced_batches / target_batches * 100)
- **SC-005**: Over-production is displayed correctly (> 100% when exceeds target)
- **SC-006**: Fulfillment status changes persist immediately without page refresh
- **SC-007**: Migration preserves all existing ProductionRun/AssemblyRun data with event_id = NULL
- **SC-008**: Import/export round-trip preserves all event-production relationships

---

## Technical Notes

### Migration Strategy

1. Export all data using existing import/export
2. Add new columns and tables to models
3. Delete and recreate database
4. Import data - new columns get default values:
   - ProductionRun.event_id → NULL
   - AssemblyRun.event_id → NULL
   - EventRecipientPackage.fulfillment_status → 'pending'

### Cascade/Restrict Strategy

| Parent Delete | Child Behavior |
|---------------|----------------|
| Event deleted | EventProductionTarget CASCADE deleted |
| Event deleted | EventAssemblyTarget CASCADE deleted |
| Event deleted | ProductionRun.event_id SET NULL |
| Event deleted | AssemblyRun.event_id SET NULL |
| Recipe deleted | RESTRICT if EventProductionTarget exists |
| FinishedGood deleted | RESTRICT if EventAssemblyTarget exists |

### Progress Calculation

```python
def get_production_progress(event_id: int) -> List[dict]:
    """
    For each EventProductionTarget:
    1. Get target_batches from target
    2. Sum ProductionRun.num_batches WHERE event_id = this event AND recipe_id = target.recipe_id
    3. Calculate percentage
    4. Return progress record
    """
```

---

## Dependencies

- **Requires**: Features 013 (BatchProductionService, AssemblyService) - COMPLETE ✅
- **Requires**: Feature 014 (Production UI dialogs) - COMPLETE ✅
- **Blocks**: Feature 016 (Reporting) - Cannot show accurate event reports without event linkage
- **Blocks**: Feature 017 (Event Dashboard) - Cannot show event progress without targets
