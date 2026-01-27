# Feature Specification: Plan State Management

**Feature Branch**: `077-plan-state-management`
**Created**: 2026-01-27
**Status**: Draft
**Input**: F077 functional spec - Plan lifecycle state machine for production workflow

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lock Plan Before Production (Priority: P1)

As a bakery planner, I want to lock my event plan once finalized so that recipe and finished goods selections cannot be accidentally changed while I'm preparing for production.

**Why this priority**: Locking is the foundational state transition that enables production workflow control. Without locking, users cannot progress plans through the lifecycle.

**Independent Test**: Can be tested by selecting an event in DRAFT state, clicking "Lock Plan", and verifying the state changes to LOCKED with recipes/FGs becoming read-only.

**Acceptance Scenarios**:

1. **Given** an event with plan_state = DRAFT, **When** user clicks "Lock Plan", **Then** the plan_state becomes LOCKED and a success message is shown
2. **Given** an event with plan_state = LOCKED, **When** user attempts to add/remove a recipe, **Then** the system prevents the change and shows an appropriate error message
3. **Given** an event with plan_state = LOCKED, **When** user attempts to modify FG quantities, **Then** the system prevents the change with an error message
4. **Given** an event with plan_state = LOCKED, **When** user modifies batch decisions, **Then** the change is allowed (batch decisions remain editable in LOCKED state)

---

### User Story 2 - Start and Complete Production (Priority: P2)

As a bakery planner, I want to track when production starts and completes so that I can see the lifecycle status of my event plans.

**Why this priority**: Extends the basic locking capability with full lifecycle tracking. Depends on P1 locking being implemented first.

**Independent Test**: Can be tested by locking a plan, clicking "Start Production", verifying IN_PRODUCTION state, then clicking "Complete" and verifying COMPLETED state.

**Acceptance Scenarios**:

1. **Given** an event with plan_state = LOCKED, **When** user clicks "Start Production", **Then** the plan_state becomes IN_PRODUCTION
2. **Given** an event with plan_state = IN_PRODUCTION, **When** user clicks "Complete Production", **Then** the plan_state becomes COMPLETED
3. **Given** an event with plan_state = IN_PRODUCTION, **When** user attempts to modify batch decisions, **Then** the system prevents the change (only amendments allowed via F078)
4. **Given** an event with plan_state = COMPLETED, **When** user attempts any modification, **Then** the system prevents all changes (read-only state)

---

### User Story 3 - View Plan State and Available Actions (Priority: P3)

As a bakery planner, I want to see the current plan state prominently displayed with contextual action buttons so that I always know what state my plan is in and what actions are available.

**Why this priority**: User experience enhancement that makes the state machine discoverable. Core functionality (P1/P2) must work first.

**Independent Test**: Can be tested by selecting events in different states and verifying the correct state badge and action buttons appear.

**Acceptance Scenarios**:

1. **Given** an event in any state, **When** user selects it in the planning tab, **Then** the current state is displayed prominently (e.g., "DRAFT", "LOCKED", etc.)
2. **Given** an event with plan_state = DRAFT, **When** user views the event, **Then** a "Lock Plan" button is enabled
3. **Given** an event with plan_state = LOCKED, **When** user views the event, **Then** "Lock Plan" is disabled/hidden and "Start Production" is enabled
4. **Given** an event with plan_state = IN_PRODUCTION, **When** user views the event, **Then** "Complete Production" is enabled and other transition buttons are disabled
5. **Given** an event with plan_state = COMPLETED, **When** user views the event, **Then** all transition buttons are disabled/hidden

---

### Edge Cases

- What happens when a user tries to lock a plan with no recipes selected? (Allow - empty plans can be locked)
- What happens when a user tries to lock a plan with no FGs selected? (Allow - planning may involve recipes only)
- What happens when a user tries to lock a plan with no batch decisions? (Allow - batch decisions can be made while locked)
- How does the system handle invalid state transitions (e.g., DRAFT → COMPLETED)? (Reject with clear error message)
- What happens if a LOCKED plan needs changes? (User must use amendments via F078, which is out of scope for this feature)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `lock_plan(event_id)` service method that transitions plan_state from DRAFT to LOCKED
- **FR-002**: System MUST provide a `start_production(event_id)` service method that transitions plan_state from LOCKED to IN_PRODUCTION
- **FR-003**: System MUST provide a `complete_production(event_id)` service method that transitions plan_state from IN_PRODUCTION to COMPLETED
- **FR-004**: System MUST reject invalid state transitions with a clear error message (e.g., DRAFT → COMPLETED is invalid)
- **FR-005**: System MUST prevent recipe modifications (add/remove EventRecipe) when plan_state is not DRAFT
- **FR-006**: System MUST prevent finished goods modifications (add/remove/change quantity of EventFinishedGood) when plan_state is not DRAFT
- **FR-007**: System MUST allow batch decision modifications when plan_state is DRAFT or LOCKED
- **FR-008**: System MUST prevent all modifications when plan_state is COMPLETED
- **FR-009**: System MUST display the current plan_state prominently in the Planning tab when an event is selected
- **FR-010**: System MUST display contextual action buttons for valid state transitions based on current state

### Key Entities

- **Event**: Extended with plan_state field (already exists from F068). States: DRAFT, LOCKED, IN_PRODUCTION, COMPLETED
- **PlanState**: Enumeration defining valid plan states (already exists from F068)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can transition a plan through all four states (DRAFT → LOCKED → IN_PRODUCTION → COMPLETED) with 100% reliability
- **SC-002**: Invalid state transitions are blocked with user-friendly error messages in 100% of cases
- **SC-003**: Modification rules are enforced correctly: recipe/FG changes blocked when not in DRAFT, batch decisions allowed in DRAFT/LOCKED
- **SC-004**: Current plan state is visible within 1 second of selecting an event in the Planning tab
- **SC-005**: State transition controls are contextually correct (only valid actions enabled) for all 4 states

## Assumptions

- The `plan_state` field and `PlanState` enum already exist in the Event model from F068
- Amendments (modifying locked/in-production plans via an audit trail) are handled by F078 and out of scope
- Production tracking (actual vs planned quantities) is handled by F079 and out of scope
- A plan can be locked even if it has no recipes, FGs, or batch decisions (flexibility for different planning workflows)

## Out of Scope

- Amendments to locked plans (F078)
- Plan snapshots for comparison (F078)
- Production-aware calculations and progress tracking (F079)
- Undo/revert state transitions (plans progress forward only in this feature)
