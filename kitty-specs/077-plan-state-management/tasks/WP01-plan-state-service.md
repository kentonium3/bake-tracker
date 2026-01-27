---
work_package_id: WP01
title: Plan State Service
lane: "done"
dependencies: []
base_branch: main
base_commit: f0f24b3db80ed1137d9ce8145585210bbd07667b
created_at: '2026-01-27T22:38:39.481022+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
assignee: ''
agent: "claude"
shell_pid: "56673"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-28T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Plan State Service

## Implementation Command

```bash
spec-kitty implement WP01
```

## Objectives & Success Criteria

Create the foundational plan state transition service that enables lifecycle management for event plans.

**Success Criteria**:
- [ ] PlanStateError exception defined in exceptions.py
- [ ] plan_state_service.py created with all transition functions
- [ ] lock_plan() transitions DRAFT → LOCKED
- [ ] start_production() transitions LOCKED → IN_PRODUCTION
- [ ] complete_production() transitions IN_PRODUCTION → COMPLETED
- [ ] Invalid transitions raise PlanStateError with clear message
- [ ] All unit tests pass

## Context & Constraints

**Reference Documents**:
- `kitty-specs/077-plan-state-management/spec.md` - User stories and requirements
- `kitty-specs/077-plan-state-management/plan.md` - Design decisions D1-D4
- `.kittify/memory/constitution.md` - Architecture principles

**Existing Infrastructure**:
- `src/models/event.py` - Contains PlanState enum (DRAFT, LOCKED, IN_PRODUCTION, COMPLETED)
- `src/services/exceptions.py` - Exception patterns to follow
- `src/services/batch_decision_service.py` - Service pattern to follow

**Key Patterns**:
- All public functions accept `session=None` parameter
- If session provided, use it directly
- If session is None, create via `session_scope()`
- Follow existing exception class structure (inherit from ServiceError)

## Subtasks & Detailed Guidance

### Subtask T001 – Add PlanStateError Exception

**Purpose**: Define a specific exception for plan state violations, enabling UI to catch and display user-friendly messages.

**Steps**:
1. Open `src/services/exceptions.py`
2. Add new exception class after the existing service exceptions (around line 245):

```python
class PlanStateError(ServiceError):
    """Raised when an invalid plan state transition is attempted.

    Args:
        event_id: The event ID involved in the failed transition
        current_state: The current PlanState value
        attempted_action: Description of what was attempted

    Example:
        >>> raise PlanStateError(123, PlanState.LOCKED, "modify recipes")
        PlanStateError: Cannot modify recipes: event 123 plan is locked
    """

    def __init__(self, event_id: int, current_state, attempted_action: str):
        self.event_id = event_id
        self.current_state = current_state
        self.attempted_action = attempted_action
        state_name = current_state.value if hasattr(current_state, 'value') else str(current_state)
        super().__init__(
            f"Cannot {attempted_action}: event {event_id} plan is {state_name}"
        )
```

3. Update the module docstring hierarchy comment to include PlanStateError

**Files**: `src/services/exceptions.py`

**Validation**:
- [ ] Exception can be imported: `from src.services.exceptions import PlanStateError`
- [ ] Exception message is formatted correctly
- [ ] Exception stores event_id, current_state, attempted_action attributes

---

### Subtask T002 – Create plan_state_service.py with Helpers

**Purpose**: Create the service module with foundational imports and helper functions.

**Steps**:
1. Create new file `src/services/plan_state_service.py`
2. Add module docstring and imports:

```python
"""Plan State Service for F077.

Provides state transition functions for event plan lifecycle management.
State machine: DRAFT → LOCKED → IN_PRODUCTION → COMPLETED

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from typing import Optional

from sqlalchemy.orm import Session

from src.models.event import Event, PlanState
from src.services.database import session_scope
from src.services.exceptions import PlanStateError, ValidationError
```

3. Add helper function to get event with validation:

