"""Unit tests for RecipientService.

Tests cover:
- CRUD operations (create, get, update, delete)
- Search functionality (by name, household)
- Dependency checking (assignments)
- Force delete behavior (FR-018)
"""

import pytest
from datetime import date

from src.services.recipient_service import (
    create_recipient,
    get_recipient,
    get_recipient_by_name,
    get_all_recipients,
    update_recipient,
    delete_recipient,
    check_recipient_has_assignments,
    get_recipient_assignment_count,
    get_recipient_events,
    search_recipients,
    get_recipients_by_household,
    RecipientNotFound,
    RecipientHasAssignmentsError,
)
from src.services.exceptions import ValidationError
from src.models import Recipient, Event, EventRecipientPackage, Package


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_recipient(test_db):
    """Create a sample recipient for testing."""
    recipient = create_recipient(
        {
            "name": "John Doe",
            "household_name": "Doe Family",
            "address": "123 Main St",
            "notes": "Test recipient",
        }
    )
    return recipient


@pytest.fixture
def sample_recipients(test_db):
    """Create multiple recipients for testing."""
    recipients = []
    for i, data in enumerate(
        [
            {"name": "Alice Smith", "household_name": "Smith Family"},
            {"name": "Bob Smith", "household_name": "Smith Family"},
            {"name": "Carol Johnson", "household_name": "Johnson Family"},
            {"name": "Dan Brown", "household_name": None},
        ]
    ):
        recipients.append(create_recipient(data))
    return recipients


@pytest.fixture
def sample_event_with_assignment(test_db, sample_recipient):
    """Create an event with a recipient assignment."""
    session = test_db()

    # Create a package
    package = Package(name="Test Package", description="Test")
    session.add(package)
    session.commit()

    # Create an event
    event = Event(
        name="Test Event",
        event_date=date(2024, 12, 25),
        year=2024,
    )
    session.add(event)
    session.commit()

    # Create assignment
    assignment = EventRecipientPackage(
        event_id=event.id,
        recipient_id=sample_recipient.id,
        package_id=package.id,
        quantity=1,
    )
    session.add(assignment)
    session.commit()

    return event, sample_recipient, package


# ============================================================================
# Create Recipient Tests
# ============================================================================


class TestCreateRecipient:
    """Tests for create_recipient function."""

    def test_create_recipient_success(self, test_db):
        """Should create a recipient with valid data."""
        recipient = create_recipient(
            {
                "name": "Test Person",
                "household_name": "Test Family",
                "address": "456 Oak St",
                "notes": "Some notes",
            }
        )

        assert recipient is not None
        assert recipient.id is not None
        assert recipient.name == "Test Person"
        assert recipient.household_name == "Test Family"
        assert recipient.address == "456 Oak St"
        assert recipient.notes == "Some notes"

    def test_create_recipient_minimal(self, test_db):
        """Should create a recipient with only required fields."""
        recipient = create_recipient({"name": "Minimal Person"})

        assert recipient is not None
        assert recipient.name == "Minimal Person"
        assert recipient.household_name is None
        assert recipient.address is None

    def test_create_recipient_missing_name(self, test_db):
        """Should raise ValidationError when name is missing."""
        with pytest.raises(ValidationError):
            create_recipient({"household_name": "No Name Family"})

    def test_create_recipient_empty_name(self, test_db):
        """Should raise ValidationError when name is empty."""
        with pytest.raises(ValidationError):
            create_recipient({"name": ""})


# ============================================================================
# Get Recipient Tests
# ============================================================================


class TestGetRecipient:
    """Tests for get_recipient function."""

    def test_get_recipient_by_id(self, test_db, sample_recipient):
        """Should retrieve a recipient by ID."""
        retrieved = get_recipient(sample_recipient.id)

        assert retrieved is not None
        assert retrieved.id == sample_recipient.id
        assert retrieved.name == sample_recipient.name

    def test_get_recipient_not_found(self, test_db):
        """Should raise RecipientNotFound for invalid ID."""
        with pytest.raises(RecipientNotFound) as exc_info:
            get_recipient(99999)

        assert exc_info.value.recipient_id == 99999


