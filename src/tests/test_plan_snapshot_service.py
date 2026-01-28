"""Unit tests for plan_snapshot_service.

Feature 078: Plan Snapshots & Amendments
"""

import pytest
from datetime import datetime

from src.models import Event, EventRecipe, EventFinishedGood, BatchDecision, Recipe, FinishedGood
from src.models import PlanSnapshot
from src.models.event import PlanState
from src.services import plan_snapshot_service


class TestCreatePlanSnapshot:
    """Tests for create_plan_snapshot function."""

    def test_creates_snapshot_with_empty_plan(self, test_db):
        """Event with no recipes/FGs still gets valid snapshot."""
        session = test_db()

        event = Event(
            name="Empty Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        snapshot = plan_snapshot_service.create_plan_snapshot(event.id, session)

        assert snapshot is not None
        assert snapshot.event_id == event.id
        assert snapshot.snapshot_data["snapshot_version"] == "1.0"
        assert snapshot.snapshot_data["recipes"] == []
        assert snapshot.snapshot_data["finished_goods"] == []
        assert snapshot.snapshot_data["batch_decisions"] == []
        assert "created_at" in snapshot.snapshot_data

    def test_idempotent_returns_existing_snapshot(self, test_db):
        """Calling create twice returns same snapshot."""
        session = test_db()

        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        snapshot1 = plan_snapshot_service.create_plan_snapshot(event.id, session)
        snapshot2 = plan_snapshot_service.create_plan_snapshot(event.id, session)

        assert snapshot1.id == snapshot2.id

    def test_raises_error_for_missing_event(self, test_db):
        """Raises ValidationError when event doesn't exist."""
        session = test_db()

        from src.services.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            plan_snapshot_service.create_plan_snapshot(99999, session)

        assert "Event 99999 not found" in str(exc_info.value)

    def test_snapshot_json_structure(self, test_db):
        """Snapshot has correct JSON structure."""
        session = test_db()

        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        snapshot = plan_snapshot_service.create_plan_snapshot(event.id, session)

        # Verify structure
        data = snapshot.snapshot_data
        assert "snapshot_version" in data
        assert data["snapshot_version"] == "1.0"
        assert "created_at" in data
        assert "recipes" in data
        assert "finished_goods" in data
        assert "batch_decisions" in data
        assert isinstance(data["recipes"], list)
        assert isinstance(data["finished_goods"], list)
        assert isinstance(data["batch_decisions"], list)


class TestGetPlanSnapshot:
    """Tests for get_plan_snapshot function."""

    def test_returns_snapshot_when_exists(self, test_db):
        """Returns snapshot for event that has one."""
        session = test_db()

        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        created = plan_snapshot_service.create_plan_snapshot(event.id, session)
        retrieved = plan_snapshot_service.get_plan_snapshot(event.id, session)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_returns_none_when_no_snapshot(self, test_db):
        """Returns None for event without snapshot."""
        session = test_db()

        event = Event(
            name="No Snapshot Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        result = plan_snapshot_service.get_plan_snapshot(event.id, session)

        assert result is None


class TestStartProductionIntegration:
    """Integration tests for start_production with snapshot creation."""

    def test_start_production_creates_snapshot(self, test_db):
        """start_production creates snapshot before state change."""
        from src.services import plan_state_service

        session = test_db()

        # Create LOCKED event
        event = Event(
            name="Production Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.LOCKED,
        )
        session.add(event)
        session.flush()
        event_id = event.id

        # Start production
        result = plan_state_service.start_production(event_id, session)

        # Verify state changed
        assert result.plan_state == PlanState.IN_PRODUCTION

        # Verify snapshot created
        snapshot = plan_snapshot_service.get_plan_snapshot(event_id, session)
        assert snapshot is not None
        assert snapshot.event_id == event_id

    def test_start_production_with_recipes_and_fgs(self, test_db):
        """start_production creates snapshot containing recipes and finished goods."""
        from src.models import Recipe, Ingredient, FinishedGood
        from src.services import plan_state_service

        session = test_db()

        # Create prerequisite data
        ingredient = Ingredient(
            display_name="Test Flour",
            slug="test-flour",
            category="Flour",
        )
        session.add(ingredient)
        session.flush()

        recipe = Recipe(
            name="Test Cookies",
            category="Cookies",
        )
        session.add(recipe)
        session.flush()

        finished_good = FinishedGood(
            display_name="Test Gift Box",
            slug="test-gift-box",
        )
        session.add(finished_good)
        session.flush()

        # Create event with plan data
        event = Event(
            name="Production Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.LOCKED,
        )
        session.add(event)
        session.flush()

        # Add event recipe
        event_recipe = EventRecipe(
            event_id=event.id,
            recipe_id=recipe.id,
        )
        session.add(event_recipe)

        # Add event finished good
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=finished_good.id,
            quantity=10,
        )
        session.add(event_fg)
        session.flush()

        event_id = event.id

        # Start production
        result = plan_state_service.start_production(event_id, session)

        # Verify snapshot contains the data
        snapshot = plan_snapshot_service.get_plan_snapshot(event_id, session)
        assert snapshot is not None

        data = snapshot.snapshot_data
        assert len(data["recipes"]) == 1
        assert data["recipes"][0]["recipe_name"] == "Test Cookies"

        assert len(data["finished_goods"]) == 1
        assert data["finished_goods"][0]["fg_name"] == "Test Gift Box"
        assert data["finished_goods"][0]["quantity"] == 10

        # No batch decisions in this test (requires full FinishedUnit setup)
        assert len(data["batch_decisions"]) == 0
