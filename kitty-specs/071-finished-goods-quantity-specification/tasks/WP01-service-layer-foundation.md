---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Service Layer Foundation"
phase: "Phase 1 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "75646"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-27T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Service Layer Foundation

## Implementation Command

```bash
spec-kitty implement WP01
```

No `--base` flag needed (this is the first work package).

---

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – This section is empty initially.

---

## Objectives & Success Criteria

Implement three quantity-aware CRUD methods in `event_service.py` with comprehensive unit tests.

**Success Criteria:**
- [ ] `get_event_fg_quantities()` returns list of (FinishedGood, quantity) tuples
- [ ] `set_event_fg_quantities()` replaces all FG quantities for an event
- [ ] `remove_event_fg()` deletes single FG from event
- [ ] All methods follow session parameter pattern per CLAUDE.md
- [ ] Unit tests cover happy path, edge cases, error conditions
- [ ] Tests pass: `./run-tests.sh src/tests/services/test_event_service_fg_quantities.py -v`

## Context & Constraints

### Referenced Documents
- **Constitution**: `.kittify/memory/constitution.md` (Principle IV: Test-Driven Development)
- **Plan**: `kitty-specs/071-finished-goods-quantity-specification/plan.md`
- **Data Model**: `kitty-specs/071-finished-goods-quantity-specification/data-model.md`
- **Research**: `kitty-specs/071-finished-goods-quantity-specification/research.md`

### Session Management Pattern (CRITICAL)

From CLAUDE.md - all service functions MUST follow this pattern:

```python
def my_function(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> ReturnType:
    """Accept optional session parameter."""
    if session is not None:
        return _my_function_impl(event_id, session)
    with session_scope() as session:
        return _my_function_impl(event_id, session)

def _my_function_impl(event_id: int, session: Session) -> ReturnType:
    """Actual implementation - always receives session."""
    # ... implementation here
```

**Why**: Nested `session_scope()` calls cause SQLAlchemy objects to become detached, resulting in silent data loss.

### Existing Patterns to Follow

**Reference**: `src/services/event_service.py` lines 3099-3177

```python
# Existing method to use as pattern:
def get_event_finished_good_ids(session: Session, event_id: int) -> List[int]:
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError(["Event not found"])
    result = session.query(EventFinishedGood.finished_good_id)\
        .filter(EventFinishedGood.event_id == event_id).all()
    return [r[0] for r in result]
```

### Database Schema

```python
# src/models/event_finished_good.py
class EventFinishedGood(BaseModel):
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    finished_good_id = Column(Integer, ForeignKey("finished_goods.id", ondelete="RESTRICT"))
    quantity = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "finished_good_id"),
        CheckConstraint("quantity > 0", name="ck_event_fg_quantity_positive"),
    )
```

---

## Subtasks & Detailed Guidance

### Subtask T001 – Implement get_event_fg_quantities()

**Purpose**: Retrieve all finished goods with their quantities for a given event.

**File**: `src/services/event_service.py`

**Steps**:
1. Add function signature accepting `session` and `event_id` parameters
2. Validate event exists (raise ValidationError if not found)
3. Query EventFinishedGood joined with FinishedGood
4. Return list of (FinishedGood object, quantity) tuples

**Implementation**:
```python
def get_event_fg_quantities(
    session: Session,
    event_id: int,
) -> List[Tuple[FinishedGood, int]]:
    """
    Get all finished goods with quantities for an event.

    Args:
        session: Database session
        event_id: Target event ID

    Returns:
        List of (FinishedGood, quantity) tuples

    Raises:
        ValidationError: If event not found
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError(["Event not found"])

    results = (
        session.query(FinishedGood, EventFinishedGood.quantity)
        .join(EventFinishedGood, FinishedGood.id == EventFinishedGood.finished_good_id)
        .filter(EventFinishedGood.event_id == event_id)
        .all()
    )
    return [(fg, qty) for fg, qty in results]
```

**Required Imports** (add if not present):
```python
from src.models.finished_good import FinishedGood
from src.models.event_finished_good import EventFinishedGood
from typing import List, Tuple
```

**Validation**:
- Returns empty list for event with no FGs
- Returns correct (FG, quantity) tuples for event with FGs
- Raises ValidationError for non-existent event

---

### Subtask T002 – Implement set_event_fg_quantities()

**Purpose**: Replace all FG quantities for an event (delete existing, insert new).

**File**: `src/services/event_service.py`

**Steps**:
1. Add function signature accepting `session`, `event_id`, and `fg_quantities` parameters
2. Validate event exists
3. Get available FG IDs for this event (filter invalid IDs)
4. Delete all existing EventFinishedGood records for event
5. Insert new records with quantities
6. Return count of records created

