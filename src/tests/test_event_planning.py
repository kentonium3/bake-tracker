"""
Unit tests for F068 planning methods in EventService.

Tests cover:
- get_events_for_planning
- create_planning_event
- update_planning_event
- delete_planning_event
"""

import pytest
from datetime import date

from src.services import event_service
from src.services.exceptions import ValidationError
from src.models import Event, PlanState


class TestGetEventsForPlanning:
    """Tests for get_events_for_planning method."""

    def test_returns_events_sorted_by_date(self, test_db):
        """Events should be sorted by date, most recent first."""
        # Create events in random order
        event_service.create_planning_event(test_db, "Event A", date(2026, 6, 15))
        event_service.create_planning_event(test_db, "Event B", date(2026, 12, 20))
        event_service.create_planning_event(test_db, "Event C", date(2026, 3, 10))
        test_db.commit()

        events = event_service.get_events_for_planning(test_db)

        assert len(events) == 3
        assert events[0].name == "Event B"  # Most recent
        assert events[1].name == "Event A"
        assert events[2].name == "Event C"  # Oldest

    def test_excludes_completed_events_by_default(self, test_db):
        """Completed events should be excluded unless requested."""
        event = event_service.create_planning_event(test_db, "Test", date(2026, 12, 20))
        event.plan_state = PlanState.COMPLETED
        test_db.commit()

        events = event_service.get_events_for_planning(test_db)
        assert len(events) == 0

    def test_includes_completed_events_when_requested(self, test_db):
        """Completed events included when include_completed=True."""
        event = event_service.create_planning_event(test_db, "Test", date(2026, 12, 20))
        event.plan_state = PlanState.COMPLETED
        test_db.commit()

        events = event_service.get_events_for_planning(test_db, include_completed=True)
        assert len(events) == 1

    def test_includes_all_non_completed_states(self, test_db):
        """Events in DRAFT, LOCKED, IN_PRODUCTION should be included."""
        e1 = event_service.create_planning_event(test_db, "Draft", date(2026, 12, 20))
        e1.plan_state = PlanState.DRAFT

        e2 = event_service.create_planning_event(test_db, "Locked", date(2026, 12, 21))
        e2.plan_state = PlanState.LOCKED

        e3 = event_service.create_planning_event(test_db, "InProd", date(2026, 12, 22))
        e3.plan_state = PlanState.IN_PRODUCTION

        test_db.commit()

        events = event_service.get_events_for_planning(test_db)
        assert len(events) == 3


class TestCreatePlanningEvent:
    """Tests for create_planning_event method."""

    def test_creates_event_with_required_fields(self, test_db):
        """Event created with name, date, and default plan_state."""
        event = event_service.create_planning_event(
            test_db, "Christmas 2026", date(2026, 12, 20)
        )
        test_db.commit()

        assert event.id is not None
        assert event.name == "Christmas 2026"
        assert event.event_date == date(2026, 12, 20)
        assert event.year == 2026
        assert event.plan_state == PlanState.DRAFT
        assert event.expected_attendees is None

    def test_creates_event_with_expected_attendees(self, test_db):
        """Event created with optional attendee count."""
        event = event_service.create_planning_event(
            test_db, "Party", date(2026, 7, 4), expected_attendees=50
        )
        test_db.commit()

        assert event.expected_attendees == 50

    def test_creates_event_with_notes(self, test_db):
        """Event created with optional notes."""
        event = event_service.create_planning_event(
            test_db, "Party", date(2026, 7, 4), notes="Test notes"
        )
        test_db.commit()

        assert event.notes == "Test notes"

    def test_rejects_negative_attendees(self, test_db):
        """Negative attendee count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            event_service.create_planning_event(
                test_db, "Party", date(2026, 7, 4), expected_attendees=-5
            )

        assert "positive integer" in str(exc_info.value)

    def test_rejects_zero_attendees(self, test_db):
        """Zero attendee count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            event_service.create_planning_event(
                test_db, "Party", date(2026, 7, 4), expected_attendees=0
            )

        assert "positive integer" in str(exc_info.value)


