# Feature Specification: Event Management & Planning Data Model

**Feature Branch**: `068-event-management-planning-data-model`
**Created**: 2026-01-26
**Status**: Draft
**Input**: User description: "See docs/func-spec/F068_event_management_planning_data_model.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Event for Planning (Priority: P1)

As a user planning a baking event, I need to create a new event with basic metadata so I can start building my production plan.

**Why this priority**: Events are the foundation of all planning. Without events, no other planning features can function. This is the entry point for the entire planning workflow.

**Independent Test**: Create a new event from the UI with name "Christmas 2026", date "2026-12-20", and expected attendees "50". Verify it appears in the event list and can be retrieved.

**Acceptance Scenarios**:

1. **Given** I am on the Planning workspace, **When** I click "Create Event" and enter name, date, and attendees, **Then** a new event is created with plan_state="DRAFT" and appears in the event list
2. **Given** I have entered an event name but no date, **When** I click "Save", **Then** I see a validation error requiring event date
3. **Given** I enter expected_attendees as -5, **When** I click "Save", **Then** I see a validation error requiring positive integer or empty

---

### User Story 2 - View and List Events (Priority: P1)

As a user, I need to view all my events in a list so I can select one for editing or to begin planning.

**Why this priority**: Users need to see existing events to work with them. This is fundamental navigation.

**Independent Test**: Create 3 events, navigate to Planning workspace, verify all 3 appear in the event list with name, date, attendees, and plan_state displayed.

**Acceptance Scenarios**:

1. **Given** I have 5 events in the database, **When** I navigate to Planning workspace, **Then** I see a list showing all 5 events with name, date, expected attendees, and plan state
2. **Given** I have events from different years (2025, 2026), **When** I view the event list, **Then** events are sorted by date (most recent first)

---

### User Story 3 - Edit Existing Event (Priority: P2)

As a user, I need to edit an existing event's metadata to correct mistakes or update details.

**Why this priority**: Users will need to modify events after creation, but this is less critical than creating and viewing.

**Independent Test**: Create an event, edit its name and expected attendees, verify changes persist.

**Acceptance Scenarios**:

1. **Given** I have an event "Christmas 2026", **When** I edit it to "Holiday Baking 2026", **Then** the name change persists and displays correctly
2. **Given** I have a DRAFT event, **When** I edit expected_attendees from 50 to 75, **Then** the change saves successfully

---

### User Story 4 - Delete Event (Priority: P2)

As a user, I need to delete events I no longer need, with associated data cleaned up automatically.

**Why this priority**: Data hygiene is important but less urgent than creation and viewing.

**Independent Test**: Create an event with recipe selections (via future features), delete the event, verify cascade deletion removes all associations.

**Acceptance Scenarios**:

1. **Given** I have an event "Test Event", **When** I click delete and confirm, **Then** the event is removed from the list
2. **Given** I have an event with event_recipes and event_finished_goods associations, **When** I delete the event, **Then** all association records are cascade deleted
3. **Given** I click delete on an event, **When** I see the confirmation dialog, **Then** I can cancel without deleting

---

### User Story 5 - Complete Planning Data Model (Priority: P1)

As a developer, the database schema must support all Phase 2 planning features (F069-F079) without requiring schema changes.

**Why this priority**: Defining the complete schema upfront prevents migration churn and ensures foreign key relationships work correctly from the start.

**Independent Test**: Run migration, verify all 6 tables exist with correct columns, foreign keys, and indexes.

**Acceptance Scenarios**:

1. **Given** I run the migration script, **When** I query the database, **Then** all planning tables exist (events updated, event_recipes, event_finished_goods, batch_decisions, plan_snapshots updated, plan_amendments)
2. **Given** event_recipes table exists, **When** I insert a valid record, **Then** foreign keys to events and recipes work correctly
3. **Given** I delete an event with associations, **When** cascade rules execute, **Then** all event_recipes, event_finished_goods, and batch_decisions for that event are deleted

---

### Edge Cases

- What happens when creating an event with a duplicate name? → Allowed (same event name different years is valid)
- What happens when editing plan_state directly? → plan_state is display-only in F068; transitions implemented in F077
- How does system handle event with NULL expected_attendees? → Displays as "-" or "Not specified", no calculation impact
- What happens when deleting event that has production runs linked? → ProductionRun.event_id set to NULL (not cascade delete)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creating events with name (required), date (required), and expected_attendees (optional positive integer)
- **FR-002**: System MUST validate event date is a valid date
- **FR-003**: System MUST validate expected_attendees is a positive integer when provided
- **FR-004**: System MUST support viewing past events as reference during planning
- **FR-005**: System MUST support editing event metadata (name, date, expected_attendees)
- **FR-006**: System MUST support deleting events with cascade to planning associations
- **FR-007**: System MUST default plan_state to 'DRAFT' for new events
- **FR-008**: System MUST define event_recipes table for many-to-many event↔recipe associations
- **FR-009**: System MUST define event_finished_goods table with quantity field
- **FR-010**: System MUST define batch_decisions table for user's batch choices per recipe
- **FR-011**: System MUST define plan_amendments table structure for Phase 3 preparation
- **FR-012**: System MUST update plan_snapshots table with snapshot_type field for ORIGINAL/CURRENT distinction

### Key Entities

- **Event**: Baking event with name, date, expected_attendees, plan_state. Entry point for all planning.
- **event_recipes**: Many-to-many junction linking events to selected recipes. Composite PK (event_id, recipe_id).
- **event_finished_goods**: Event FG selections with quantities. Composite PK (event_id, finished_good_id).
- **batch_decisions**: User's batch choices per recipe for an event. Stores batches count and yield_option_id.
- **plan_snapshots**: Updated with snapshot_type (ORIGINAL/CURRENT) and snapshot_data JSON for Phase 3.
- **plan_amendments**: Amendment tracking for Phase 3 (DROP_FG, ADD_FG, MODIFY_BATCH types).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Migration script executes without errors on existing database
- **SC-002**: All 6 planning tables created/updated with correct schema
- **SC-003**: Event CRUD operations complete in <100ms for typical operations
- **SC-004**: Cascade delete correctly removes all event associations
- **SC-005**: UI event list displays all events with required fields
- **SC-006**: Create/Edit event dialogs validate inputs before saving
- **SC-007**: Service follows established patterns (session management, CRUD signatures)
- **SC-008**: Unit tests cover all service methods with >80% coverage