```python
def _get_event_or_raise(event_id: int, session: Session) -> Event:
    """Get event by ID or raise ValidationError if not found.

    Args:
        event_id: Event ID to fetch
        session: Database session

    Returns:
        Event instance

    Raises:
        ValidationError: If event does not exist
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])
    return event


def get_plan_state(event_id: int, session: Session = None) -> PlanState:
    """Get the current plan state for an event.

    Args:
        event_id: Event ID to query
        session: Optional session for transaction sharing

    Returns:
        Current PlanState value

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        event = _get_event_or_raise(event_id, session)
        return event.plan_state

    with session_scope() as session:
        event = _get_event_or_raise(event_id, session)
        return event.plan_state
```

**Files**: `src/services/plan_state_service.py` (new file)

**Validation**:
- [ ] Module imports successfully
- [ ] get_plan_state() returns correct PlanState for existing event
- [ ] get_plan_state() raises ValidationError for non-existent event

---

### Subtask T003 – Implement lock_plan() Transition

**Purpose**: Implement the first state transition from DRAFT to LOCKED.

**Steps**:
1. Add lock_plan function to plan_state_service.py:

```python
def _lock_plan_impl(event_id: int, session: Session) -> Event:
    """Internal implementation of lock_plan."""
    event = _get_event_or_raise(event_id, session)

    if event.plan_state != PlanState.DRAFT:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "lock plan (must be in DRAFT state)"
        )

    event.plan_state = PlanState.LOCKED
    session.flush()
    return event


def lock_plan(event_id: int, session: Session = None) -> Event:
    """Transition event plan from DRAFT to LOCKED.

    Locking a plan prevents recipe and finished goods modifications.
    Batch decisions can still be modified while locked.

    Args:
        event_id: Event ID to lock
        session: Optional session for transaction sharing

    Returns:
        Updated Event instance

    Raises:
        ValidationError: If event not found
        PlanStateError: If plan is not in DRAFT state
    """
    if session is not None:
        return _lock_plan_impl(event_id, session)

    with session_scope() as session:
        return _lock_plan_impl(event_id, session)
```

**Files**: `src/services/plan_state_service.py`

**Validation**:
- [ ] lock_plan() on DRAFT event succeeds and returns event with LOCKED state
- [ ] lock_plan() on LOCKED event raises PlanStateError
- [ ] lock_plan() on IN_PRODUCTION event raises PlanStateError
- [ ] lock_plan() on COMPLETED event raises PlanStateError

---

### Subtask T004 – Implement start_production() and complete_production()

**Purpose**: Implement the remaining state transitions.

**Steps**:
1. Add start_production function:

```python
def _start_production_impl(event_id: int, session: Session) -> Event:
    """Internal implementation of start_production."""
    event = _get_event_or_raise(event_id, session)

    if event.plan_state != PlanState.LOCKED:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "start production (must be in LOCKED state)"
        )

    event.plan_state = PlanState.IN_PRODUCTION
    session.flush()
    return event


def start_production(event_id: int, session: Session = None) -> Event:
    """Transition event plan from LOCKED to IN_PRODUCTION.

    Starting production prevents most modifications. Only amendments
    (via F078) will be allowed after this point.

    Args:
        event_id: Event ID to start production
        session: Optional session for transaction sharing

    Returns:
        Updated Event instance

    Raises:
        ValidationError: If event not found
        PlanStateError: If plan is not in LOCKED state
    """
    if session is not None:
        return _start_production_impl(event_id, session)

    with session_scope() as session:
        return _start_production_impl(event_id, session)
```

2. Add complete_production function:

