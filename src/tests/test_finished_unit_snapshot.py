"""
Unit tests for FinishedUnitSnapshot model and service functions.

Feature 064: FinishedGoods Snapshot Architecture

Tests cover:
- create_finished_unit_snapshot(): snapshot creation with all fields
- get_finished_unit_snapshot(): snapshot retrieval by ID
- get_finished_unit_snapshots_by_planning_id(): query by planning context
- Error handling for invalid IDs
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models import Recipe, FinishedUnit, FinishedUnitSnapshot, PlanningSnapshot
from src.models.finished_unit import YieldMode
from src.services.finished_unit_service import (
    create_finished_unit_snapshot,
    get_finished_unit_snapshot,
    get_finished_unit_snapshots_by_planning_id,
    SnapshotCreationError,
)
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
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
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
    """Create a test FinishedUnit with all fields populated."""
    fu = FinishedUnit(
        slug="test-cookie",
        display_name="Test Cookie",
        description="A delicious test cookie",
        recipe_id=sample_recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookie",
        category="Cookies",
        production_notes="Cool on wire rack",
        notes="Best served warm",
    )
    db_session.add(fu)
    db_session.flush()
    db_session.commit()
    return fu


@pytest.fixture
def sample_batch_portion_unit(db_session, sample_recipe):
    """Create a test FinishedUnit with BATCH_PORTION yield mode."""
    fu = FinishedUnit(
        slug="test-cake",
        display_name="Test Cake",
        description="A test cake",
        recipe_id=sample_recipe.id,
        yield_mode=YieldMode.BATCH_PORTION,
        batch_percentage=50.0,
        portion_description="9-inch round pan",
        category="Cakes",
    )
    db_session.add(fu)
    db_session.flush()
    db_session.commit()
    return fu


# ============================================================================
# Tests: create_finished_unit_snapshot()
# ============================================================================


class TestCreateFinishedUnitSnapshot:
    """Tests for create_finished_unit_snapshot()."""

    def test_creates_snapshot_with_all_fields(self, db_session, sample_finished_unit):
        """Snapshot captures all FinishedUnit fields."""
        result = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            session=db_session,
        )

        assert result["id"] is not None
        assert result["finished_unit_id"] == sample_finished_unit.id
        assert result["planning_snapshot_id"] is None
        assert result["assembly_run_id"] is None
        assert result["is_backfilled"] is False
        assert "snapshot_date" in result

        # Verify definition_data captures all fields
        data = result["definition_data"]
        assert data["slug"] == "test-cookie"
        assert data["display_name"] == "Test Cookie"
        assert data["description"] == "A delicious test cookie"
        assert data["recipe_id"] == sample_finished_unit.recipe_id
        assert data["recipe_name"] == "Test Cookie Recipe"
        assert data["recipe_category"] == "Cookies"
        assert data["yield_mode"] == "discrete_count"
        assert data["items_per_batch"] == 24
        assert data["item_unit"] == "cookie"
        assert data["batch_percentage"] is None
        assert data["portion_description"] is None
        assert data["category"] == "Cookies"
        assert data["production_notes"] == "Cool on wire rack"
        assert data["notes"] == "Best served warm"

    def test_creates_snapshot_with_batch_portion_mode(
        self, db_session, sample_batch_portion_unit
    ):
        """Snapshot captures BATCH_PORTION fields correctly."""
        result = create_finished_unit_snapshot(
            finished_unit_id=sample_batch_portion_unit.id,
            session=db_session,
        )

        data = result["definition_data"]
        assert data["yield_mode"] == "batch_portion"
        assert data["batch_percentage"] == 50.0
        assert data["portion_description"] == "9-inch round pan"
        assert data["items_per_batch"] is None
        assert data["item_unit"] is None

    def test_raises_error_for_invalid_id(self, db_session):
        """Raises SnapshotCreationError for non-existent FinishedUnit."""
        with pytest.raises(SnapshotCreationError) as exc_info:
            create_finished_unit_snapshot(
                finished_unit_id=99999,
                session=db_session,
            )

        assert "not found" in str(exc_info.value)

    def test_accepts_nullable_context_ids(self, db_session, sample_finished_unit):
        """Snapshot can be created with null context IDs."""
        result = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            planning_snapshot_id=None,
            assembly_run_id=None,
            session=db_session,
        )

        assert result["planning_snapshot_id"] is None
        assert result["assembly_run_id"] is None

    def test_snapshot_persisted_to_database(self, db_session, sample_finished_unit):
        """Snapshot is actually persisted and queryable."""
        result = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            session=db_session,
        )
        db_session.commit()

        # Query directly from database
        snapshot = (
            db_session.query(FinishedUnitSnapshot)
            .filter_by(id=result["id"])
            .first()
        )

        assert snapshot is not None
        assert snapshot.finished_unit_id == sample_finished_unit.id
        assert snapshot.is_backfilled is False


# ============================================================================
# Tests: get_finished_unit_snapshot()
# ============================================================================


class TestGetFinishedUnitSnapshot:
    """Tests for get_finished_unit_snapshot()."""

    def test_returns_snapshot_by_id(self, db_session, sample_finished_unit):
        """Can retrieve snapshot by ID."""
        created = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            session=db_session,
        )

        result = get_finished_unit_snapshot(created["id"], session=db_session)

        assert result is not None
        assert result["id"] == created["id"]
        assert result["finished_unit_id"] == sample_finished_unit.id
        assert result["definition_data"]["slug"] == "test-cookie"
        assert result["definition_data"]["display_name"] == "Test Cookie"

    def test_returns_none_for_invalid_id(self, db_session):
        """Returns None for non-existent snapshot."""
        result = get_finished_unit_snapshot(99999, session=db_session)
        assert result is None

    def test_definition_data_parsed_correctly(self, db_session, sample_finished_unit):
        """Definition data is properly parsed from JSON."""
        created = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            session=db_session,
        )

        result = get_finished_unit_snapshot(created["id"], session=db_session)

        # Verify all expected fields are present and properly typed
        data = result["definition_data"]
        assert isinstance(data, dict)
        assert isinstance(data["slug"], str)
        assert isinstance(data["items_per_batch"], int)


# ============================================================================
# Tests: get_finished_unit_snapshots_by_planning_id()
# ============================================================================


class TestGetFinishedUnitSnapshotsByPlanningId:
    """Tests for get_finished_unit_snapshots_by_planning_id()."""

    def test_returns_empty_list_for_no_matches(self, db_session):
        """Returns empty list when no snapshots match."""
        result = get_finished_unit_snapshots_by_planning_id(
            planning_snapshot_id=99999,
            session=db_session,
        )

        assert result == []

    def test_returns_snapshots_for_planning_id(
        self, db_session, sample_finished_unit, sample_batch_portion_unit
    ):
        """Returns all snapshots linked to a planning_snapshot_id."""
        # Create actual PlanningSnapshot records for FK integrity
        ps1 = PlanningSnapshot(notes="Planning snapshot 1")
        ps2 = PlanningSnapshot(notes="Planning snapshot 2")
        db_session.add(ps1)
        db_session.add(ps2)
        db_session.flush()

        # Create two snapshots with same planning_snapshot_id
        snap1 = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            planning_snapshot_id=ps1.id,
            session=db_session,
        )
        snap2 = create_finished_unit_snapshot(
            finished_unit_id=sample_batch_portion_unit.id,
            planning_snapshot_id=ps1.id,
            session=db_session,
        )

        # Create another snapshot with different planning_id
        create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            planning_snapshot_id=ps2.id,  # Different ID
            session=db_session,
        )

        # Query for first planning_id
        result = get_finished_unit_snapshots_by_planning_id(
            planning_snapshot_id=ps1.id,
            session=db_session,
        )

        assert len(result) == 2
        snapshot_ids = {s["id"] for s in result}
        assert snap1["id"] in snapshot_ids
        assert snap2["id"] in snapshot_ids


# ============================================================================
# Tests: Model behavior
# ============================================================================


class TestFinishedUnitSnapshotModel:
    """Tests for FinishedUnitSnapshot model methods."""

    def test_get_definition_data_parses_json(self, db_session, sample_finished_unit):
        """Model's get_definition_data() method parses JSON correctly."""
        create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            session=db_session,
        )

        snapshot = db_session.query(FinishedUnitSnapshot).first()
        data = snapshot.get_definition_data()

        assert isinstance(data, dict)
        assert data["slug"] == "test-cookie"

    def test_get_definition_data_returns_empty_dict_for_invalid_json(self, db_session):
        """Model's get_definition_data() returns empty dict for invalid JSON."""
        # Create snapshot with manually corrupted data
        snapshot = FinishedUnitSnapshot(
            finished_unit_id=1,  # Fake ID for test
            definition_data="not valid json{{{",
        )

        # get_definition_data should handle gracefully
        data = snapshot.get_definition_data()
        assert data == {}

    def test_repr(self, db_session, sample_finished_unit):
        """Model's __repr__ method works correctly."""
        result = create_finished_unit_snapshot(
            finished_unit_id=sample_finished_unit.id,
            session=db_session,
        )

        snapshot = db_session.query(FinishedUnitSnapshot).filter_by(id=result["id"]).first()
        repr_str = repr(snapshot)

        assert "FinishedUnitSnapshot" in repr_str
        assert str(snapshot.id) in repr_str
        assert str(sample_finished_unit.id) in repr_str
