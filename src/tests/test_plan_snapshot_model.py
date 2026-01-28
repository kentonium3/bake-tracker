"""Unit tests for PlanSnapshot model.

Feature 078: Plan Snapshots & Amendments
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.models import Event, PlanSnapshot


class TestPlanSnapshotModel:
    """Tests for PlanSnapshot model."""

    def test_create_snapshot_with_valid_data(self, test_db):
        """Snapshot can be created with valid JSON data."""
        session = test_db()

        # Create event first
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        # Create snapshot
        snapshot_data = {
            "snapshot_version": "1.0",
            "recipes": [],
            "finished_goods": [],
            "batch_decisions": [],
        }
        snapshot = PlanSnapshot(
            event_id=event.id,
            snapshot_data=snapshot_data,
        )
        session.add(snapshot)
        session.flush()

        assert snapshot.id is not None
        assert snapshot.event_id == event.id
        assert snapshot.snapshot_data == snapshot_data
        assert snapshot.created_at is not None

    def test_unique_constraint_prevents_duplicate_snapshots(self, test_db):
        """Only one snapshot allowed per event."""
        session = test_db()

        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        # First snapshot succeeds
        snapshot1 = PlanSnapshot(
            event_id=event.id,
            snapshot_data={"snapshot_version": "1.0"},
        )
        session.add(snapshot1)
        session.flush()

        # Second snapshot should fail
        snapshot2 = PlanSnapshot(
            event_id=event.id,
            snapshot_data={"snapshot_version": "1.0"},
        )
        session.add(snapshot2)

        with pytest.raises(IntegrityError):
            session.flush()

    def test_cascade_delete_removes_snapshot(self, test_db):
        """Deleting event deletes snapshot."""
        session = test_db()

        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        snapshot = PlanSnapshot(
            event_id=event.id,
            snapshot_data={"snapshot_version": "1.0"},
        )
        session.add(snapshot)
        session.flush()
        snapshot_id = snapshot.id

        # Delete event
        session.delete(event)
        session.flush()

        # Snapshot should be gone
        result = (
            session.query(PlanSnapshot)
            .filter(PlanSnapshot.id == snapshot_id)
            .first()
        )
        assert result is None

    def test_event_relationship_bidirectional(self, test_db):
        """Event and snapshot can access each other."""
        session = test_db()

        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        snapshot = PlanSnapshot(
            event_id=event.id,
            snapshot_data={"snapshot_version": "1.0"},
        )
        session.add(snapshot)
        session.flush()

        # Refresh to load relationships
        session.refresh(event)
        session.refresh(snapshot)

        assert event.plan_snapshot == snapshot
        assert snapshot.event == event

    def test_json_data_stored_and_retrieved_correctly(self, test_db):
        """Complex JSON data is stored and retrieved correctly."""
        session = test_db()

        event = Event(
            name="Christmas 2026",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        # Complex snapshot data structure
        snapshot_data = {
            "snapshot_version": "1.0",
            "created_at": "2026-12-01T10:00:00Z",
            "recipes": [
                {
                    "id": 1,
                    "name": "Chocolate Chip Cookies",
                    "batches_planned": 5,
                },
                {
                    "id": 2,
                    "name": "Sugar Cookies",
                    "batches_planned": 3,
                },
            ],
            "finished_goods": [
                {
                    "id": 1,
                    "name": "Cookie Gift Box",
                    "quantity_planned": 50,
                },
            ],
            "batch_decisions": [
                {
                    "recipe_id": 1,
                    "batch_count": 5,
                    "notes": "Extra for testing",
                },
            ],
        }
        snapshot = PlanSnapshot(
            event_id=event.id,
            snapshot_data=snapshot_data,
        )
        session.add(snapshot)
        session.flush()

        # Refresh to get persisted data
        session.refresh(snapshot)

        assert snapshot.snapshot_data["snapshot_version"] == "1.0"
        assert len(snapshot.snapshot_data["recipes"]) == 2
        assert snapshot.snapshot_data["recipes"][0]["name"] == "Chocolate Chip Cookies"
        assert len(snapshot.snapshot_data["finished_goods"]) == 1
        assert len(snapshot.snapshot_data["batch_decisions"]) == 1

    def test_repr_string(self, test_db):
        """Model has correct string representation."""
        session = test_db()

        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        snapshot = PlanSnapshot(
            event_id=event.id,
            snapshot_data={"snapshot_version": "1.0"},
        )
        session.add(snapshot)
        session.flush()

        repr_str = repr(snapshot)
        assert "PlanSnapshot" in repr_str
        assert f"id={snapshot.id}" in repr_str
        assert f"event_id={event.id}" in repr_str

    def test_event_id_required(self, test_db):
        """Event ID is required (non-nullable)."""
        session = test_db()

        # Attempt to create snapshot without event_id
        snapshot = PlanSnapshot(
            event_id=None,
            snapshot_data={"snapshot_version": "1.0"},
        )
        session.add(snapshot)

        with pytest.raises(IntegrityError):
            session.flush()
