---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Remaining Models & Service Layer Extension"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-26T19:16:03Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Remaining Models & Service Layer Extension

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

**Depends on WP01** - Branch from WP01's completed work:
```bash
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

**Goal**: Complete model layer (PlanAmendment, PlanningSnapshot updates, __init__.py exports) and extend EventService with planning CRUD methods.

**Success Criteria**:
- [ ] PlanAmendment model created with AmendmentType enum
- [ ] PlanningSnapshot updated with snapshot_type and snapshot_data fields
- [ ] All new models exported from `src/models/__init__.py`
- [ ] EventService extended with planning CRUD methods
- [ ] Validation for expected_attendees (positive or None)
- [ ] Unit tests for new service methods (>70% coverage)
- [ ] All existing tests still pass

---

## Context & Constraints

**Reference Documents**:
- Data model: `kitty-specs/068-event-management-planning-data-model/data-model.md`
- Research patterns: `kitty-specs/068-event-management-planning-data-model/research.md`
- Constitution: `.kittify/memory/constitution.md` (Principle IV: TDD, Principle V: Layered Architecture)

**Key Patterns to Follow**:
- EventService is ~1900 lines; add methods in clearly marked section
- Session management: session passed to methods, not created inside
- Follow existing CRUD patterns (create_event, get_event, etc.)

**Constraints**:
- plan_state transitions are NOT implemented in F068 (that's F077)
- F068 only stores the field; state is display-only
- All validation must be in service layer, not UI

---

## Subtasks & Detailed Guidance

### Subtask T008 – Create PlanAmendment Model with AmendmentType Enum [P]

**Purpose**: Track amendments to locked plans during production (Phase 3 preparation).

**Steps**:
1. Create new file `src/models/plan_amendment.py`
2. Implement the model with AmendmentType enum:

```python
"""
PlanAmendment model for tracking plan amendments.

Records changes made to locked plans during production.
Feature 068: Event Management & Planning Data Model (Phase 3 preparation)
"""

from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class AmendmentType(str, Enum):
    """
    Types of plan amendments.

    Used to categorize changes made to locked plans.
    """
    DROP_FG = "drop_fg"           # Remove a finished good from plan
    ADD_FG = "add_fg"             # Add a finished good to plan
    MODIFY_BATCH = "modify_batch" # Change batch count for a recipe


