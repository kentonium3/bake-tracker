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
def draft_event(test_db):
    """Create a test event in DRAFT state."""
    with session_scope() as session:
        event = Event(
            name="Test Event",
            event_date=date(2026, 12, 25),
            year=2026,
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

    def test_event_not_found(self, test_db):
        """Should raise ValidationError for non-existent event."""
        with pytest.raises(ValidationError) as exc_info:
            get_plan_state(99999)
        assert "not found" in str(exc_info.value)

    def test_with_session(self, draft_event):
        """Should work with provided session."""
        with session_scope() as session:
            state = get_plan_state(draft_event, session=session)
            assert state == PlanState.DRAFT


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
        assert "DRAFT" in str(exc_info.value)

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

    def test_event_not_found(self, test_db):
        """Should raise ValidationError for non-existent event."""
        with pytest.raises(ValidationError):
            lock_plan(99999)

    def test_with_session(self, draft_event):
        """Should work with provided session."""
        with session_scope() as session:
            event = lock_plan(draft_event, session=session)
            assert event.plan_state == PlanState.LOCKED


class TestStartProduction:
    """Tests for start_production()."""

    def test_locked_to_in_production(self, draft_event):
        """Should transition from LOCKED to IN_PRODUCTION."""
        lock_plan(draft_event)

        event = start_production(draft_event)
        assert event.plan_state == PlanState.IN_PRODUCTION

        # Verify persisted
        assert get_plan_state(draft_event) == PlanState.IN_PRODUCTION

    def test_draft_raises_error(self, draft_event):
        """Should reject start_production on draft plan."""
        with pytest.raises(PlanStateError) as exc_info:
            start_production(draft_event)

        assert "LOCKED" in str(exc_info.value)
        assert exc_info.value.current_state == PlanState.DRAFT

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

    def test_event_not_found(self, test_db):
        """Should raise ValidationError for non-existent event."""
        with pytest.raises(ValidationError):
            start_production(99999)


class TestCompleteProduction:
    """Tests for complete_production()."""

    def test_in_production_to_completed(self, draft_event):
        """Should transition from IN_PRODUCTION to COMPLETED."""
        lock_plan(draft_event)
        start_production(draft_event)

        event = complete_production(draft_event)
        assert event.plan_state == PlanState.COMPLETED

        # Verify persisted
        assert get_plan_state(draft_event) == PlanState.COMPLETED

    def test_draft_raises_error(self, draft_event):
        """Should reject complete_production on draft plan."""
        with pytest.raises(PlanStateError) as exc_info:
            complete_production(draft_event)

        assert "IN_PRODUCTION" in str(exc_info.value)
        assert exc_info.value.current_state == PlanState.DRAFT

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

    def test_event_not_found(self, test_db):
        """Should raise ValidationError for non-existent event."""
        with pytest.raises(ValidationError):
            complete_production(99999)


class TestFullLifecycle:
    """Test complete state machine lifecycle."""

    def test_full_transition_sequence(self, draft_event):
        """Should support full DRAFT -> LOCKED -> IN_PRODUCTION -> COMPLETED."""
        assert get_plan_state(draft_event) == PlanState.DRAFT

        lock_plan(draft_event)
        assert get_plan_state(draft_event) == PlanState.LOCKED

        start_production(draft_event)
        assert get_plan_state(draft_event) == PlanState.IN_PRODUCTION

        complete_production(draft_event)
        assert get_plan_state(draft_event) == PlanState.COMPLETED

    def test_cannot_skip_states(self, draft_event):
        """Should not allow skipping states (e.g., DRAFT -> COMPLETED)."""
        # Cannot go directly from DRAFT to IN_PRODUCTION
        with pytest.raises(PlanStateError):
            start_production(draft_event)

        # Cannot go directly from DRAFT to COMPLETED
        with pytest.raises(PlanStateError):
            complete_production(draft_event)

        # Cannot go from LOCKED to COMPLETED
        lock_plan(draft_event)
        with pytest.raises(PlanStateError):
            complete_production(draft_event)


class TestPlanStateErrorAttributes:
    """Test PlanStateError exception attributes."""

    def test_error_has_event_id(self, draft_event):
        """Exception should include event_id."""
        lock_plan(draft_event)

        with pytest.raises(PlanStateError) as exc_info:
            lock_plan(draft_event)

        assert exc_info.value.event_id == draft_event

    def test_error_has_current_state(self, draft_event):
        """Exception should include current_state."""
        lock_plan(draft_event)

        with pytest.raises(PlanStateError) as exc_info:
            lock_plan(draft_event)

        assert exc_info.value.current_state == PlanState.LOCKED

    def test_error_has_attempted_action(self, draft_event):
        """Exception should include attempted_action."""
        lock_plan(draft_event)

        with pytest.raises(PlanStateError) as exc_info:
            lock_plan(draft_event)

        assert "lock plan" in exc_info.value.attempted_action

    def test_error_message_format(self, draft_event):
        """Exception message should be user-friendly."""
        lock_plan(draft_event)

        with pytest.raises(PlanStateError) as exc_info:
            lock_plan(draft_event)

        message = str(exc_info.value)
        assert "Cannot" in message
        assert "locked" in message
        assert str(draft_event) in message
