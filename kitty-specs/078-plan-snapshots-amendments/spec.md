# Feature Specification: Plan Snapshots & Amendments

**Feature Branch**: `078-plan-snapshots-amendments`
**Created**: 2026-01-27
**Status**: Draft
**Input**: F078 functional spec - Plan versioning and amendment logging for mid-production changes

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Plan Snapshot at Production Start (Priority: P1)

As a bakery planner, I want the system to automatically capture a complete snapshot of my plan when I start production, so that I have a permanent record of what I originally intended to produce.

**Why this priority**: Snapshots are the foundation for all amendment tracking. Without a baseline, there's nothing to compare amendments against.

**Independent Test**: Can be tested by locking a plan (F077), clicking "Start Production", and verifying that a snapshot record is created containing the original recipes, FGs, quantities, and batch decisions.

**Acceptance Scenarios**:

1. **Given** an event with plan_state = LOCKED, **When** user clicks "Start Production" (F077 transition), **Then** a plan snapshot is automatically created before the state changes to IN_PRODUCTION
2. **Given** a snapshot is created, **When** I query the snapshot, **Then** it contains: all EventRecipe records, all EventFinishedGood records with quantities, all BatchDecision records
3. **Given** a plan already has a snapshot, **When** the user attempts to start production again (invalid), **Then** no duplicate snapshot is created

---

### User Story 2 - Record Amendments During Production (Priority: P2)

As a bakery planner, I want to record amendments to my plan during production with required reasons, so that I have an audit trail of all changes made after the plan was locked.

**Why this priority**: Amendment recording is the core value proposition. Extends the snapshot baseline with change tracking.

**Independent Test**: Can be tested by starting production on an event, then using amendment controls to drop an FG, add an FG, or modify batch decisions, verifying each creates an amendment record with reason.

**Acceptance Scenarios**:

1. **Given** an event with plan_state = IN_PRODUCTION, **When** I submit a DROP_FG amendment with fg_id, original_quantity, and reason, **Then** an amendment record is created with type DROP_FG and the FG is removed from the current plan
2. **Given** an event with plan_state = IN_PRODUCTION, **When** I submit an ADD_FG amendment with fg_id, new_quantity, and reason, **Then** an amendment record is created with type ADD_FG and the FG is added to the current plan
3. **Given** an event with plan_state = IN_PRODUCTION, **When** I submit a MODIFY_BATCH amendment with recipe_id, old_batches, new_batches, and reason, **Then** an amendment record is created with type MODIFY_BATCH and the batch decision is updated
4. **Given** an event with plan_state != IN_PRODUCTION (DRAFT, LOCKED, or COMPLETED), **When** I attempt to create any amendment, **Then** the system rejects the amendment with a clear error message
5. **Given** any amendment type, **When** I attempt to submit without a reason, **Then** the system rejects the amendment requiring a reason

---

### User Story 3 - View Amendment History (Priority: P3)

As a bakery planner, I want to see the complete amendment history for an event, so that I can understand what changes were made and why.

**Why this priority**: Visibility into the audit trail. Depends on P1/P2 being implemented first.

**Independent Test**: Can be tested by creating several amendments on an event, then viewing the amendment history panel to verify all amendments are displayed with their types, data, reasons, and timestamps.

**Acceptance Scenarios**:

1. **Given** an event with multiple amendments, **When** I view the amendment history, **Then** I see all amendments in chronological order with type, summary, reason, and timestamp
2. **Given** an event with no amendments, **When** I view the amendment history, **Then** I see an empty state message indicating no amendments have been made
3. **Given** any amendment in history, **When** I view its details, **Then** I can see the full amendment data (what was changed, from what, to what)

---

### User Story 4 - Compare Original vs Current Plan (Priority: P4)

As a bakery planner, I want to compare my original plan (from the snapshot) with the current plan (after amendments), so that I can see all differences at a glance.

**Why this priority**: User experience enhancement for understanding cumulative impact of amendments.

**Independent Test**: Can be tested by creating amendments, then viewing the comparison view to verify original values (from snapshot) are shown alongside current values with differences highlighted.

