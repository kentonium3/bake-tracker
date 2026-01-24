"""
Unit tests for ProductionPlanSnapshot model (Feature 039, refactored F065).

Tests cover:
- ProductionPlanSnapshot creation as lightweight container
- Shopping status tracking
- Event relationship and cascade delete
- Event.output_mode enum values

Note: Tests for calculation_results, staleness fields, and related methods
were removed in F065 as those features were replaced with on-demand calculation.
"""

from datetime import date
import pytest
from sqlalchemy.exc import IntegrityError

from src.models import Event, ProductionPlanSnapshot, OutputMode
from src.utils.datetime_utils import utc_now


@pytest.fixture
def sample_event(test_db):
    """Create a sample event for testing."""
    session = test_db()
    event = Event(
        name="Christmas 2025",
        event_date=date(2025, 12, 25),
        year=2025,
        notes="Test event for production planning",
        output_mode=OutputMode.BUNDLED,
    )
    session.add(event)
    session.commit()
    return event


class TestCreateProductionPlanSnapshot:
    """Tests for basic ProductionPlanSnapshot creation."""

    def test_create_snapshot_with_valid_data(self, test_db, sample_event):
        """Test creating a production plan snapshot with valid data."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.id is not None
        assert snapshot.event_id == sample_event.id
        assert snapshot.calculated_at == now
        assert snapshot.shopping_complete is False

    def test_create_snapshot_with_input_hash(self, test_db, sample_event):
        """Test creating snapshot with optional input hash."""
        session = test_db()

        now = utc_now()
        input_hash = "abc123def456" * 5 + "abcd"  # 64 char hash

        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            input_hash=input_hash,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.input_hash == input_hash

    def test_snapshot_requires_event(self, test_db):
        """Test that snapshot requires a valid event_id."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=99999,  # Non-existent event
            calculated_at=now,
        )
        session.add(snapshot)

        with pytest.raises(IntegrityError):
            session.commit()


class TestProductionPlanSnapshotShoppingStatus:
    """Tests for shopping completion tracking."""

    def test_shopping_complete_default(self, test_db, sample_event):
        """Test shopping_complete defaults to False."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.shopping_complete is False
        assert snapshot.shopping_completed_at is None

    def test_mark_shopping_complete(self, test_db, sample_event):
        """Test marking shopping as complete."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        snapshot.shopping_complete = True
        snapshot.shopping_completed_at = utc_now()
        session.commit()

        assert snapshot.shopping_complete is True
        assert snapshot.shopping_completed_at is not None


class TestEventRelationshipAndCascade:
    """Tests for Event-ProductionPlanSnapshot relationship and cascade delete."""

    def test_event_relationship(self, test_db, sample_event):
        """Test that snapshot can access its event."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        # Refresh to ensure relationship is loaded
        session.refresh(snapshot)

        assert snapshot.event is not None
        assert snapshot.event.name == "Christmas 2025"
        assert snapshot.event.id == sample_event.id

    def test_event_has_snapshots_relationship(self, test_db, sample_event):
        """Test that event can access its snapshots."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        # Refresh event to load relationship
        session.refresh(sample_event)

        assert len(sample_event.production_plan_snapshots) == 1
        assert sample_event.production_plan_snapshots[0].id == snapshot.id

    def test_cascade_delete(self, test_db, sample_event):
        """Test that deleting event cascades to delete snapshots."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        snapshot_id = snapshot.id

        # Delete the event
        session.delete(sample_event)
        session.commit()

        # Verify snapshot was cascade deleted
        deleted_snapshot = session.get(ProductionPlanSnapshot, snapshot_id)
        assert deleted_snapshot is None


class TestEventOutputMode:
    """Tests for Event.output_mode enum field."""

    def test_event_output_mode_bundled(self, test_db):
        """Test Event accepts BUNDLED output_mode."""
        session = test_db()

        event = Event(
            name="Bundled Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        session.add(event)
        session.commit()

        assert event.output_mode == OutputMode.BUNDLED
        assert event.output_mode.value == "bundled"

    def test_event_output_mode_bulk_count(self, test_db):
        """Test Event accepts BULK_COUNT output_mode."""
        session = test_db()

        event = Event(
            name="Bulk Count Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.commit()

        assert event.output_mode == OutputMode.BULK_COUNT
        assert event.output_mode.value == "bulk_count"

    def test_event_output_mode_nullable(self, test_db):
        """Test Event output_mode can be None (for existing events)."""
        session = test_db()

        event = Event(
            name="No Mode Event",
            event_date=date(2025, 12, 25),
            year=2025,
            # output_mode not set
        )
        session.add(event)
        session.commit()

        assert event.output_mode is None

    def test_output_mode_enum_values(self):
        """Test OutputMode enum has correct values."""
        assert OutputMode.BUNDLED.value == "bundled"
        assert OutputMode.BULK_COUNT.value == "bulk_count"
        assert len(OutputMode) == 2


class TestProductionPlanSnapshotToDict:
    """Tests for to_dict serialization."""

    def test_to_dict_basic(self, test_db, sample_event):
        """Test to_dict converts snapshot to dictionary."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        result = snapshot.to_dict()

        assert "id" in result
        assert "event_id" in result
        assert "calculated_at" in result
        assert result["shopping_complete"] is False

    def test_to_dict_with_relationships(self, test_db, sample_event):
        """Test to_dict with include_relationships=True."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        # Refresh to load relationships
        session.refresh(snapshot)

        result = snapshot.to_dict(include_relationships=True)

        assert "event_name" in result
        assert result["event_name"] == "Christmas 2025"


class TestProductionPlanSnapshotRepr:
    """Tests for __repr__ method."""

    def test_repr(self, test_db, sample_event):
        """Test __repr__ returns expected string format."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        repr_str = repr(snapshot)

        assert "ProductionPlanSnapshot" in repr_str
        assert f"id={snapshot.id}" in repr_str
        assert f"event_id={sample_event.id}" in repr_str
        assert "calculated_at=" in repr_str
