"""Integration tests for plan state modification guards (F077).

Tests verify that modification guards correctly block operations
based on event plan state.

WP02: Modification Guards
- T006: Guard set_event_recipes()
- T007: Guard set_event_fg_quantities()
- T008: Guard save_batch_decisions()
- T009: Integration tests
"""

import pytest
from datetime import date

from src.models.event import Event, PlanState
from src.models.recipe import Recipe
from src.models.finished_good import FinishedGood
from src.models.finished_unit import FinishedUnit
from src.models.composition import Composition
from src.services.database import session_scope
from src.services.event_service import (
    set_event_recipes,
    set_event_fg_quantities,
)
from src.services.batch_decision_service import (
    save_batch_decision,
    delete_batch_decisions,
    BatchDecisionInput,
)
from src.services.plan_state_service import (
    lock_plan,
    start_production,
    complete_production,
)
from src.services.exceptions import PlanStateError


@pytest.fixture
def event_with_recipe(test_db):
    """Create an event with a recipe and finished good in DRAFT state.

    Sets up the full chain needed for FG selection:
    Recipe -> FinishedUnit -> Composition -> FinishedGood
    """
    with session_scope() as session:
        # Create a minimal recipe
        recipe = Recipe(
            name="Test Recipe",
            category="Test Category",
        )
        session.add(recipe)
        session.flush()
        recipe_id = recipe.id

        # Create a finished unit based on this recipe
        finished_unit = FinishedUnit(
            display_name="Test FU",
            slug="test_fu",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="piece",
        )
        session.add(finished_unit)
        session.flush()
        fu_id = finished_unit.id

        # Create a finished good
        finished_good = FinishedGood(
            display_name="Test FG",
            slug="test_fg",
        )
        session.add(finished_good)
        session.flush()
        fg_id = finished_good.id

        # Create composition linking FG to FU
        composition = Composition(
            assembly_id=fg_id,
            finished_unit_id=fu_id,
            component_quantity=1,
        )
        session.add(composition)

        # Create event in DRAFT state
        event = Event(
            name="Test Event",
            event_date=date(2026, 12, 25),
            year=2026,
            plan_state=PlanState.DRAFT,
        )
        session.add(event)
        session.flush()
        event_id = event.id

    return {
        "event_id": event_id,
        "recipe_id": recipe_id,
        "finished_unit_id": fu_id,
        "finished_good_id": fg_id,
    }