**Implementation**:
```python
def set_event_fg_quantities(
    session: Session,
    event_id: int,
    fg_quantities: List[Tuple[int, int]],  # [(fg_id, quantity), ...]
) -> int:
    """
    Replace all FG quantities for an event.

    Args:
        session: Database session
        event_id: Target event ID
        fg_quantities: List of (finished_good_id, quantity) tuples

    Returns:
        Count of records created

    Raises:
        ValidationError: If event not found

    Notes:
        - Only FGs available to the event are saved (invalid IDs filtered)
        - Uses replace pattern: DELETE existing, INSERT new
        - Empty list clears all FG associations
        - Quantity must be > 0 (DB constraint enforces)
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError(["Event not found"])

    # Get available FG IDs to filter input
    available_fgs = get_available_finished_goods(event_id, session)
    available_ids = {fg.id for fg in available_fgs}

    # Filter to only available FGs with valid quantities
    valid_pairs = [
        (fg_id, qty) for fg_id, qty in fg_quantities
        if fg_id in available_ids and qty > 0
    ]

    # Delete existing records
    session.query(EventFinishedGood)\
        .filter(EventFinishedGood.event_id == event_id)\
        .delete(synchronize_session=False)

    # Insert new records
    for fg_id, quantity in valid_pairs:
        session.add(EventFinishedGood(
            event_id=event_id,
            finished_good_id=fg_id,
            quantity=quantity
        ))

    session.flush()
    return len(valid_pairs)
```

**Validation**:
- Returns 0 for empty list (clears all FGs)
- Filters invalid FG IDs (not in available list)
- Filters quantities <= 0
- Correctly replaces existing quantities

---

### Subtask T003 – Implement remove_event_fg()

**Purpose**: Remove a single FG from an event.

**File**: `src/services/event_service.py`

**Steps**:
1. Add function signature accepting `session`, `event_id`, and `fg_id` parameters
2. Find and delete the specific EventFinishedGood record
3. Return True if deleted, False if not found

**Implementation**:
```python
def remove_event_fg(
    session: Session,
    event_id: int,
    fg_id: int,
) -> bool:
    """
    Remove a single FG from an event.

    Args:
        session: Database session
        event_id: Target event ID
        fg_id: Finished good ID to remove

    Returns:
        True if record deleted, False if not found
    """
    result = session.query(EventFinishedGood)\
        .filter(
            EventFinishedGood.event_id == event_id,
            EventFinishedGood.finished_good_id == fg_id
        )\
        .delete(synchronize_session=False)

    session.flush()
    return result > 0
```

**Validation**:
- Returns True when record exists and is deleted
- Returns False when record doesn't exist
- Doesn't affect other event's FGs

---

### Subtask T004 – Write Unit Tests

**Purpose**: Ensure service methods work correctly with comprehensive test coverage.

**File**: `src/tests/services/test_event_service_fg_quantities.py` (NEW FILE)

**Steps**:
1. Create new test file with fixtures
2. Write tests for `get_event_fg_quantities()`
3. Write tests for `set_event_fg_quantities()`
4. Write tests for `remove_event_fg()`

