"""
Tests for EventService fulfillment status methods.

Feature 016: Event-Centric Production Model
Work Package: WP05 - Service Layer - Fulfillment Status
"""

from datetime import date, datetime, UTC

import pytest

from src.models import (
    Event,
    EventRecipientPackage,
    FulfillmentStatus,
    Recipient,
    Package,
)
from src.services import event_service


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_event(test_db):
    """Create a test event."""
    session = test_db()
    event = Event(
        name="Holiday 2024",
        event_date=date(2024, 12, 25),
        year=2024,
    )
    session.add(event)
    session.commit()
    return event


@pytest.fixture
def test_recipient(test_db):
    """Create a test recipient."""
    session = test_db()
    recipient = Recipient(name="Test Recipient")
    session.add(recipient)
    session.commit()
    return recipient


@pytest.fixture
def test_package(test_db):
    """Create a test package."""
    session = test_db()
    package = Package(
        name="Cookie Box",
    )
    session.add(package)
    session.commit()
    return package


@pytest.fixture
def test_assignment(test_db, test_event, test_recipient, test_package):
    """Create a test package assignment with default pending status."""
    session = test_db()
    assignment = EventRecipientPackage(
        event_id=test_event.id,
        recipient_id=test_recipient.id,
        package_id=test_package.id,
        quantity=1,
        fulfillment_status=FulfillmentStatus.PENDING.value,
    )
    session.add(assignment)
    session.commit()
    return assignment


# ============================================================================
# TestFulfillmentStatus - Transition Tests
# ============================================================================


class TestFulfillmentStatusTransitions:
    """Test fulfillment status transition validation."""

    def test_transition_pending_to_ready(self, test_db, test_assignment):
        """Valid transition: pending -> ready."""
        # Initial status is pending
        assert test_assignment.fulfillment_status == FulfillmentStatus.PENDING.value

        # Transition to ready
        result = event_service.update_fulfillment_status(
            test_assignment.id, FulfillmentStatus.READY
        )

        # Verify transition succeeded
        assert result.fulfillment_status == FulfillmentStatus.READY.value

        # Verify persisted in database
        session = test_db()
        refreshed = session.get(EventRecipientPackage, test_assignment.id)
        assert refreshed.fulfillment_status == FulfillmentStatus.READY.value

    def test_transition_ready_to_delivered(self, test_db, test_event, test_recipient, test_package):
        """Valid transition: ready -> delivered."""
        session = test_db()
        # Create assignment with ready status
        assignment = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=1,
            fulfillment_status=FulfillmentStatus.READY.value,
        )
        session.add(assignment)
        session.commit()

        # Transition to delivered
        result = event_service.update_fulfillment_status(assignment.id, FulfillmentStatus.DELIVERED)

        # Verify transition succeeded
        assert result.fulfillment_status == FulfillmentStatus.DELIVERED.value

    def test_transition_pending_to_delivered_invalid(self, test_db, test_assignment):
        """Invalid transition: cannot skip pending -> delivered."""
        # Attempt to skip to delivered
        with pytest.raises(ValueError) as exc_info:
            event_service.update_fulfillment_status(test_assignment.id, FulfillmentStatus.DELIVERED)

        # Verify error message
        assert "Invalid transition" in str(exc_info.value)
        assert "pending" in str(exc_info.value)
        assert "delivered" in str(exc_info.value)
        assert "Allowed: ['ready']" in str(exc_info.value)

    def test_transition_delivered_to_any_invalid(
        self, test_db, test_event, test_recipient, test_package
    ):
        """Invalid transition: delivered is terminal state."""
        session = test_db()
        # Create assignment with delivered status
        assignment = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=1,
            fulfillment_status=FulfillmentStatus.DELIVERED.value,
        )
        session.add(assignment)
        session.commit()
        assignment_id = assignment.id  # Capture ID before session closes

        # Attempt to transition to ready (backwards)
        with pytest.raises(ValueError) as exc_info:
            event_service.update_fulfillment_status(assignment_id, FulfillmentStatus.READY)

        assert "Invalid transition" in str(exc_info.value)
        assert "Allowed: []" in str(exc_info.value)

        # Attempt to transition to pending (backwards)
        with pytest.raises(ValueError) as exc_info:
            event_service.update_fulfillment_status(assignment_id, FulfillmentStatus.PENDING)

        assert "Invalid transition" in str(exc_info.value)

    def test_transition_ready_to_pending_invalid(
        self, test_db, test_event, test_recipient, test_package
    ):
        """Invalid transition: cannot go backwards ready -> pending."""
        session = test_db()
        # Create assignment with ready status
        assignment = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=1,
            fulfillment_status=FulfillmentStatus.READY.value,
        )
        session.add(assignment)
        session.commit()

        # Attempt to go backwards
        with pytest.raises(ValueError) as exc_info:
            event_service.update_fulfillment_status(assignment.id, FulfillmentStatus.PENDING)

        assert "Invalid transition" in str(exc_info.value)
        assert "ready" in str(exc_info.value)
        assert "pending" in str(exc_info.value)

    def test_package_not_found(self, test_db):
        """ValueError raised for non-existent package."""
        with pytest.raises(ValueError) as exc_info:
            event_service.update_fulfillment_status(99999, FulfillmentStatus.READY)

        assert "not found" in str(exc_info.value)
        assert "99999" in str(exc_info.value)


