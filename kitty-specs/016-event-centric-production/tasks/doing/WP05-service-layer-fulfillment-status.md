---
work_package_id: "WP05"
subtasks:
  - "T025"
  - "T026"
  - "T027"
title: "Service Layer - Fulfillment Status"
phase: "Phase 3 - Progress & Fulfillment"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Service Layer - Fulfillment Status

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Implement fulfillment status update and query methods with sequential workflow enforcement.

**Success Criteria**:
- `update_fulfillment_status()` enforces sequential transitions
- Valid transitions: pending->ready, ready->delivered
- Invalid transitions raise ValueError with clear message
- `get_packages_by_status()` filters correctly or returns all
- Unit tests cover valid and invalid transitions

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - FR-018, FR-019, FR-020, User Story 7
- `kitty-specs/016-event-centric-production/contracts/event-service-contracts.md`

**Sequential Workflow**:
```
pending -> ready -> delivered (terminal)
```

**Valid Transitions**:
| Current | Allowed Next |
|---------|-------------|
| pending | ready |
| ready | delivered |
| delivered | (none) |

**Dependencies**: WP01 (fulfillment_status column exists)

---

## Subtasks & Detailed Guidance

### Subtask T025 - Implement EventService.update_fulfillment_status()

**Purpose**: Update package status with workflow enforcement.

**Steps**:
1. Open `src/services/event_service.py`
2. Add method:
   ```python
   def update_fulfillment_status(
       self,
       event_recipient_package_id: int,
       new_status: FulfillmentStatus,
       session: Optional[Session] = None
   ) -> EventRecipientPackage:
       """
       Update package fulfillment status with sequential workflow enforcement.

       Valid transitions:
         pending -> ready
         ready -> delivered

       Raises ValueError if transition is invalid.
       """
       # Define valid transitions
       valid_transitions = {
           FulfillmentStatus.PENDING: [FulfillmentStatus.READY],
           FulfillmentStatus.READY: [FulfillmentStatus.DELIVERED],
           FulfillmentStatus.DELIVERED: []
       }

       with self._get_session(session) as sess:
           package = sess.query(EventRecipientPackage).filter_by(
               id=event_recipient_package_id
           ).first()

           if not package:
               raise ValueError(f"Package with id {event_recipient_package_id} not found")

           current_status = FulfillmentStatus(package.fulfillment_status)

           if new_status not in valid_transitions[current_status]:
               allowed = [s.value for s in valid_transitions[current_status]]
               raise ValueError(
                   f"Invalid transition: {current_status.value} -> {new_status.value}. "
                   f"Allowed: {allowed}"
               )

           package.fulfillment_status = new_status.value
           sess.commit()
           return package
   ```
3. Add import: `from src.models import FulfillmentStatus, EventRecipientPackage`

**Files**: `src/services/event_service.py`
**Parallel?**: No (foundational)
**Notes**: Error message should be clear for UI display.

---

### Subtask T026 - Implement EventService.get_packages_by_status()

**Purpose**: Retrieve packages filtered by fulfillment status.

**Steps**:
1. Add method:
   ```python
   def get_packages_by_status(
       self,
       event_id: int,
       status: Optional[FulfillmentStatus] = None,
       session: Optional[Session] = None
   ) -> List[EventRecipientPackage]:
       """Get packages filtered by fulfillment status (or all if None)."""
       with self._get_session(session) as sess:
           query = sess.query(EventRecipientPackage).options(
               joinedload(EventRecipientPackage.recipient),
               joinedload(EventRecipientPackage.package)
           ).filter_by(event_id=event_id)

           if status is not None:
               query = query.filter(
                   EventRecipientPackage.fulfillment_status == status.value
               )

           return query.all()
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: No
**Notes**: Eager load recipient and package for UI display.

---

### Subtask T027 - Write unit tests for fulfillment status

**Purpose**: Verify workflow enforcement and filtering.

**Steps**:
1. Create `src/tests/services/test_event_service_fulfillment.py`
2. Add test cases:
   ```python
   class TestFulfillmentStatus:
       def test_transition_pending_to_ready(self, db_session, package):
           """Valid: pending -> ready."""
           # Package starts as pending
           # Update to ready
           # Assert: status is now ready

       def test_transition_ready_to_delivered(self, db_session, package):
           """Valid: ready -> delivered."""
           # Set package to ready first
           # Update to delivered
           # Assert: status is now delivered

       def test_transition_pending_to_delivered_invalid(self, db_session, package):
           """Invalid: cannot skip pending -> delivered."""
           # Package is pending
           # Attempt update to delivered
           # Assert: ValueError raised with clear message

       def test_transition_delivered_to_any_invalid(self, db_session, package):
           """Invalid: delivered is terminal state."""
           # Set package to delivered
           # Attempt any transition
           # Assert: ValueError raised

       def test_transition_ready_to_pending_invalid(self, db_session, package):
           """Invalid: cannot go backwards."""
           # Set package to ready
           # Attempt update to pending
           # Assert: ValueError raised

       def test_package_not_found(self, db_session):
           """ValueError for non-existent package."""
           # Assert: ValueError with "not found" message

   class TestGetPackagesByStatus:
       def test_filter_by_status(self, db_session, event):
           """Returns only packages with matching status."""
           # Create packages with different statuses
           # Filter by READY
           # Assert: only ready packages returned

       def test_all_packages_when_no_filter(self, db_session, event):
           """Returns all packages when status=None."""
           # Create packages with different statuses
           # Get all
           # Assert: all packages returned

       def test_empty_result(self, db_session, event):
           """Empty list when no matching packages."""
   ```

**Files**: `src/tests/services/test_event_service_fulfillment.py`
**Parallel?**: No
**Notes**: Test both valid and invalid transitions thoroughly.

---

## Test Strategy

**Run Tests**:
```bash
pytest src/tests/services/test_event_service_fulfillment.py -v
```

**Coverage Requirements**:
- All valid transitions: pending->ready, ready->delivered
- All invalid transitions: skip, reverse, from terminal
- Package not found error
- Filter by each status
- No filter returns all

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Inconsistent state | Service layer is single source of truth for transitions |
| UI bypass | Validate in service, UI just presents options |
| Error message clarity | Include current, attempted, and allowed in message |

---

## Definition of Done Checklist

- [ ] `update_fulfillment_status()` implemented
- [ ] Valid transitions work correctly
- [ ] Invalid transitions raise ValueError
- [ ] Error message is clear and helpful
- [ ] `get_packages_by_status()` implemented
- [ ] Filtering works correctly
- [ ] Unit tests for all scenarios
- [ ] All tests pass
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. All transition combinations tested
2. Error messages include enough context
3. Eager loading prevents N+1 in get_packages_by_status
4. Status comparison uses .value correctly
5. Package not found handled gracefully

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T04:08:37Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-11T04:15:00Z – claude – shell_pid=85015 – lane=doing – Completed all subtasks:
  - T025: Implemented update_fulfillment_status() with transition validation
  - T026: Implemented get_packages_by_status() with eager loading
  - T027: Created test_event_service_fulfillment.py with 12 tests:
    - TestFulfillmentStatusTransitions: 6 tests (pending->ready, ready->delivered, skip, terminal, backwards, not found)
    - TestGetPackagesByStatus: 6 tests (filter pending, ready, delivered, all, empty, eager load)
  - All 12 tests pass
