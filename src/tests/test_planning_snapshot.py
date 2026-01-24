"""
Unit tests for PlanningSnapshot model and service functions.

Feature 064: FinishedGoods Snapshot Architecture

Tests cover:
- create_planning_snapshot(): container creation with optional event linkage
- get_planning_snapshot(): retrieval with aggregated snapshots
- get_planning_snapshots_by_event(): query by event
- delete_planning_snapshot(): cascade deletion to child snapshots
"""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models import (
    Event,
    Recipe,
    FinishedUnit,
    FinishedUnitSnapshot,
    PlanningSnapshot,
)
from src.models.finished_unit import YieldMode
from src.services.planning_snapshot_service import (
    create_planning_snapshot,
    get_planning_snapshot,
    get_planning_snapshots_by_event,
    delete_planning_snapshot,
    PlanningSnapshotError,
)
from src.services.finished_unit_service import create_finished_unit_snapshot
from src.services import database


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session.

    This fixture creates an in-memory database for each test,
    ensuring tests are isolated. It also patches the global
    session factory so services use the test database.
    """
    from sqlalchemy import event as sa_event

    # Create in-memory database with FK support
    engine = create_engine("sqlite:///:memory:")

    # Enable foreign key support for SQLite (required for CASCADE)
    @sa_event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    # Create session factory with expire_on_commit=False
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    # Patch the global session factory
    original_get_session = database.get_session
    database._session_factory = Session

    def patched_get_session():
        return Session()

    database.get_session = patched_get_session

    # Create a session for the test
    session = Session()

    yield session

    # Cleanup
    session.close()
    database.get_session = original_get_session


@pytest.fixture
def sample_event(db_session):
    """Create a test event."""
    event = Event(
        name="Test Holiday Event",
        event_date=date(2025, 12, 25),
        year=2025,
        notes="Test event notes",
    )
    db_session.add(event)
    db_session.flush()
    return event


@pytest.fixture
def sample_recipe(db_session):
    """Create a test recipe."""
    recipe = Recipe(
        name="Test Cookie Recipe",
        category="Cookies",
        source="Test",
    )
    db_session.add(recipe)
    db_session.flush()
    return recipe


@pytest.fixture
def sample_finished_unit(db_session, sample_recipe):
    """Create a test FinishedUnit."""
    fu = FinishedUnit(
        slug="test-cookie",
        display_name="Test Cookie",
        description="A delicious test cookie",
        recipe_id=sample_recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookie",
        category="Cookies",
    )
    db_session.add(fu)
    db_session.flush()
    db_session.commit()
    return fu


# ============================================================================
# Tests: create_planning_snapshot()
# ============================================================================


class TestCreatePlanningSnapshot:
    """Tests for create_planning_snapshot()."""

    def test_creates_without_event(self, db_session):
        """Can create standalone planning snapshot without event linkage."""
        result = create_planning_snapshot(session=db_session)

        assert result["id"] is not None
        assert result["event_id"] is None
        assert result["notes"] is None
        assert "created_at" in result

    def test_creates_with_event(self, db_session, sample_event):
        """Can create planning snapshot linked to event."""
        result = create_planning_snapshot(
            event_id=sample_event.id,
            notes="Test planning notes",
            session=db_session,
        )

        assert result["event_id"] == sample_event.id
        assert result["notes"] == "Test planning notes"

    def test_snapshot_persisted_to_database(self, db_session):
        """Snapshot is actually persisted and queryable."""
        result = create_planning_snapshot(
            notes="Persisted snapshot",
            session=db_session,
        )
        db_session.commit()

        # Query directly from database
        snapshot = (
            db_session.query(PlanningSnapshot)
            .filter_by(id=result["id"])
            .first()
        )

        assert snapshot is not None
        assert snapshot.notes == "Persisted snapshot"


# ============================================================================
# Tests: get_planning_snapshot()
# ============================================================================


class TestGetPlanningSnapshot:
    """Tests for get_planning_snapshot()."""

    def test_returns_snapshot_by_id(self, db_session, sample_event):
        """Can retrieve planning snapshot by ID."""
        created = create_planning_snapshot(
            event_id=sample_event.id,
            notes="Test snapshot",
            session=db_session,
        )

        result = get_planning_snapshot(created["id"], session=db_session)

        assert result is not None
        assert result["id"] == created["id"]
        assert result["event_id"] == sample_event.id
        assert result["notes"] == "Test snapshot"

    def test_returns_none_for_invalid_id(self, db_session):
        """Returns None for non-existent snapshot."""
        result = get_planning_snapshot(99999, session=db_session)
        assert result is None

    def test_returns_empty_snapshot_lists_initially(self, db_session):
        """New planning snapshot has empty snapshot lists."""
        created = create_planning_snapshot(session=db_session)

        result = get_planning_snapshot(
            created["id"],
            include_snapshots=True,
            session=db_session,
        )

        assert result["finished_unit_snapshots"] == []
        assert result["material_unit_snapshots"] == []
        assert result["finished_good_snapshots"] == []
        assert result["total_snapshots"] == 0

    def test_aggregates_linked_finished_unit_snapshots(
        self, db_session, sample_finished_unit
    ):
        """Aggregates FinishedUnitSnapshots linked to planning snapshot."""
        # Create planning snapshot
        ps = create_planning_snapshot(session=db_session)

        # Create linked FinishedUnitSnapshot
        fu_snap = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            planning_snapshot_id=ps["id"],
            session=db_session,
        )

        # Retrieve with snapshots
        result = get_planning_snapshot(
            ps["id"],
            include_snapshots=True,
            session=db_session,
        )

        assert result is not None
        assert len(result["finished_unit_snapshots"]) == 1
        assert result["finished_unit_snapshots"][0]["id"] == fu_snap["id"]
        assert result["total_snapshots"] == 1

    def test_excludes_snapshots_when_flag_is_false(self, db_session, sample_finished_unit):
        """Can retrieve without loading snapshot details."""
        # Create planning snapshot with linked snapshot
        ps = create_planning_snapshot(session=db_session)
        create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            planning_snapshot_id=ps["id"],
            session=db_session,
        )

        # Retrieve without snapshot details
        result = get_planning_snapshot(
            ps["id"],
            include_snapshots=False,
            session=db_session,
        )

        assert result is not None
        assert "finished_unit_snapshots" not in result
        assert "total_snapshots" not in result


# ============================================================================
# Tests: get_planning_snapshots_by_event()
# ============================================================================


class TestGetPlanningSnapshotsByEvent:
    """Tests for get_planning_snapshots_by_event()."""

    def test_returns_empty_list_for_no_matches(self, db_session, sample_event):
        """Returns empty list when event has no planning snapshots."""
        result = get_planning_snapshots_by_event(
            event_id=sample_event.id,
            session=db_session,
        )

        assert result == []

    def test_returns_all_snapshots_for_event(self, db_session, sample_event):
        """Returns all planning snapshots for an event."""
        # Create multiple planning snapshots for same event
        ps1 = create_planning_snapshot(
            event_id=sample_event.id,
            notes="First snapshot",
            session=db_session,
        )
        ps2 = create_planning_snapshot(
            event_id=sample_event.id,
            notes="Second snapshot",
            session=db_session,
        )

        result = get_planning_snapshots_by_event(
            event_id=sample_event.id,
            session=db_session,
        )

        assert len(result) == 2
        snapshot_ids = {s["id"] for s in result}
        assert ps1["id"] in snapshot_ids
        assert ps2["id"] in snapshot_ids

    def test_excludes_snapshots_from_other_events(self, db_session):
        """Does not include snapshots from other events."""
        # Create two events
        event1 = Event(name="Event 1", event_date=date(2025, 12, 25), year=2025)
        event2 = Event(name="Event 2", event_date=date(2025, 12, 26), year=2025)
        db_session.add(event1)
        db_session.add(event2)
        db_session.flush()

        # Create snapshot for each event
        ps1 = create_planning_snapshot(event_id=event1.id, session=db_session)
        create_planning_snapshot(event_id=event2.id, session=db_session)

        # Query for event1 only
        result = get_planning_snapshots_by_event(
            event_id=event1.id,
            session=db_session,
        )

        assert len(result) == 1
        assert result[0]["id"] == ps1["id"]


# ============================================================================
# Tests: delete_planning_snapshot()
# ============================================================================


class TestDeletePlanningSnapshot:
    """Tests for delete_planning_snapshot()."""

    def test_deletes_planning_snapshot(self, db_session):
        """Can delete a planning snapshot."""
        ps = create_planning_snapshot(
            notes="To be deleted",
            session=db_session,
        )

        result = delete_planning_snapshot(ps["id"], session=db_session)

        assert result is True

        # Verify deletion
        assert get_planning_snapshot(ps["id"], session=db_session) is None

    def test_returns_false_for_invalid_id(self, db_session):
        """Returns False for non-existent ID."""
        result = delete_planning_snapshot(99999, session=db_session)
        assert result is False

    def test_cascades_to_finished_unit_snapshots(self, db_session, sample_finished_unit):
        """Deleting PlanningSnapshot deletes linked FinishedUnitSnapshots."""
        # Create planning snapshot with linked FinishedUnitSnapshot
        ps = create_planning_snapshot(session=db_session)
        fu_snap = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            planning_snapshot_id=ps["id"],
            session=db_session,
        )
        db_session.commit()

        # Verify snapshot exists before deletion
        from src.services.finished_unit_service import get_finished_unit_snapshot
        assert get_finished_unit_snapshot(fu_snap["id"], session=db_session) is not None

        # Delete planning snapshot
        result = delete_planning_snapshot(ps["id"], session=db_session)
        db_session.commit()

        assert result is True

        # Verify child snapshot is gone (cascade delete)
        assert get_finished_unit_snapshot(fu_snap["id"], session=db_session) is None

    def test_does_not_delete_unrelated_snapshots(
        self, db_session, sample_finished_unit
    ):
        """Deleting PlanningSnapshot does not affect unrelated snapshots."""
        # Create two planning snapshots
        ps1 = create_planning_snapshot(session=db_session)
        ps2 = create_planning_snapshot(session=db_session)

        # Create snapshots linked to each
        fu_snap1 = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            planning_snapshot_id=ps1["id"],
            session=db_session,
        )
        fu_snap2 = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            planning_snapshot_id=ps2["id"],
            session=db_session,
        )
        db_session.commit()

        # Delete first planning snapshot
        delete_planning_snapshot(ps1["id"], session=db_session)
        db_session.commit()

        # Verify first is gone, second remains
        from src.services.finished_unit_service import get_finished_unit_snapshot
        assert get_finished_unit_snapshot(fu_snap1["id"], session=db_session) is None
        assert get_finished_unit_snapshot(fu_snap2["id"], session=db_session) is not None


# ============================================================================
# Tests: Model behavior
# ============================================================================


class TestPlanningSnapshotModel:
    """Tests for PlanningSnapshot model methods and relationships."""

    def test_repr(self, db_session, sample_event):
        """Model's __repr__ method works correctly."""
        ps = create_planning_snapshot(
            event_id=sample_event.id,
            session=db_session,
        )

        snapshot = db_session.query(PlanningSnapshot).filter_by(id=ps["id"]).first()
        repr_str = repr(snapshot)

        assert "PlanningSnapshot" in repr_str
        assert str(snapshot.id) in repr_str
        assert str(sample_event.id) in repr_str

    def test_event_relationship_bidirectional(self, db_session, sample_event):
        """Event and PlanningSnapshot have bidirectional relationship."""
        ps = create_planning_snapshot(
            event_id=sample_event.id,
            session=db_session,
        )
        db_session.commit()

        # Refresh event to load relationships
        db_session.refresh(sample_event)

        # Access planning_snapshots from event side
        planning_snapshots = list(sample_event.planning_snapshots)
        assert len(planning_snapshots) == 1
        assert planning_snapshots[0].id == ps["id"]

        # Access event from planning_snapshot side
        snapshot = db_session.query(PlanningSnapshot).filter_by(id=ps["id"]).first()
        assert snapshot.event.id == sample_event.id

    def test_event_deletion_sets_null(self, db_session):
        """Event deletion sets planning_snapshot.event_id to NULL (not deleted)."""
        # Create event and linked planning snapshot
        event = Event(name="Deletable Event", event_date=date(2025, 12, 25), year=2025)
        db_session.add(event)
        db_session.flush()

        ps = create_planning_snapshot(
            event_id=event.id,
            notes="Should survive event deletion",
            session=db_session,
        )
        db_session.commit()

        ps_id = ps["id"]

        # Delete the event
        db_session.delete(event)
        db_session.commit()

        # Verify planning snapshot still exists with NULL event_id
        snapshot = db_session.query(PlanningSnapshot).filter_by(id=ps_id).first()
        assert snapshot is not None
        assert snapshot.event_id is None
        assert snapshot.notes == "Should survive event deletion"