**Test File Structure**:
```python
"""Tests for event_service FG quantity methods."""
import pytest
from sqlalchemy.orm import Session

from src.models.event import Event
from src.models.finished_good import FinishedGood
from src.models.event_finished_good import EventFinishedGood
from src.services import event_service
from src.services.errors import ValidationError
from src.utils.session import session_scope


class TestGetEventFgQuantities:
    """Tests for get_event_fg_quantities()."""

    def test_returns_empty_list_for_event_without_fgs(self, session, event):
        """Event with no FG quantities returns empty list."""
        result = event_service.get_event_fg_quantities(session, event.id)
        assert result == []

    def test_returns_fg_quantity_tuples(self, session, event, finished_good):
        """Returns (FinishedGood, quantity) tuples."""
        # Setup: Add FG to event with quantity
        efg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=finished_good.id,
            quantity=24
        )
        session.add(efg)
        session.flush()

        result = event_service.get_event_fg_quantities(session, event.id)

        assert len(result) == 1
        fg, qty = result[0]
        assert fg.id == finished_good.id
        assert qty == 24

    def test_raises_validation_error_for_missing_event(self, session):
        """Non-existent event raises ValidationError."""
        with pytest.raises(ValidationError):
            event_service.get_event_fg_quantities(session, 99999)


class TestSetEventFgQuantities:
    """Tests for set_event_fg_quantities()."""

    def test_creates_new_records(self, session, event, finished_good):
        """Creates EventFinishedGood records with quantities."""
        # Make FG available (may need recipe association)
        fg_quantities = [(finished_good.id, 12)]

        count = event_service.set_event_fg_quantities(session, event.id, fg_quantities)

        assert count == 1
        efg = session.query(EventFinishedGood).filter_by(
            event_id=event.id,
            finished_good_id=finished_good.id
        ).first()
        assert efg is not None
        assert efg.quantity == 12

    def test_replaces_existing_quantities(self, session, event, finished_good):
        """Existing quantities are replaced, not appended."""
        # Setup: existing record
        efg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=finished_good.id,
            quantity=10
        )
        session.add(efg)
        session.flush()

        # Replace with new quantity
        count = event_service.set_event_fg_quantities(
            session, event.id, [(finished_good.id, 25)]
        )

        assert count == 1
        session.expire_all()
        efg = session.query(EventFinishedGood).filter_by(
            event_id=event.id
        ).first()
        assert efg.quantity == 25

    def test_empty_list_clears_all_fgs(self, session, event, finished_good):
        """Empty list removes all FG associations."""
        # Setup: existing record
        session.add(EventFinishedGood(
            event_id=event.id,
            finished_good_id=finished_good.id,
            quantity=10
        ))
        session.flush()

        count = event_service.set_event_fg_quantities(session, event.id, [])

        assert count == 0
        assert session.query(EventFinishedGood).filter_by(
            event_id=event.id
        ).count() == 0

    def test_filters_invalid_fg_ids(self, session, event):
        """Invalid FG IDs are filtered out."""
        count = event_service.set_event_fg_quantities(
            session, event.id, [(99999, 10)]
        )
        assert count == 0

    def test_filters_zero_quantities(self, session, event, finished_good):
        """Quantities <= 0 are filtered out."""
        count = event_service.set_event_fg_quantities(
            session, event.id, [(finished_good.id, 0)]
        )
        assert count == 0

    def test_raises_validation_error_for_missing_event(self, session):
        """Non-existent event raises ValidationError."""
        with pytest.raises(ValidationError):
            event_service.set_event_fg_quantities(session, 99999, [])


class TestRemoveEventFg:
    """Tests for remove_event_fg()."""

    def test_removes_existing_record(self, session, event, finished_good):
        """Returns True and removes record when it exists."""
        session.add(EventFinishedGood(
            event_id=event.id,
            finished_good_id=finished_good.id,
            quantity=10
        ))
        session.flush()

        result = event_service.remove_event_fg(session, event.id, finished_good.id)

        assert result is True
        assert session.query(EventFinishedGood).filter_by(
            event_id=event.id,
            finished_good_id=finished_good.id
        ).first() is None

    def test_returns_false_for_missing_record(self, session, event):
        """Returns False when record doesn't exist."""
        result = event_service.remove_event_fg(session, event.id, 99999)
        assert result is False
```

**Fixtures** (add to conftest.py or use existing):
- `session`: Database session
- `event`: Test event object
- `finished_good`: Test finished good object (must be available to event)

**Run Tests**:
```bash
./run-tests.sh src/tests/services/test_event_service_fg_quantities.py -v
```

---

## Test Strategy

**Required Tests** (per constitution Principle IV):
- Unit tests for all three service methods
- Cover happy path, edge cases, error conditions
- Test coverage should exceed 70% for new code

**Test Commands**:
```bash
# Run all tests for this work package
./run-tests.sh src/tests/services/test_event_service_fg_quantities.py -v

# With coverage
./run-tests.sh src/tests/services/test_event_service_fg_quantities.py -v --cov=src/services/event_service
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Follow session parameter pattern strictly |
| FK violations on insert | Filter to available FGs before insert |
| Concurrent modifications | Single-user desktop app - not a concern |
| Breaking existing methods | New methods only - existing methods unchanged |

---

## Definition of Done Checklist

- [ ] `get_event_fg_quantities()` implemented and working
- [ ] `set_event_fg_quantities()` implemented with replace pattern
- [ ] `remove_event_fg()` implemented
- [ ] All methods follow session parameter pattern
- [ ] Unit tests written for all methods
- [ ] All tests pass: `./run-tests.sh src/tests/services/test_event_service_fg_quantities.py -v`
- [ ] No regressions in existing tests

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Session parameter pattern correctly implemented?
2. Replace pattern (not append) in set_event_fg_quantities?
3. Invalid FG IDs filtered correctly?
4. ValidationError raised for missing events?
5. Test coverage adequate (happy path + edge cases)?

**Code Review Focus**:
- Check imports are added correctly
- Verify session.flush() calls for consistency
- Ensure no hardcoded values

---

## Activity Log

- 2026-01-27T12:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-27T14:03:37Z – claude-opus – shell_pid=75646 – lane=doing – Started implementation via workflow command
- 2026-01-27T14:08:08Z – claude-opus – shell_pid=75646 – lane=for_review – Service layer complete: 3 methods implemented (get_event_fg_quantities, set_event_fg_quantities, remove_event_fg), 15 unit tests passing