# ============================================================================
# TestGetPackagesByStatus - Filter Tests
# ============================================================================


class TestGetPackagesByStatus:
    """Test get_packages_by_status filtering."""

    def test_filter_by_status_pending(self, test_db, test_event, test_recipient, test_package):
        """Returns only packages with matching pending status."""
        session = test_db()

        # Create packages with different statuses
        pending = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=1,
            fulfillment_status=FulfillmentStatus.PENDING.value,
        )
        ready = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=2,
            fulfillment_status=FulfillmentStatus.READY.value,
        )
        session.add_all([pending, ready])
        session.commit()

        # Filter by pending
        result = event_service.get_packages_by_status(test_event.id, FulfillmentStatus.PENDING)

        assert len(result) == 1
        assert result[0].fulfillment_status == FulfillmentStatus.PENDING.value
        assert result[0].quantity == 1

    def test_filter_by_status_ready(self, test_db, test_event, test_recipient, test_package):
        """Returns only packages with matching ready status."""
        session = test_db()

        # Create packages with different statuses
        pending = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=1,
            fulfillment_status=FulfillmentStatus.PENDING.value,
        )
        ready = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=2,
            fulfillment_status=FulfillmentStatus.READY.value,
        )
        delivered = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=3,
            fulfillment_status=FulfillmentStatus.DELIVERED.value,
        )
        session.add_all([pending, ready, delivered])
        session.commit()

        # Filter by ready
        result = event_service.get_packages_by_status(test_event.id, FulfillmentStatus.READY)

        assert len(result) == 1
        assert result[0].fulfillment_status == FulfillmentStatus.READY.value
        assert result[0].quantity == 2

    def test_filter_by_status_delivered(self, test_db, test_event, test_recipient, test_package):
        """Returns only packages with matching delivered status."""
        session = test_db()

        # Create packages with different statuses
        pending = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=1,
            fulfillment_status=FulfillmentStatus.PENDING.value,
        )
        delivered = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=3,
            fulfillment_status=FulfillmentStatus.DELIVERED.value,
        )
        session.add_all([pending, delivered])
        session.commit()

        # Filter by delivered
        result = event_service.get_packages_by_status(test_event.id, FulfillmentStatus.DELIVERED)

        assert len(result) == 1
        assert result[0].fulfillment_status == FulfillmentStatus.DELIVERED.value
        assert result[0].quantity == 3

    def test_all_packages_when_no_filter(self, test_db, test_event, test_recipient, test_package):
        """Returns all packages when status=None."""
        session = test_db()

        # Create packages with different statuses
        pending = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=1,
            fulfillment_status=FulfillmentStatus.PENDING.value,
        )
        ready = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=2,
            fulfillment_status=FulfillmentStatus.READY.value,
        )
        delivered = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=3,
            fulfillment_status=FulfillmentStatus.DELIVERED.value,
        )
        session.add_all([pending, ready, delivered])
        session.commit()

        # Get all (no filter)
        result = event_service.get_packages_by_status(test_event.id, status=None)

        assert len(result) == 3

    def test_empty_result(self, test_db, test_event):
        """Empty list when no matching packages."""
        # No packages exist for this event
        result = event_service.get_packages_by_status(test_event.id, FulfillmentStatus.PENDING)

        assert result == []

    def test_eager_loads_relationships(self, test_db, test_event, test_recipient, test_package):
        """Verifies recipient and package are eager loaded."""
        session = test_db()

        assignment = EventRecipientPackage(
            event_id=test_event.id,
            recipient_id=test_recipient.id,
            package_id=test_package.id,
            quantity=1,
            fulfillment_status=FulfillmentStatus.PENDING.value,
        )
        session.add(assignment)
        session.commit()

        # Get packages
        result = event_service.get_packages_by_status(test_event.id)

        # Verify relationships are loaded (would fail if lazy loaded)
        assert len(result) == 1
        assert result[0].recipient is not None
        assert result[0].recipient.name == "Test Recipient"
        assert result[0].package is not None
        assert result[0].package.name == "Cookie Box"