class TestUpdatePlanningEvent:
    """Tests for update_planning_event method."""

    def test_updates_name(self, test_db):
        """Event name can be updated."""
        event = event_service.create_planning_event(test_db, "Old Name", date(2026, 12, 20))
        test_db.commit()

        updated = event_service.update_planning_event(test_db, event.id, name="New Name")
        test_db.commit()

        assert updated.name == "New Name"

    def test_updates_date(self, test_db):
        """Event date can be updated."""
        event = event_service.create_planning_event(test_db, "Test", date(2026, 12, 20))
        test_db.commit()

        updated = event_service.update_planning_event(
            test_db, event.id, event_date=date(2026, 12, 25)
        )
        test_db.commit()

        assert updated.event_date == date(2026, 12, 25)
        assert updated.year == 2026

    def test_updates_expected_attendees(self, test_db):
        """Attendee count can be updated."""
        event = event_service.create_planning_event(test_db, "Party", date(2026, 7, 4))
        test_db.commit()

        updated = event_service.update_planning_event(
            test_db, event.id, expected_attendees=75
        )
        test_db.commit()

        assert updated.expected_attendees == 75

    def test_clears_attendees_with_zero(self, test_db):
        """Passing 0 clears expected_attendees to None."""
        event = event_service.create_planning_event(
            test_db, "Party", date(2026, 7, 4), expected_attendees=50
        )
        test_db.commit()

        updated = event_service.update_planning_event(
            test_db, event.id, expected_attendees=0
        )
        test_db.commit()

        assert updated.expected_attendees is None

    def test_updates_notes(self, test_db):
        """Notes can be updated."""
        event = event_service.create_planning_event(test_db, "Test", date(2026, 12, 20))
        test_db.commit()

        updated = event_service.update_planning_event(
            test_db, event.id, notes="Updated notes"
        )
        test_db.commit()

        assert updated.notes == "Updated notes"

    def test_rejects_negative_attendees(self, test_db):
        """Negative attendee count should raise ValidationError."""
        event = event_service.create_planning_event(test_db, "Test", date(2026, 12, 20))
        test_db.commit()

        with pytest.raises(ValidationError) as exc_info:
            event_service.update_planning_event(
                test_db, event.id, expected_attendees=-5
            )

        assert "positive integer" in str(exc_info.value)

    def test_rejects_not_found(self, test_db):
        """Non-existent event ID raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            event_service.update_planning_event(test_db, 99999, name="Test")

        assert "not found" in str(exc_info.value)

    def test_no_changes_when_no_params(self, test_db):
        """Event unchanged when no update params provided."""
        event = event_service.create_planning_event(
            test_db, "Original", date(2026, 12, 20), expected_attendees=50
        )
        test_db.commit()
        original_name = event.name
        original_attendees = event.expected_attendees

        updated = event_service.update_planning_event(test_db, event.id)
        test_db.commit()

        assert updated.name == original_name
        assert updated.expected_attendees == original_attendees


class TestDeletePlanningEvent:
    """Tests for delete_planning_event method."""

    def test_deletes_event(self, test_db):
        """Event is deleted successfully."""
        event = event_service.create_planning_event(test_db, "Test", date(2026, 12, 20))
        test_db.commit()
        event_id = event.id

        result = event_service.delete_planning_event(test_db, event_id)
        test_db.commit()

        assert result is True
        assert test_db.query(Event).filter(Event.id == event_id).first() is None

    def test_returns_false_for_not_found(self, test_db):
        """Returns False for non-existent event."""
        result = event_service.delete_planning_event(test_db, 99999)
        assert result is False

    def test_delete_is_idempotent(self, test_db):
        """Deleting already-deleted event returns False."""
        event = event_service.create_planning_event(test_db, "Test", date(2026, 12, 20))
        test_db.commit()
        event_id = event.id

        # First delete
        result1 = event_service.delete_planning_event(test_db, event_id)
        test_db.commit()
        assert result1 is True

        # Second delete
        result2 = event_service.delete_planning_event(test_db, event_id)
        assert result2 is False


class TestValidateExpectedAttendees:
    """Tests for _validate_expected_attendees helper."""

    def test_accepts_none(self, test_db):
        """None is valid (optional field)."""
        # Should not raise
        event_service._validate_expected_attendees(None)

    def test_accepts_positive(self, test_db):
        """Positive integers are valid."""
        # Should not raise
        event_service._validate_expected_attendees(1)
        event_service._validate_expected_attendees(100)
        event_service._validate_expected_attendees(1000000)

    def test_rejects_zero(self, test_db):
        """Zero raises ValidationError."""
        with pytest.raises(ValidationError):
            event_service._validate_expected_attendees(0)

    def test_rejects_negative(self, test_db):
        """Negative values raise ValidationError."""
        with pytest.raises(ValidationError):
            event_service._validate_expected_attendees(-1)
        with pytest.raises(ValidationError):
            event_service._validate_expected_attendees(-100)