```python
def _complete_production_impl(event_id: int, session: Session) -> Event:
    """Internal implementation of complete_production."""
    event = _get_event_or_raise(event_id, session)

    if event.plan_state != PlanState.IN_PRODUCTION:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "complete production (must be in IN_PRODUCTION state)"
        )

    event.plan_state = PlanState.COMPLETED
    session.flush()
    return event


def complete_production(event_id: int, session: Session = None) -> Event:
    """Transition event plan from IN_PRODUCTION to COMPLETED.

    Completing production makes the plan read-only. No further
    modifications are allowed.

    Args:
        event_id: Event ID to complete
        session: Optional session for transaction sharing

    Returns:
        Updated Event instance

    Raises:
        ValidationError: If event not found
        PlanStateError: If plan is not in IN_PRODUCTION state
    """
    if session is not None:
        return _complete_production_impl(event_id, session)

    with session_scope() as session:
        return _complete_production_impl(event_id, session)
```

**Files**: `src/services/plan_state_service.py`

**Validation**:
- [ ] start_production() on LOCKED event succeeds → IN_PRODUCTION
- [ ] start_production() on non-LOCKED event raises PlanStateError
- [ ] complete_production() on IN_PRODUCTION event succeeds → COMPLETED
- [ ] complete_production() on non-IN_PRODUCTION event raises PlanStateError

---

### Subtask T005 – Write Unit Tests

**Purpose**: Comprehensive test coverage for all state transitions and edge cases.

**Steps**:
1. Create `src/tests/test_plan_state_service.py`:

```python
"""Unit tests for plan_state_service.py (F077).

Tests cover:
- All valid state transitions
- Invalid transition rejection
- Event not found handling
- Session management patterns
"""

import pytest
from datetime import date

from src.models.event import Event, PlanState
from src.services.database import session_scope
from src.services.plan_state_service import (
    get_plan_state,
    lock_plan,
    start_production,
    complete_production,
)
from src.services.exceptions import PlanStateError, ValidationError


@pytest.fixture
def draft_event():
    """Create a test event in DRAFT state."""
    with session_scope() as session:
        event = Event(
            name="Test Event",
            date=date(2026, 12, 25),
            plan_state=PlanState.DRAFT,
        )
        session.add(event)
        session.flush()
        event_id = event.id
    return event_id


class TestGetPlanState:
    """Tests for get_plan_state()."""

    def test_returns_current_state(self, draft_event):
        """Should return the current plan state."""
        state = get_plan_state(draft_event)
        assert state == PlanState.DRAFT

    def test_event_not_found(self):
        """Should raise ValidationError for non-existent event."""
        with pytest.raises(ValidationError) as exc_info:
            get_plan_state(99999)
        assert "not found" in str(exc_info.value)


class TestLockPlan:
    """Tests for lock_plan()."""

    def test_draft_to_locked(self, draft_event):
        """Should transition from DRAFT to LOCKED."""
        event = lock_plan(draft_event)
        assert event.plan_state == PlanState.LOCKED

        # Verify persisted
        assert get_plan_state(draft_event) == PlanState.LOCKED

    def test_locked_raises_error(self, draft_event):
        """Should reject lock on already locked plan."""
        lock_plan(draft_event)

        with pytest.raises(PlanStateError) as exc_info:
            lock_plan(draft_event)

        assert exc_info.value.event_id == draft_event
        assert exc_info.value.current_state == PlanState.LOCKED

    def test_in_production_raises_error(self, draft_event):
        """Should reject lock on in-production plan."""
        lock_plan(draft_event)
        start_production(draft_event)

        with pytest.raises(PlanStateError):
            lock_plan(draft_event)

    def test_completed_raises_error(self, draft_event):
        """Should reject lock on completed plan."""
        lock_plan(draft_event)
        start_production(draft_event)
        complete_production(draft_event)

        with pytest.raises(PlanStateError):
            lock_plan(draft_event)

    def test_event_not_found(self):
        """Should raise ValidationError for non-existent event."""
        with pytest.raises(ValidationError):
            lock_plan(99999)


class TestStartProduction:
    """Tests for start_production()."""

    def test_locked_to_in_production(self, draft_event):
        """Should transition from LOCKED to IN_PRODUCTION."""
        lock_plan(draft_event)

        event = start_production(draft_event)
        assert event.plan_state == PlanState.IN_PRODUCTION

    def test_draft_raises_error(self, draft_event):
        """Should reject start_production on draft plan."""
        with pytest.raises(PlanStateError) as exc_info:
            start_production(draft_event)

        assert "LOCKED" in str(exc_info.value)

    def test_in_production_raises_error(self, draft_event):
        """Should reject start_production on already in-production plan."""
        lock_plan(draft_event)
        start_production(draft_event)

        with pytest.raises(PlanStateError):
            start_production(draft_event)

    def test_completed_raises_error(self, draft_event):
        """Should reject start_production on completed plan."""
        lock_plan(draft_event)
        start_production(draft_event)
        complete_production(draft_event)

        with pytest.raises(PlanStateError):
            start_production(draft_event)


class TestCompleteProduction:
    """Tests for complete_production()."""

    def test_in_production_to_completed(self, draft_event):
        """Should transition from IN_PRODUCTION to COMPLETED."""
        lock_plan(draft_event)
        start_production(draft_event)

        event = complete_production(draft_event)
        assert event.plan_state == PlanState.COMPLETED

    def test_draft_raises_error(self, draft_event):
        """Should reject complete_production on draft plan."""
        with pytest.raises(PlanStateError):
            complete_production(draft_event)

    def test_locked_raises_error(self, draft_event):
        """Should reject complete_production on locked plan."""
        lock_plan(draft_event)

        with pytest.raises(PlanStateError):
            complete_production(draft_event)

    def test_completed_raises_error(self, draft_event):
        """Should reject complete_production on already completed plan."""
        lock_plan(draft_event)
        start_production(draft_event)
        complete_production(draft_event)

        with pytest.raises(PlanStateError):
            complete_production(draft_event)


class TestFullLifecycle:
    """Test complete state machine lifecycle."""

    def test_full_transition_sequence(self, draft_event):
        """Should support full DRAFT → LOCKED → IN_PRODUCTION → COMPLETED."""
        assert get_plan_state(draft_event) == PlanState.DRAFT

        lock_plan(draft_event)
        assert get_plan_state(draft_event) == PlanState.LOCKED

        start_production(draft_event)
        assert get_plan_state(draft_event) == PlanState.IN_PRODUCTION

        complete_production(draft_event)
        assert get_plan_state(draft_event) == PlanState.COMPLETED
```

