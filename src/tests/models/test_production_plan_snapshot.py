"""
Unit tests for ProductionPlanSnapshot model (Feature 039).

Tests cover:
- ProductionPlanSnapshot creation and JSON storage
- Helper methods for extracting calculation results
- Staleness marking and clearing
- Event relationship and cascade delete
- Event.output_mode enum values
"""

import json
from datetime import datetime, date, timedelta
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


@pytest.fixture
def sample_calculation_results():
    """Provide sample calculation results JSON structure."""
    return {
        "recipe_batches": [
            {
                "recipe_id": 1,
                "recipe_name": "Chocolate Chip Cookies",
                "units_needed": 300,
                "batches": 7,
                "yield_per_batch": 48,
                "total_yield": 336,
                "waste_units": 36,
                "waste_percent": 10.7,
            },
            {
                "recipe_id": 2,
                "recipe_name": "Fudge Brownies",
                "units_needed": 150,
                "batches": 7,
                "yield_per_batch": 24,
                "total_yield": 168,
                "waste_units": 18,
                "waste_percent": 10.7,
            },
        ],
        "aggregated_ingredients": [
            {
                "ingredient_id": 1,
                "ingredient_slug": "all-purpose-flour",
                "ingredient_name": "All-Purpose Flour",
                "total_quantity": 14.0,
                "unit": "cups",
            },
            {
                "ingredient_id": 2,
                "ingredient_slug": "butter",
                "ingredient_name": "Butter",
                "total_quantity": 7.0,
                "unit": "cups",
            },
        ],
        "shopping_list": [
            {
                "ingredient_slug": "all-purpose-flour",
                "ingredient_name": "All-Purpose Flour",
                "needed": 14.0,
                "in_stock": 10.0,
                "to_buy": 4.0,
                "unit": "cups",
            },
            {
                "ingredient_slug": "butter",
                "ingredient_name": "Butter",
                "needed": 7.0,
                "in_stock": 8.0,
                "to_buy": 0.0,
                "unit": "cups",
            },
        ],
    }


class TestCreateProductionPlanSnapshot:
    """Tests for basic ProductionPlanSnapshot creation."""

    def test_create_snapshot_with_valid_data(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test creating a production plan snapshot with valid data."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.id is not None
        assert snapshot.event_id == sample_event.id
        assert snapshot.calculated_at == now
        assert snapshot.is_stale is False
        assert snapshot.shopping_complete is False
        assert snapshot.calculation_results == sample_calculation_results

    def test_create_snapshot_with_input_hash(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test creating snapshot with optional input hash."""
        session = test_db()

        now = utc_now()
        input_hash = "abc123def456" * 5 + "abcd"  # 64 char hash

        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            input_hash=input_hash,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.input_hash == input_hash

    def test_snapshot_requires_event(
        self, test_db, sample_calculation_results
    ):
        """Test that snapshot requires a valid event_id."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=99999,  # Non-existent event
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)

        with pytest.raises(IntegrityError):
            session.commit()


class TestProductionPlanSnapshotHelperMethods:
    """Tests for helper methods that extract data from calculation_results."""

    def test_get_recipe_batches(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test get_recipe_batches extracts recipe batch data."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        batches = snapshot.get_recipe_batches()

        assert len(batches) == 2
        assert batches[0]["recipe_name"] == "Chocolate Chip Cookies"
        assert batches[0]["batches"] == 7
        assert batches[1]["recipe_name"] == "Fudge Brownies"
        assert batches[1]["units_needed"] == 150

    def test_get_shopping_list(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test get_shopping_list extracts shopping list data."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        shopping = snapshot.get_shopping_list()

        assert len(shopping) == 2
        assert shopping[0]["ingredient_slug"] == "all-purpose-flour"
        assert shopping[0]["to_buy"] == 4.0
        assert shopping[1]["to_buy"] == 0.0  # Butter is sufficient

    def test_get_aggregated_ingredients(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test get_aggregated_ingredients extracts ingredient data."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        ingredients = snapshot.get_aggregated_ingredients()

        assert len(ingredients) == 2
        assert ingredients[0]["ingredient_name"] == "All-Purpose Flour"
        assert ingredients[0]["total_quantity"] == 14.0

    def test_get_methods_with_empty_results(self, test_db, sample_event):
        """Test helper methods return empty lists when calculation_results is empty."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results={},  # Empty results
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.get_recipe_batches() == []
        assert snapshot.get_shopping_list() == []
        assert snapshot.get_aggregated_ingredients() == []


class TestProductionPlanSnapshotStaleness:
    """Tests for staleness marking and clearing."""

    def test_mark_stale(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test mark_stale sets is_stale and stale_reason."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.is_stale is False
        assert snapshot.stale_reason is None

        snapshot.mark_stale("Recipe 'Chocolate Chip Cookies' modified")
        session.commit()

        assert snapshot.is_stale is True
        assert snapshot.stale_reason == "Recipe 'Chocolate Chip Cookies' modified"

    def test_mark_fresh(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test mark_fresh clears is_stale and stale_reason."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
            is_stale=True,
            stale_reason="Previous modification",
        )
        session.add(snapshot)
        session.commit()

        snapshot.mark_fresh()
        session.commit()

        assert snapshot.is_stale is False
        assert snapshot.stale_reason is None


class TestProductionPlanSnapshotShoppingStatus:
    """Tests for shopping completion tracking."""

    def test_shopping_complete_default(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test shopping_complete defaults to False."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.shopping_complete is False
        assert snapshot.shopping_completed_at is None

    def test_mark_shopping_complete(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test marking shopping as complete."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
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

    def test_event_relationship(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test that snapshot can access its event."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        # Refresh to ensure relationship is loaded
        session.refresh(snapshot)

        assert snapshot.event is not None
        assert snapshot.event.name == "Christmas 2025"
        assert snapshot.event.id == sample_event.id

    def test_event_has_snapshots_relationship(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test that event can access its snapshots."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        # Refresh event to load relationship
        session.refresh(sample_event)

        assert len(sample_event.production_plan_snapshots) == 1
        assert sample_event.production_plan_snapshots[0].id == snapshot.id

    def test_cascade_delete(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test that deleting event cascades to delete snapshots."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        snapshot_id = snapshot.id
        event_id = sample_event.id

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

    def test_to_dict_basic(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test to_dict converts snapshot to dictionary."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        result = snapshot.to_dict()

        assert "id" in result
        assert "event_id" in result
        assert "calculated_at" in result
        assert "is_stale" in result
        assert result["is_stale"] is False
        assert result["shopping_complete"] is False

    def test_to_dict_with_relationships(
        self, test_db, sample_event, sample_calculation_results
    ):
        """Test to_dict with include_relationships=True."""
        session = test_db()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=sample_event.id,
            calculated_at=now,
            requirements_updated_at=now,
            recipes_updated_at=now,
            bundles_updated_at=now,
            calculation_results=sample_calculation_results,
        )
        session.add(snapshot)
        session.commit()

        # Refresh to load relationships
        session.refresh(snapshot)

        result = snapshot.to_dict(include_relationships=True)

        assert "event_name" in result
        assert result["event_name"] == "Christmas 2025"