class TestGetRecipientByName:
    """Tests for get_recipient_by_name function."""

    def test_get_recipient_by_name_exact(self, test_db, sample_recipient):
        """Should find recipient by exact name match."""
        retrieved = get_recipient_by_name("John Doe")

        assert retrieved is not None
        assert retrieved.name == "John Doe"

    def test_get_recipient_by_name_case_insensitive(self, test_db, sample_recipient):
        """Should find recipient case-insensitively."""
        retrieved = get_recipient_by_name("JOHN DOE")

        assert retrieved is not None
        assert retrieved.name == "John Doe"

    def test_get_recipient_by_name_not_found(self, test_db):
        """Should raise RecipientNotFoundByName when name not found."""
        import pytest
        from src.services.exceptions import RecipientNotFoundByName

        with pytest.raises(RecipientNotFoundByName) as exc_info:
            get_recipient_by_name("Nonexistent Person")
        assert exc_info.value.name == "Nonexistent Person"


# ============================================================================
# Get All Recipients Tests
# ============================================================================


class TestGetAllRecipients:
    """Tests for get_all_recipients function."""

    def test_get_all_recipients(self, test_db, sample_recipients):
        """Should return all recipients ordered by name."""
        recipients = get_all_recipients()

        assert len(recipients) == 4
        # Verify ordering by name
        names = [r.name for r in recipients]
        assert names == sorted(names)

    def test_get_all_recipients_empty(self, test_db):
        """Should return empty list when no recipients exist."""
        recipients = get_all_recipients()

        assert recipients == []

    def test_get_all_recipients_with_name_filter(self, test_db, sample_recipients):
        """Should filter by name."""
        recipients = get_all_recipients(name_search="Smith")

        assert len(recipients) == 2
        assert all("Smith" in r.name for r in recipients)

    def test_get_all_recipients_with_household_filter(self, test_db, sample_recipients):
        """Should filter by household."""
        recipients = get_all_recipients(household_search="Johnson")

        assert len(recipients) == 1
        assert recipients[0].household_name == "Johnson Family"


# ============================================================================
# Update Recipient Tests
# ============================================================================


class TestUpdateRecipient:
    """Tests for update_recipient function."""

    def test_update_recipient_success(self, test_db, sample_recipient):
        """Should update recipient with valid data."""
        updated = update_recipient(
            sample_recipient.id,
            {
                "name": "John Updated",
                "household_name": "Updated Family",
                "address": "789 New St",
                "notes": "Updated notes",
            },
        )

        assert updated.name == "John Updated"
        assert updated.household_name == "Updated Family"
        assert updated.address == "789 New St"
        assert updated.notes == "Updated notes"

    def test_update_recipient_not_found(self, test_db):
        """Should raise RecipientNotFound for invalid ID."""
        with pytest.raises(RecipientNotFound):
            update_recipient(99999, {"name": "Test"})

    def test_update_recipient_empty_name(self, test_db, sample_recipient):
        """Should raise ValidationError when name is empty."""
        with pytest.raises(ValidationError):
            update_recipient(sample_recipient.id, {"name": ""})


# ============================================================================
# Delete Recipient Tests
# ============================================================================


class TestDeleteRecipient:
    """Tests for delete_recipient function."""

    def test_delete_recipient_success(self, test_db, sample_recipient):
        """Should delete a recipient without assignments."""
        result = delete_recipient(sample_recipient.id)

        assert result is True

        with pytest.raises(RecipientNotFound):
            get_recipient(sample_recipient.id)

    def test_delete_recipient_not_found(self, test_db):
        """Should raise RecipientNotFound for invalid ID."""
        with pytest.raises(RecipientNotFound):
            delete_recipient(99999)

    def test_delete_recipient_with_assignments_no_force(
        self, test_db, sample_event_with_assignment
    ):
        """Should raise error when deleting recipient with assignments."""
        event, recipient, package = sample_event_with_assignment

        with pytest.raises(RecipientHasAssignmentsError) as exc_info:
            delete_recipient(recipient.id)

        assert exc_info.value.recipient_id == recipient.id
        assert exc_info.value.assignment_count == 1

    def test_delete_recipient_with_assignments_force(self, test_db, sample_event_with_assignment):
        """Should delete recipient with force=True."""
        event, recipient, package = sample_event_with_assignment

        result = delete_recipient(recipient.id, force=True)

        assert result is True

        with pytest.raises(RecipientNotFound):
            get_recipient(recipient.id)