**Acceptance Scenarios**:

1. **Given** an event with a snapshot and amendments, **When** I open the plan comparison view, **Then** I see the original plan state and current plan state side by side
2. **Given** a DROP_FG amendment was made, **When** I view the comparison, **Then** the dropped FG shows in original but not in current
3. **Given** an ADD_FG amendment was made, **When** I view the comparison, **Then** the added FG shows in current but not in original
4. **Given** a MODIFY_BATCH amendment was made, **When** I view the comparison, **Then** the batch count shows original value vs current value with difference highlighted

---

### Edge Cases

- What happens if production is started on an event with no recipes/FGs/batch decisions? (Allow - empty snapshot is valid; user may add via amendments)
- What happens if user tries to drop an FG that was already dropped? (Reject - FG not in current plan)
- What happens if user tries to add an FG that's already in the plan? (Reject - FG already exists; use MODIFY if changing quantity)
- How are amendments stored? (Append-only JSON in plan_amendments table; never deleted or modified)
- What happens if snapshot retrieval fails? (Graceful degradation - show current plan only with warning)
- Can amendments be undone? (No - out of scope; append-only log)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically create a plan snapshot when `start_production()` is called, before the state changes to IN_PRODUCTION
- **FR-002**: System MUST store snapshot data as JSON including: EventRecipe records, EventFinishedGood records with quantities, BatchDecision records
- **FR-003**: System MUST support DROP_FG amendment type with data: {fg_id, original_quantity, reason}
- **FR-004**: System MUST support ADD_FG amendment type with data: {fg_id, new_quantity, reason}
- **FR-005**: System MUST support MODIFY_BATCH amendment type with data: {recipe_id, old_batches, new_batches, reason}
- **FR-006**: System MUST require a non-empty reason for all amendments
- **FR-007**: System MUST reject amendments when plan_state is not IN_PRODUCTION
- **FR-008**: System MUST store amendments in append-only fashion (never delete or modify existing amendments)
- **FR-009**: System MUST display amendment history for an event showing all amendments in chronological order
- **FR-010**: System MUST provide UI controls to create each amendment type with reason entry
- **FR-011**: System MUST provide a comparison view showing original plan (from snapshot) vs current plan (with amendments applied)
- **FR-012**: System MUST highlight differences in the comparison view (added, removed, modified items)

### Key Entities

- **PlanSnapshot**: Complete state of a plan at a point in time (production start). Contains JSON data with recipes, FGs, quantities, and batch decisions. One snapshot per event (created on first production start).
- **PlanAmendment**: Record of a single change to a plan during production. Contains amendment_type enum (DROP_FG, ADD_FG, MODIFY_BATCH), amendment_data JSON, reason text, and timestamp. Multiple amendments per event, append-only.
- **AmendmentType**: Enumeration of allowed amendment types (DROP_FG, ADD_FG, MODIFY_BATCH)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Plan snapshots are created 100% of the time when transitioning from LOCKED to IN_PRODUCTION
- **SC-002**: All three amendment types (DROP_FG, ADD_FG, MODIFY_BATCH) can be recorded with 100% reliability
- **SC-003**: Amendments without reasons are rejected 100% of the time
- **SC-004**: Amendment history displays all amendments accurately with no missing entries
- **SC-005**: Comparison view correctly shows original vs current state with differences visible within 2 seconds of loading
- **SC-006**: Amendments are only allowed in IN_PRODUCTION state; other states reject with clear error

## Assumptions

- The `plan_snapshots` and `plan_amendments` tables already exist in the schema from F068 planning data model
- The `PlanState` enum and state transition logic from F077 are already implemented
- A plan can only have one snapshot (created at first production start)
- Amendments modify the live plan data (EventFinishedGood, BatchDecision); the snapshot preserves the original
- Users understand that amendments cannot be undone (this is intentional for audit integrity)

## Out of Scope

- Amendment undo/revert functionality (future feature)
- Amendment approval workflow (future feature)
- Production-aware calculations and progress tracking (F079)
- Multiple snapshots per event (version history)
- Amendment notifications or alerts