class PlanAmendment(BaseModel):
    """
    Tracks amendments to locked plans during production.

    When a plan is locked and production starts, users may need to
    make amendments (drop items, add items, change batch counts).
    This table records those amendments with reasons.

    Note: This is Phase 3 preparation. F068 defines the table structure;
    actual amendment logic is implemented in F078-F079.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        amendment_type: Type of amendment (DROP_FG, ADD_FG, MODIFY_BATCH)
        amendment_data: JSON with type-specific details
        reason: Optional user-provided reason
        created_at: When amendment was made
    """

    __tablename__ = "plan_amendments"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amendment details
    amendment_type = Column(SQLEnum(AmendmentType), nullable=False)
    amendment_data = Column(JSON, nullable=False)
    reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    event = relationship("Event", back_populates="plan_amendments")

    # Indexes
    __table_args__ = (
        Index("idx_plan_amendment_event", "event_id"),
        Index("idx_plan_amendment_type", "amendment_type"),
        Index("idx_plan_amendment_created", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"PlanAmendment(id={self.id}, event_id={self.event_id}, "
            f"type={self.amendment_type.value})"
        )
```

**Files**: `src/models/plan_amendment.py` (new file, ~85 lines)
**Parallel?**: Yes - independent file
**Notes**:
- Uses `sqlalchemy.dialects.sqlite.JSON` for JSON column
- amendment_data schema varies by type (see data-model.md)

---

### Subtask T009 – Update PlanningSnapshot with New Fields [P]

**Purpose**: Add snapshot_type and snapshot_data fields for Phase 3 plan comparison.

**Steps**:
1. Open `src/models/planning_snapshot.py`
2. Add SnapshotType enum BEFORE the class definition:

```python
from enum import Enum

class SnapshotType(str, Enum):
    """
    Type of planning snapshot.

    Used to distinguish between original locked plan and current state.
    """
    ORIGINAL = "original"  # Snapshot when plan was locked
    CURRENT = "current"    # Latest snapshot reflecting amendments
```

3. Add imports for SQLEnum and JSON:
```python
from sqlalchemy import ... Enum as SQLEnum ...
from sqlalchemy.dialects.sqlite import JSON
```

4. Add new fields AFTER existing columns (after `notes`):
```python
# Phase 3 fields (F068 preparation)
snapshot_type = Column(SQLEnum(SnapshotType), nullable=True, index=True)
snapshot_data = Column(JSON, nullable=True)
```

5. Add index to `__table_args__`:
```python
Index("idx_planning_snapshot_type", "snapshot_type"),
```

**Files**: `src/models/planning_snapshot.py` (modify)
**Parallel?**: Yes - independent file modification
**Notes**:
- Fields are nullable for backward compatibility with existing records
- Phase 3 (F078-F079) will populate these fields

---

### Subtask T010 – Update models/__init__.py with New Exports

**Purpose**: Export all new models and enums for use throughout the application.

**Steps**:
1. Open `src/models/__init__.py`
2. Add imports for new models:

```python
# Planning models (F068)
from .event_recipe import EventRecipe
from .event_finished_good import EventFinishedGood
from .batch_decision import BatchDecision
from .plan_amendment import PlanAmendment, AmendmentType
from .event import PlanState  # New enum added to event.py
from .planning_snapshot import SnapshotType  # New enum added
```

3. Add to `__all__` list (if using explicit exports):
```python
__all__ = [
    # ... existing exports ...
    "EventRecipe",
    "EventFinishedGood",
    "BatchDecision",
    "PlanAmendment",
    "AmendmentType",
    "PlanState",
    "SnapshotType",
]
```

**Files**: `src/models/__init__.py` (modify)
**Parallel?**: No - depends on all models being created
**Validation**: `from src.models import EventRecipe, PlanState, AmendmentType` works

---

### Subtask T011 – Add Planning CRUD Methods to EventService

**Purpose**: Extend EventService with methods for planning workflow.

**Steps**:
1. Open `src/services/event_service.py`
2. Find a good location (end of file, or create new section with comment marker)
3. Add section marker:

```python
# ============================================================================
# F068: Planning Module Methods
# ============================================================================
```

4. Add the following methods:

```python
def get_events_for_planning(
    self,
    session: Session,
    include_completed: bool = False,
) -> List[Event]:
    """
    Get events for the Planning workspace.

    Args:
        session: Database session
        include_completed: If True, include COMPLETED events

    Returns:
        List of Event objects sorted by event_date (most recent first)
    """
    query = session.query(Event)

    if not include_completed:
        query = query.filter(Event.plan_state != PlanState.COMPLETED)

    return query.order_by(Event.event_date.desc()).all()


def create_planning_event(
    self,
    session: Session,
    name: str,
    event_date: date,
    expected_attendees: Optional[int] = None,
    notes: Optional[str] = None,
) -> Event:
    """
    Create a new event for planning.

    Args:
        session: Database session
        name: Event name (required)
        event_date: Event date (required)
        expected_attendees: Optional attendee count (must be positive)
        notes: Optional notes

    Returns:
        Created Event object

    Raises:
        ValidationError: If validation fails
    """
    # Validate expected_attendees
    if expected_attendees is not None and expected_attendees <= 0:
        raise ValidationError("Expected attendees must be a positive integer")

    # Create event with planning defaults
    event = Event(
        name=name,
        event_date=event_date,
        year=event_date.year,
        expected_attendees=expected_attendees,
        plan_state=PlanState.DRAFT,
        notes=notes,
    )

    session.add(event)
    session.flush()

    return event


def update_planning_event(
    self,
    session: Session,
    event_id: int,
    name: Optional[str] = None,
    event_date: Optional[date] = None,
    expected_attendees: Optional[int] = None,
    notes: Optional[str] = None,
) -> Event:
    """
    Update an existing event's planning metadata.

    Args:
        session: Database session
        event_id: ID of event to update
        name: New name (if provided)
        event_date: New date (if provided)
        expected_attendees: New attendee count (if provided, must be positive or None to clear)
        notes: New notes (if provided)

    Returns:
        Updated Event object

    Raises:
        ValidationError: If event not found or validation fails
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError(f"Event with ID {event_id} not found")

    # Validate and update expected_attendees
    # Special handling: pass 0 to clear, positive to set
    if expected_attendees is not None:
        if expected_attendees == 0:
            event.expected_attendees = None
        elif expected_attendees < 0:
            raise ValidationError("Expected attendees must be a positive integer")
        else:
            event.expected_attendees = expected_attendees

    # Update other fields if provided
    if name is not None:
        event.name = name
    if event_date is not None:
        event.event_date = event_date
        event.year = event_date.year
    if notes is not None:
        event.notes = notes

    session.flush()
    return event


def delete_planning_event(
    self,
    session: Session,
    event_id: int,
) -> bool:
    """
    Delete an event and all its planning associations.

    Cascade delete removes: event_recipes, event_finished_goods,
    batch_decisions, plan_amendments.

    Args:
        session: Database session
        event_id: ID of event to delete

    Returns:
        True if deleted, False if not found
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        return False

    session.delete(event)
    session.flush()
    return True
```

5. Add necessary imports at top of file:
```python
from src.models import PlanState  # If not already imported
```

**Files**: `src/services/event_service.py` (modify, add ~100 lines)
**Parallel?**: No - depends on models
**Notes**:
- Do NOT add state transition methods (that's F077)
- plan_state is set to DRAFT on create; cannot be changed in F068

---

### Subtask T012 – Add Validation for expected_attendees

**Purpose**: Ensure expected_attendees validation is consistent across service methods.

**Steps**:
1. Review create_planning_event and update_planning_event methods (T011)
2. Ensure validation rules are consistent:
   - NULL is valid (optional field)
   - Positive integers are valid
   - Zero or negative values raise ValidationError
3. Consider adding a helper method:

```python
def _validate_expected_attendees(self, value: Optional[int]) -> None:
    """
    Validate expected_attendees value.

    Args:
        value: Attendee count to validate

    Raises:
        ValidationError: If value is not positive (when provided)
    """
    if value is not None and value <= 0:
        raise ValidationError("Expected attendees must be a positive integer")
```

**Files**: `src/services/event_service.py` (modify)
**Parallel?**: No - part of T011 work
**Notes**: This subtask is about ensuring validation is complete and consistent

---

### Subtask T013 – Ensure plan_state is Display-Only in F068

**Purpose**: Verify plan_state cannot be modified directly through F068 service methods.

**Steps**:
1. Review update_planning_event method
2. Ensure plan_state is NOT accepted as a parameter
3. Add comment documenting this constraint:

```python
def update_planning_event(
    self,
    session: Session,
    event_id: int,
    name: Optional[str] = None,
    event_date: Optional[date] = None,
    expected_attendees: Optional[int] = None,
    notes: Optional[str] = None,
    # NOTE: plan_state is intentionally NOT a parameter.
    # State transitions are implemented in F077 (Plan State Management).
) -> Event:
```

4. If a user tries to import PlanState and set it directly on the model, that's allowed at the ORM level but the service doesn't facilitate it.

**Files**: `src/services/event_service.py` (verify/document)
**Parallel?**: No - part of T011 work
**Notes**: This is about verification and documentation, not new code

---

### Subtask T014 – Write Unit Tests for Planning Service Methods

**Purpose**: Ensure >70% test coverage for new planning methods per Constitution.

**Steps**:
1. Create new file `src/tests/test_event_planning.py`
2. Write tests for each new method:

```python
"""
Unit tests for F068 planning methods in EventService.
"""

import pytest
from datetime import date
from sqlalchemy.orm import Session

from src.services.event_service import EventService
from src.services.exceptions import ValidationError
from src.models import Event, PlanState


class TestGetEventsForPlanning:
    """Tests for get_events_for_planning method."""

    def test_returns_events_sorted_by_date(self, session: Session):
        """Events should be sorted by date, most recent first."""
        service = EventService()
        # Create events in random order
        service.create_planning_event(session, "Event A", date(2026, 6, 15))
        service.create_planning_event(session, "Event B", date(2026, 12, 20))
        service.create_planning_event(session, "Event C", date(2026, 3, 10))
        session.commit()

        events = service.get_events_for_planning(session)

        assert len(events) == 3
        assert events[0].name == "Event B"  # Most recent
        assert events[1].name == "Event A"
        assert events[2].name == "Event C"  # Oldest

    def test_excludes_completed_events_by_default(self, session: Session):
        """Completed events should be excluded unless requested."""
        service = EventService()
        event = service.create_planning_event(session, "Test", date(2026, 12, 20))
        event.plan_state = PlanState.COMPLETED
        session.commit()

        events = service.get_events_for_planning(session)
        assert len(events) == 0

        events_with_completed = service.get_events_for_planning(
            session, include_completed=True
        )
        assert len(events_with_completed) == 1


class TestCreatePlanningEvent:
    """Tests for create_planning_event method."""

    def test_creates_event_with_required_fields(self, session: Session):
        """Event created with name, date, and default plan_state."""
        service = EventService()
        event = service.create_planning_event(
            session, "Christmas 2026", date(2026, 12, 20)
        )
        session.commit()

        assert event.id is not None
        assert event.name == "Christmas 2026"
        assert event.event_date == date(2026, 12, 20)
        assert event.year == 2026
        assert event.plan_state == PlanState.DRAFT
        assert event.expected_attendees is None

    def test_creates_event_with_expected_attendees(self, session: Session):
        """Event created with optional attendee count."""
        service = EventService()
        event = service.create_planning_event(
            session, "Party", date(2026, 7, 4), expected_attendees=50
        )
        session.commit()

        assert event.expected_attendees == 50

    def test_rejects_negative_attendees(self, session: Session):
        """Negative attendee count should raise ValidationError."""
        service = EventService()
        with pytest.raises(ValidationError) as exc_info:
            service.create_planning_event(
                session, "Party", date(2026, 7, 4), expected_attendees=-5
            )

        assert "positive integer" in str(exc_info.value)

    def test_rejects_zero_attendees(self, session: Session):
        """Zero attendee count should raise ValidationError."""
        service = EventService()
        with pytest.raises(ValidationError) as exc_info:
            service.create_planning_event(
                session, "Party", date(2026, 7, 4), expected_attendees=0
            )

        assert "positive integer" in str(exc_info.value)


class TestUpdatePlanningEvent:
    """Tests for update_planning_event method."""

    def test_updates_name(self, session: Session):
        """Event name can be updated."""
        service = EventService()
        event = service.create_planning_event(session, "Old Name", date(2026, 12, 20))
        session.commit()

        updated = service.update_planning_event(session, event.id, name="New Name")
        session.commit()

        assert updated.name == "New Name"

    def test_updates_expected_attendees(self, session: Session):
        """Attendee count can be updated."""
        service = EventService()
        event = service.create_planning_event(session, "Party", date(2026, 7, 4))
        session.commit()

        updated = service.update_planning_event(
            session, event.id, expected_attendees=75
        )
        session.commit()

        assert updated.expected_attendees == 75

    def test_clears_attendees_with_zero(self, session: Session):
        """Passing 0 clears expected_attendees to None."""
        service = EventService()
        event = service.create_planning_event(
            session, "Party", date(2026, 7, 4), expected_attendees=50
        )
        session.commit()

        updated = service.update_planning_event(
            session, event.id, expected_attendees=0
        )
        session.commit()

        assert updated.expected_attendees is None

    def test_rejects_not_found(self, session: Session):
        """Non-existent event ID raises ValidationError."""
        service = EventService()
        with pytest.raises(ValidationError) as exc_info:
            service.update_planning_event(session, 99999, name="Test")

        assert "not found" in str(exc_info.value)


class TestDeletePlanningEvent:
    """Tests for delete_planning_event method."""

    def test_deletes_event(self, session: Session):
        """Event is deleted successfully."""
        service = EventService()
        event = service.create_planning_event(session, "Test", date(2026, 12, 20))
        session.commit()
        event_id = event.id

        result = service.delete_planning_event(session, event_id)
        session.commit()

        assert result is True
        assert session.query(Event).filter(Event.id == event_id).first() is None

    def test_returns_false_for_not_found(self, session: Session):
        """Returns False for non-existent event."""
        service = EventService()
        result = service.delete_planning_event(session, 99999)
        assert result is False

    # TODO: Add test for cascade delete once event_recipes etc are populated
```

3. Add pytest fixture for session if not using existing fixture:
```python
@pytest.fixture
def session():
    """Provide a database session for tests."""
    from src.services.database import session_scope
    with session_scope() as s:
        yield s
```

**Files**: `src/tests/test_event_planning.py` (new file, ~180 lines)
**Parallel?**: No - depends on service methods
**Validation**: Run `pytest src/tests/test_event_planning.py -v` - all tests pass

---

## Test Strategy

**Required Coverage**: >70% for new planning methods in EventService

**Test Commands**:
```bash
# Run planning tests
pytest src/tests/test_event_planning.py -v

# Run with coverage
pytest src/tests/test_event_planning.py -v --cov=src/services/event_service

# Run all tests to ensure no regressions
pytest src/tests -v
```

**Key Test Scenarios**:
1. Create event with valid data → Success
2. Create event with invalid attendees → ValidationError
3. Update event fields → Changes persist
4. Update with zero attendees → Clears to None
5. Delete event → Returns True, event removed
6. Delete non-existent → Returns False
7. Get events excludes completed by default
8. Get events sorted by date (most recent first)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| EventService file is large (1900+ lines) | Add methods at end with clear section marker |
| Test fixture compatibility | Use existing project test patterns |
| Import errors | Ensure models/__init__.py updated before running tests |

---

## Definition of Done Checklist

- [ ] PlanAmendment model created with AmendmentType enum
- [ ] PlanningSnapshot has snapshot_type and snapshot_data fields
- [ ] All models exported from __init__.py
- [ ] EventService has get_events_for_planning method
- [ ] EventService has create_planning_event method
- [ ] EventService has update_planning_event method
- [ ] EventService has delete_planning_event method
- [ ] Validation rejects invalid expected_attendees
- [ ] plan_state is NOT settable via update method
- [ ] Unit tests written and passing
- [ ] All existing tests still pass
- [ ] Code coverage >70% for new methods

---

## Review Guidance

**Reviewers should verify**:
1. Service methods follow existing session management pattern
2. Validation is complete and matches spec
3. plan_state cannot be modified (F068 constraint)
4. Test coverage is adequate
5. No business logic in models (all in service)
6. Error messages are clear and helpful

---

## Activity Log

- 2026-01-26T19:16:03Z – system – lane=planned – Prompt created.