# ============================================================================
# Dependency Checking Tests
# ============================================================================


class TestCheckRecipientHasAssignments:
    """Tests for check_recipient_has_assignments function."""

    def test_has_no_assignments(self, test_db, sample_recipient):
        """Should return False when recipient has no assignments."""
        result = check_recipient_has_assignments(sample_recipient.id)

        assert result is False

    def test_has_assignments(self, test_db, sample_event_with_assignment):
        """Should return True when recipient has assignments."""
        event, recipient, package = sample_event_with_assignment

        result = check_recipient_has_assignments(recipient.id)

        assert result is True


class TestGetRecipientAssignmentCount:
    """Tests for get_recipient_assignment_count function."""

    def test_zero_assignments(self, test_db, sample_recipient):
        """Should return 0 when no assignments."""
        count = get_recipient_assignment_count(sample_recipient.id)

        assert count == 0

    def test_multiple_assignments(self, test_db, sample_event_with_assignment):
        """Should count all assignments."""
        event, recipient, package = sample_event_with_assignment
        session = test_db()

        # Add another assignment
        assignment2 = EventRecipientPackage(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=2,
        )
        session.add(assignment2)
        session.commit()

        count = get_recipient_assignment_count(recipient.id)

        assert count == 2


class TestGetRecipientEvents:
    """Tests for get_recipient_events function."""

    def test_no_events(self, test_db, sample_recipient):
        """Should return empty list when no event assignments."""
        events = get_recipient_events(sample_recipient.id)

        assert events == []

    def test_has_events(self, test_db, sample_event_with_assignment):
        """Should return events where recipient has assignments."""
        event, recipient, package = sample_event_with_assignment

        events = get_recipient_events(recipient.id)

        assert len(events) == 1
        assert events[0].id == event.id

    def test_distinct_events(self, test_db, sample_event_with_assignment):
        """Should return distinct events even with multiple assignments."""
        event, recipient, package = sample_event_with_assignment
        session = test_db()

        # Add another assignment to same event
        assignment2 = EventRecipientPackage(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=2,
        )
        session.add(assignment2)
        session.commit()

        events = get_recipient_events(recipient.id)

        # Should still be 1 event (distinct)
        assert len(events) == 1


# ============================================================================
# Search Tests
# ============================================================================


class TestSearchRecipients:
    """Tests for search_recipients function."""

    def test_search_by_name(self, test_db, sample_recipients):
        """Should find recipients by name partial match."""
        results = search_recipients("Smith")

        assert len(results) == 2
        assert all("Smith" in r.name for r in results)

    def test_search_by_household(self, test_db, sample_recipients):
        """Should find recipients by household partial match."""
        results = search_recipients("Johnson")

        assert len(results) == 1
        assert results[0].household_name == "Johnson Family"

    def test_search_case_insensitive(self, test_db, sample_recipients):
        """Should search case-insensitively."""
        results = search_recipients("SMITH")

        assert len(results) == 2

    def test_search_no_results(self, test_db, sample_recipients):
        """Should return empty list when no matches."""
        results = search_recipients("Nonexistent")

        assert results == []


class TestGetRecipientsByHousehold:
    """Tests for get_recipients_by_household function."""

    def test_get_by_household(self, test_db, sample_recipients):
        """Should return all recipients in a household."""
        results = get_recipients_by_household("Smith Family")

        assert len(results) == 2
        assert all(r.household_name == "Smith Family" for r in results)

    def test_get_by_household_empty(self, test_db, sample_recipients):
        """Should return empty list for nonexistent household."""
        results = get_recipients_by_household("Nonexistent Family")

        assert results == []