2. Run tests to verify:
```bash
pytest src/tests/test_plan_state_service.py -v
```

**Files**: `src/tests/test_plan_state_service.py` (new file)

**Validation**:
- [ ] All tests pass
- [ ] Test coverage includes happy path and error cases
- [ ] Tests run in isolation (use fixtures properly)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session not flushed | Use session.flush() after state change |
| State not persisted | Test by re-querying after transition |
| Circular import | Import PlanState from models, not services |

## Definition of Done Checklist

- [ ] PlanStateError exception added to exceptions.py
- [ ] plan_state_service.py created with all functions
- [ ] get_plan_state() works correctly
- [ ] lock_plan() transitions and validates correctly
- [ ] start_production() transitions and validates correctly
- [ ] complete_production() transitions and validates correctly
- [ ] All unit tests pass
- [ ] No linting errors

## Review Guidance

- Verify exception message format is user-friendly
- Verify session management follows CLAUDE.md pattern
- Verify all invalid transitions raise PlanStateError
- Run full test suite to check for regressions

## Activity Log

- 2026-01-28T00:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-27T22:43:25Z – claude – shell_pid=55084 – lane=for_review – Implementation complete: 25 tests passing
- 2026-01-27T22:44:08Z – claude – shell_pid=56673 – lane=doing – Started review via workflow command
- 2026-01-27T22:44:35Z – claude – shell_pid=56673 – lane=done – Review passed: All success criteria met, 25 tests passing, follows session management pattern