class TestRecipeGuards:
    """Tests for set_event_recipes() guard (T006)."""

    def test_draft_allows_modification(self, event_with_recipe):
        """DRAFT state should allow recipe modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        with session_scope() as session:
            count, _ = set_event_recipes(session, event_id, [recipe_id])
            assert count >= 0  # No error raised

    def test_locked_blocks_modification(self, event_with_recipe):
        """LOCKED state should block recipe modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

        assert "recipes" in str(exc_info.value).lower()
        assert exc_info.value.current_state == PlanState.LOCKED

    def test_in_production_blocks_modification(self, event_with_recipe):
        """IN_PRODUCTION state should block recipe modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)
        start_production(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

        assert exc_info.value.current_state == PlanState.IN_PRODUCTION

    def test_completed_blocks_modification(self, event_with_recipe):
        """COMPLETED state should block recipe modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)
        start_production(event_id)
        complete_production(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

        assert exc_info.value.current_state == PlanState.COMPLETED


class TestFGGuards:
    """Tests for set_event_fg_quantities() guard (T007)."""

    def test_draft_allows_modification(self, event_with_recipe):
        """DRAFT state should allow FG modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]
        fg_id = event_with_recipe["finished_good_id"]

        # First add recipe to make FG available
        with session_scope() as session:
            set_event_recipes(session, event_id, [recipe_id])

        # Now set FG quantities - should work in DRAFT
        with session_scope() as session:
            count = set_event_fg_quantities(session, event_id, [(fg_id, 10)])
            assert count >= 0  # No error raised

    def test_locked_blocks_modification(self, event_with_recipe):
        """LOCKED state should block FG modifications."""
        event_id = event_with_recipe["event_id"]
        fg_id = event_with_recipe["finished_good_id"]

        lock_plan(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_fg_quantities(session, event_id, [(fg_id, 10)])

        assert "finished goods" in str(exc_info.value).lower()
        assert exc_info.value.current_state == PlanState.LOCKED

    def test_in_production_blocks_modification(self, event_with_recipe):
        """IN_PRODUCTION state should block FG modifications."""
        event_id = event_with_recipe["event_id"]
        fg_id = event_with_recipe["finished_good_id"]

        lock_plan(event_id)
        start_production(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_fg_quantities(session, event_id, [(fg_id, 10)])

        assert exc_info.value.current_state == PlanState.IN_PRODUCTION

    def test_completed_blocks_modification(self, event_with_recipe):
        """COMPLETED state should block FG modifications."""
        event_id = event_with_recipe["event_id"]
        fg_id = event_with_recipe["finished_good_id"]

        lock_plan(event_id)
        start_production(event_id)
        complete_production(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_fg_quantities(session, event_id, [(fg_id, 10)])

        assert exc_info.value.current_state == PlanState.COMPLETED


class TestBatchDecisionGuards:
    """Tests for save_batch_decision() guard (T008)."""

    def test_draft_allows_modification(self, event_with_recipe):
        """DRAFT state should allow batch decision modifications."""
        event_id = event_with_recipe["event_id"]
        fu_id = event_with_recipe["finished_unit_id"]

        decision = BatchDecisionInput(
            finished_unit_id=fu_id,
            batches=2,
            is_shortfall=False,
        )
        result = save_batch_decision(event_id, decision)
        assert result.batches == 2

    def test_locked_allows_modification(self, event_with_recipe):
        """LOCKED state should allow batch decision modifications."""
        event_id = event_with_recipe["event_id"]
        fu_id = event_with_recipe["finished_unit_id"]

        lock_plan(event_id)

        decision = BatchDecisionInput(
            finished_unit_id=fu_id,
            batches=3,
            is_shortfall=False,
        )
        result = save_batch_decision(event_id, decision)
        assert result.batches == 3

    def test_in_production_blocks_modification(self, event_with_recipe):
        """IN_PRODUCTION state should block batch decision modifications."""
        event_id = event_with_recipe["event_id"]
        fu_id = event_with_recipe["finished_unit_id"]

        lock_plan(event_id)
        start_production(event_id)

        decision = BatchDecisionInput(
            finished_unit_id=fu_id,
            batches=2,
            is_shortfall=False,
        )

        with pytest.raises(PlanStateError) as exc_info:
            save_batch_decision(event_id, decision)

        assert "batch decisions" in str(exc_info.value).lower()
        assert exc_info.value.current_state == PlanState.IN_PRODUCTION

    def test_completed_blocks_modification(self, event_with_recipe):
        """COMPLETED state should block batch decision modifications."""
        event_id = event_with_recipe["event_id"]
        fu_id = event_with_recipe["finished_unit_id"]

        lock_plan(event_id)
        start_production(event_id)
        complete_production(event_id)

        decision = BatchDecisionInput(
            finished_unit_id=fu_id,
            batches=2,
            is_shortfall=False,
        )

        with pytest.raises(PlanStateError) as exc_info:
            save_batch_decision(event_id, decision)

        assert exc_info.value.current_state == PlanState.COMPLETED


class TestDeleteBatchDecisionGuards:
    """Tests for delete_batch_decisions() guard."""

    def test_draft_allows_delete(self, event_with_recipe):
        """DRAFT state should allow deleting batch decisions."""
        event_id = event_with_recipe["event_id"]

        # Should not raise
        count = delete_batch_decisions(event_id)
        assert count >= 0

    def test_locked_allows_delete(self, event_with_recipe):
        """LOCKED state should allow deleting batch decisions."""
        event_id = event_with_recipe["event_id"]

        lock_plan(event_id)

        # Should not raise
        count = delete_batch_decisions(event_id)
        assert count >= 0

    def test_in_production_blocks_delete(self, event_with_recipe):
        """IN_PRODUCTION state should block deleting batch decisions."""
        event_id = event_with_recipe["event_id"]

        lock_plan(event_id)
        start_production(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            delete_batch_decisions(event_id)

        assert exc_info.value.current_state == PlanState.IN_PRODUCTION

    def test_completed_blocks_delete(self, event_with_recipe):
        """COMPLETED state should block deleting batch decisions."""
        event_id = event_with_recipe["event_id"]

        lock_plan(event_id)
        start_production(event_id)
        complete_production(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            delete_batch_decisions(event_id)

        assert exc_info.value.current_state == PlanState.COMPLETED


class TestPlanStateErrorAttributes:
    """Test that PlanStateError has correct attributes for UI display."""

    def test_error_has_event_id(self, event_with_recipe):
        """Exception should include event_id."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

        assert exc_info.value.event_id == event_id

    def test_error_has_current_state(self, event_with_recipe):
        """Exception should include current_state."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

        assert exc_info.value.current_state == PlanState.LOCKED

    def test_error_has_attempted_action(self, event_with_recipe):
        """Exception should include attempted_action."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

        assert "recipes" in exc_info.value.attempted_action

    def test_error_message_is_user_friendly(self, event_with_recipe):
        """Exception message should be user-friendly for UI display."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

        message = str(exc_info.value)
        # Should be readable text
        assert "Cannot" in message
        assert "locked" in message
