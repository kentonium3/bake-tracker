"""Unit tests for plan_amendment_service.

Feature 078: Plan Snapshots & Amendments
Feature 079 WP04: Amendment Production Validation
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models import (
    Event,
    EventFinishedGood,
    BatchDecision,
    FinishedGood,
    Recipe,
    FinishedUnit,
    Composition,
    ProductionRun,
)
from src.models.event import PlanState
from src.models.plan_amendment import AmendmentType
from src.services import plan_amendment_service
from src.services.plan_amendment_service import (
    _has_production_for_recipe,
    _get_recipes_for_finished_good,
)
from src.services.exceptions import ValidationError, PlanStateError


class TestAmendmentValidation:
    """Tests for amendment validation rules."""

    def test_rejects_amendment_when_not_in_production(self, test_db):
        """Amendments require IN_PRODUCTION state."""
        session = test_db()

        event = Event(
            name="Draft Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.DRAFT,
        )
        session.add(event)
        session.flush()

        with pytest.raises(PlanStateError):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": 1},
                "test reason",
                session
            )

    def test_rejects_amendment_when_locked(self, test_db):
        """Amendments require IN_PRODUCTION state, not LOCKED."""
        session = test_db()

        event = Event(
            name="Locked Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.LOCKED,
        )
        session.add(event)
        session.flush()

        with pytest.raises(PlanStateError):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": 1},
                "test reason",
                session
            )

    def test_rejects_amendment_with_empty_reason(self, test_db):
        """Amendments require non-empty reason."""
        session = test_db()

        event = Event(
            name="In Production",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": 1},
                "",  # Empty reason
                session
            )

    def test_rejects_amendment_with_whitespace_only_reason(self, test_db):
        """Amendments require non-whitespace reason."""
        session = test_db()

        event = Event(
            name="In Production",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": 1},
                "   ",  # Whitespace only
                session
            )


class TestDropFinishedGood:
    """Tests for drop_finished_good function."""

    def test_drops_fg_and_creates_amendment(self, test_db):
        """Successfully drops FG and records amendment."""
        session = test_db()

        # Create FG
        fg = FinishedGood(
            display_name="Test Gift Box",
            slug="test-gift-box",
        )
        session.add(fg)
        session.flush()

        # Create event
        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG to event
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg.id,
            quantity=10,
        )
        session.add(event_fg)
        session.flush()

        # Drop
        amendment = plan_amendment_service.drop_finished_good(
            event.id, fg.id, "Not needed", session
        )

        # Verify amendment
        assert amendment.amendment_type == AmendmentType.DROP_FG
        assert amendment.amendment_data["fg_id"] == fg.id
        assert amendment.amendment_data["original_quantity"] == 10
        assert amendment.reason == "Not needed"

        # Verify EventFinishedGood deleted
        remaining = session.query(EventFinishedGood).filter(
            EventFinishedGood.event_id == event.id,
            EventFinishedGood.finished_good_id == fg.id,
        ).first()
        assert remaining is None

    def test_rejects_drop_when_fg_not_in_plan(self, test_db):
        """Cannot drop FG that's not in plan."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.drop_finished_good(
                event.id, 99999, "Test", session
            )
        assert "not in event plan" in str(exc_info.value)


class TestAddFinishedGood:
    """Tests for add_finished_good function."""

    def test_adds_fg_and_creates_amendment(self, test_db):
        """Successfully adds FG and records amendment."""
        session = test_db()

        # Create FG
        fg = FinishedGood(
            display_name="New Gift Box",
            slug="new-gift-box",
        )
        session.add(fg)
        session.flush()

        # Create event
        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG via amendment
        amendment = plan_amendment_service.add_finished_good(
            event.id, fg.id, 5, "Adding more", session
        )

        assert amendment.amendment_type == AmendmentType.ADD_FG
        assert amendment.amendment_data["quantity"] == 5
        assert amendment.amendment_data["fg_name"] == "New Gift Box"

        # Verify EventFinishedGood created
        event_fg = session.query(EventFinishedGood).filter(
            EventFinishedGood.event_id == event.id,
            EventFinishedGood.finished_good_id == fg.id,
        ).first()
        assert event_fg is not None
        assert event_fg.quantity == 5

    def test_rejects_add_when_fg_already_in_plan(self, test_db):
        """Cannot add FG that's already in plan."""
        session = test_db()

        # Create FG
        fg = FinishedGood(
            display_name="Existing Gift Box",
            slug="existing-gift-box",
        )
        session.add(fg)
        session.flush()

        # Create event
        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG first time directly
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg.id,
            quantity=10,
        )
        session.add(event_fg)
        session.flush()

        # Try to add again via amendment
        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.add_finished_good(
                event.id, fg.id, 5, "Duplicate", session
            )
        assert "already in event plan" in str(exc_info.value)

    def test_rejects_add_when_fg_not_found(self, test_db):
        """Cannot add FG that doesn't exist."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.add_finished_good(
                event.id, 99999, 5, "Ghost FG", session
            )
        assert "not found" in str(exc_info.value)

    def test_rejects_add_with_zero_quantity(self, test_db):
        """Cannot add FG with zero quantity."""
        session = test_db()

        fg = FinishedGood(
            display_name="Test Box",
            slug="test-box",
        )
        session.add(fg)
        session.flush()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.add_finished_good(
                event.id, fg.id, 0, "Zero quantity", session
            )
        assert "positive" in str(exc_info.value)


class TestModifyBatchDecision:
    """Tests for modify_batch_decision function."""

    def test_modifies_batch_and_creates_amendment(self, test_db):
        """Successfully modifies batch count and records amendment."""
        session = test_db()

        # Create recipe
        recipe = Recipe(
            name="Test Cookies",
            category="Cookies",
        )
        session.add(recipe)
        session.flush()

        # Create event
        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create FinishedUnit (requires recipe_id)
        from src.models import FinishedUnit

        finished_unit = FinishedUnit(
            display_name="Cookie",
            slug="cookie-test",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(finished_unit)
        session.flush()

        batch_decision = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=finished_unit.id,
            batches=5,
        )
        session.add(batch_decision)
        session.flush()

        # Modify batch
        amendment = plan_amendment_service.modify_batch_decision(
            event.id, recipe.id, 8, "Need more", session
        )

        assert amendment.amendment_type == AmendmentType.MODIFY_BATCH
        assert amendment.amendment_data["old_batches"] == 5
        assert amendment.amendment_data["new_batches"] == 8
        assert amendment.amendment_data["recipe_name"] == "Test Cookies"

        # Verify BatchDecision updated
        session.refresh(batch_decision)
        assert batch_decision.batches == 8

    def test_rejects_modify_when_no_batch_decision(self, test_db):
        """Cannot modify batch for recipe without batch decision."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.modify_batch_decision(
                event.id, 99999, 10, "No batch", session
            )
        assert "No batch decision" in str(exc_info.value)

    def test_rejects_negative_batch_count(self, test_db):
        """Cannot set negative batch count."""
        session = test_db()

        # Create recipe
        recipe = Recipe(
            name="Test Recipe Neg",
            category="Test",
        )
        session.add(recipe)
        session.flush()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create FinishedUnit (requires recipe_id)
        from src.models import FinishedUnit

        finished_unit = FinishedUnit(
            display_name="Test Unit Neg",
            slug="test-unit-neg",
            recipe_id=recipe.id,
            items_per_batch=12,
            item_unit="unit",
        )
        session.add(finished_unit)
        session.flush()

        batch_decision = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=finished_unit.id,
            batches=5,
        )
        session.add(batch_decision)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.modify_batch_decision(
                event.id, recipe.id, -1, "Negative", session
            )
        assert "cannot be negative" in str(exc_info.value)


class TestGetAmendments:
    """Tests for get_amendments function."""

    def test_returns_amendments_in_chronological_order(self, test_db):
        """Amendments returned oldest first."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create multiple amendments
        for i in range(3):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": i},
                f"Reason {i}",
                session
            )

        amendments = plan_amendment_service.get_amendments(event.id, session)

        assert len(amendments) == 3
        # Verify chronological order
        for i in range(len(amendments) - 1):
            assert amendments[i].created_at <= amendments[i + 1].created_at

    def test_returns_empty_list_when_no_amendments(self, test_db):
        """Returns empty list for event with no amendments."""
        session = test_db()

        event = Event(
            name="No Amendments",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        amendments = plan_amendment_service.get_amendments(event.id, session)
        assert amendments == []

    def test_amendments_contain_correct_data(self, test_db):
        """Amendment data is accessible."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        plan_amendment_service.create_amendment(
            event.id,
            AmendmentType.DROP_FG,
            {"fg_id": 123, "fg_name": "Test Box"},
            "Testing data",
            session
        )

        amendments = plan_amendment_service.get_amendments(event.id, session)

        assert len(amendments) == 1
        assert amendments[0].amendment_type == AmendmentType.DROP_FG
        assert amendments[0].amendment_data["fg_id"] == 123
        assert amendments[0].amendment_data["fg_name"] == "Test Box"
        assert amendments[0].reason == "Testing data"


# =============================================================================
# F079 WP04: Amendment Production Validation Tests
# =============================================================================


class TestHasProductionForRecipe:
    """Tests for _has_production_for_recipe helper."""

    def test_returns_true_when_production_exists(self, test_db):
        """Should return True when production run exists for recipe in event."""
        session = test_db()

        # Create recipe
        recipe = Recipe(name="Test Recipe", category="Test")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Test FU",
            slug="test-fu",
            recipe_id=recipe.id,
            items_per_batch=12,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create production run
        production_run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            event_id=event.id,
            num_batches=2,
            expected_yield=24,
            actual_yield=24,
            total_ingredient_cost=Decimal("10.00"),
            per_unit_cost=Decimal("0.4167"),
        )
        session.add(production_run)
        session.flush()

        # Test
        result = _has_production_for_recipe(event.id, recipe.id, session)
        assert result is True

    def test_returns_false_when_no_production(self, test_db):
        """Should return False when no production run exists."""
        session = test_db()

        # Create recipe
        recipe = Recipe(name="Test Recipe", category="Test")
        session.add(recipe)
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Test (no production run created)
        result = _has_production_for_recipe(event.id, recipe.id, session)
        assert result is False

    def test_returns_false_for_different_event(self, test_db):
        """Production in one event should not affect another."""
        session = test_db()

        # Create recipe
        recipe = Recipe(name="Test Recipe", category="Test")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Test FU",
            slug="test-fu",
            recipe_id=recipe.id,
            items_per_batch=12,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create two events
        event1 = Event(
            name="Event 1",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        event2 = Event(
            name="Event 2",
            event_date=datetime(2026, 12, 26).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add_all([event1, event2])
        session.flush()

        # Create production run for event1 only
        production_run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            event_id=event1.id,
            num_batches=2,
            expected_yield=24,
            actual_yield=24,
            total_ingredient_cost=Decimal("10.00"),
            per_unit_cost=Decimal("0.4167"),
        )
        session.add(production_run)
        session.flush()

        # Test - event1 has production, event2 does not
        assert _has_production_for_recipe(event1.id, recipe.id, session) is True
        assert _has_production_for_recipe(event2.id, recipe.id, session) is False


class TestGetRecipesForFinishedGood:
    """Tests for _get_recipes_for_finished_good helper."""

    def test_returns_recipe_ids_from_composition(self, test_db):
        """Should return recipe IDs from FG's FinishedUnit components."""
        session = test_db()

        # Create recipe
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Sugar Cookie",
            slug="sugar-cookie",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create finished good
        fg = FinishedGood(
            display_name="Cookie Box",
            slug="cookie-box",
        )
        session.add(fg)
        session.flush()

        # Create composition linking FG to FU
        composition = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu.id,
            component_quantity=6,
        )
        session.add(composition)
        session.flush()

        # Test
        recipe_ids = _get_recipes_for_finished_good(fg.id, session)
        assert len(recipe_ids) == 1
        assert recipe.id in recipe_ids

    def test_returns_multiple_recipe_ids(self, test_db):
        """Should return all recipe IDs when FG has multiple FU components."""
        session = test_db()

        # Create two recipes
        recipe1 = Recipe(name="Recipe 1", category="Cookies")
        recipe2 = Recipe(name="Recipe 2", category="Brownies")
        session.add_all([recipe1, recipe2])
        session.flush()

        # Create finished units
        fu1 = FinishedUnit(
            display_name="Cookie",
            slug="test-cookie",
            recipe_id=recipe1.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        fu2 = FinishedUnit(
            display_name="Brownie",
            slug="test-brownie",
            recipe_id=recipe2.id,
            items_per_batch=16,
            item_unit="brownie",
        )
        session.add_all([fu1, fu2])
        session.flush()

        # Create finished good
        fg = FinishedGood(
            display_name="Variety Box",
            slug="variety-box",
        )
        session.add(fg)
        session.flush()

        # Create compositions
        comp1 = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu1.id,
            component_quantity=3,
        )
        comp2 = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu2.id,
            component_quantity=2,
        )
        session.add_all([comp1, comp2])
        session.flush()

        # Test
        recipe_ids = _get_recipes_for_finished_good(fg.id, session)
        assert len(recipe_ids) == 2
        assert recipe1.id in recipe_ids
        assert recipe2.id in recipe_ids

    def test_returns_empty_for_fg_without_fu_components(self, test_db):
        """FG with no FinishedUnit components returns empty list."""
        session = test_db()

        # Create finished good with no compositions
        fg = FinishedGood(
            display_name="Empty Box",
            slug="empty-box",
        )
        session.add(fg)
        session.flush()

        # Test
        recipe_ids = _get_recipes_for_finished_good(fg.id, session)
        assert recipe_ids == []


class TestAmendmentProductionValidation:
    """Tests for blocking amendments when production exists."""

    def test_modify_batch_blocked_when_production_exists(self, test_db):
        """
        Given: Recipe has ProductionRun records
        When: modify_batch_decision() called
        Then: ValidationError raised with clear message
        """
        session = test_db()

        # Create recipe
        recipe = Recipe(name="Test Cookies", category="Cookies")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Cookie",
            slug="test-cookie-prod",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create batch decision
        batch_decision = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=5,
        )
        session.add(batch_decision)
        session.flush()

        # Create production run
        production_run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            event_id=event.id,
            num_batches=2,
            expected_yield=48,
            actual_yield=48,
            total_ingredient_cost=Decimal("10.00"),
            per_unit_cost=Decimal("0.2083"),
        )
        session.add(production_run)
        session.flush()

        # Test - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.modify_batch_decision(
                event.id,
                recipe.id,
                new_batches=10,
                reason="Increase production",
                session=session,
            )

        assert "Cannot modify batch decision" in str(exc_info.value)
        assert recipe.name in str(exc_info.value)
        assert "production has already been recorded" in str(exc_info.value)

    def test_modify_batch_allowed_when_no_production(self, test_db):
        """
        Given: Recipe has no ProductionRun records
        When: modify_batch_decision() called
        Then: Amendment succeeds
        """
        session = test_db()

        # Create recipe
        recipe = Recipe(name="Test Cookies No Prod", category="Cookies")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Cookie No Prod",
            slug="test-cookie-no-prod",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create batch decision
        batch_decision = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=5,
        )
        session.add(batch_decision)
        session.flush()

        # Test - should succeed (no production exists)
        amendment = plan_amendment_service.modify_batch_decision(
            event.id,
            recipe.id,
            new_batches=10,
            reason="Increase production",
            session=session,
        )

        assert amendment is not None
        assert amendment.amendment_type == AmendmentType.MODIFY_BATCH
        assert amendment.amendment_data["old_batches"] == 5
        assert amendment.amendment_data["new_batches"] == 10

    def test_drop_fg_blocked_when_contributing_recipe_has_production(self, test_db):
        """
        Given: FG's contributing recipe has ProductionRun records
        When: drop_finished_good() called
        Then: ValidationError raised listing the recipe
        """
        session = test_db()

        # Create recipe
        recipe = Recipe(name="Gift Box Cookies", category="Cookies")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Cookie for Box",
            slug="cookie-for-box",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create finished good
        fg = FinishedGood(
            display_name="Gift Box",
            slug="gift-box-prod",
        )
        session.add(fg)
        session.flush()

        # Create composition
        composition = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu.id,
            component_quantity=6,
        )
        session.add(composition)
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG to event plan
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg.id,
            quantity=10,
        )
        session.add(event_fg)
        session.flush()

        # Create production run
        production_run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            event_id=event.id,
            num_batches=3,
            expected_yield=72,
            actual_yield=72,
            total_ingredient_cost=Decimal("15.00"),
            per_unit_cost=Decimal("0.2083"),
        )
        session.add(production_run)
        session.flush()

        # Test - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.drop_finished_good(
                event.id,
                fg.id,
                reason="No longer needed",
                session=session,
            )

        assert "Cannot drop finished good" in str(exc_info.value)
        assert fg.display_name in str(exc_info.value)
        assert recipe.name in str(exc_info.value)

    def test_drop_fg_allowed_when_no_production(self, test_db):
        """
        Given: FG's contributing recipes have no production
        When: drop_finished_good() called
        Then: Amendment succeeds
        """
        session = test_db()

        # Create recipe
        recipe = Recipe(name="No Prod Cookies", category="Cookies")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Cookie No Prod FG",
            slug="cookie-no-prod-fg",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create finished good
        fg = FinishedGood(
            display_name="Gift Box No Prod",
            slug="gift-box-no-prod",
        )
        session.add(fg)
        session.flush()

        # Create composition
        composition = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu.id,
            component_quantity=6,
        )
        session.add(composition)
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG to event plan
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg.id,
            quantity=10,
        )
        session.add(event_fg)
        session.flush()

        # Test - should succeed (no production exists)
        amendment = plan_amendment_service.drop_finished_good(
            event.id,
            fg.id,
            reason="No longer needed",
            session=session,
        )

        assert amendment is not None
        assert amendment.amendment_type == AmendmentType.DROP_FG
        assert amendment.amendment_data["fg_id"] == fg.id
        assert amendment.amendment_data["original_quantity"] == 10

    def test_add_fg_not_blocked_by_production(self, test_db):
        """ADD_FG should not be blocked by existing production."""
        session = test_db()

        # Create recipe
        recipe = Recipe(name="Existing Cookies", category="Cookies")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Existing Cookie",
            slug="existing-cookie",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create finished good to be added
        fg = FinishedGood(
            display_name="New Box",
            slug="new-box",
        )
        session.add(fg)
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create production run for existing recipe
        production_run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            event_id=event.id,
            num_batches=2,
            expected_yield=48,
            actual_yield=48,
            total_ingredient_cost=Decimal("10.00"),
            per_unit_cost=Decimal("0.2083"),
        )
        session.add(production_run)
        session.flush()

        # Test - ADD_FG should succeed regardless of production
        amendment = plan_amendment_service.add_finished_good(
            event.id,
            fg.id,
            quantity=5,
            reason="Adding new item",
            session=session,
        )

        assert amendment is not None
        assert amendment.amendment_type == AmendmentType.ADD_FG

    def test_error_message_includes_recipe_name(self, test_db):
        """Error messages should include recipe name for clarity."""
        session = test_db()

        # Create recipe with distinctive name
        recipe = Recipe(name="Grandma's Special Cookies", category="Cookies")
        session.add(recipe)
        session.flush()

        # Create finished unit
        fu = FinishedUnit(
            display_name="Special Cookie",
            slug="special-cookie",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(fu)
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create batch decision
        batch_decision = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=5,
        )
        session.add(batch_decision)
        session.flush()

        # Create production run
        production_run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            event_id=event.id,
            num_batches=1,
            expected_yield=24,
            actual_yield=24,
            total_ingredient_cost=Decimal("5.00"),
            per_unit_cost=Decimal("0.2083"),
        )
        session.add(production_run)
        session.flush()

        # Test - error message should include recipe name
        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.modify_batch_decision(
                event.id,
                recipe.id,
                new_batches=10,
                reason="Test",
                session=session,
            )

        # Recipe name should be in the error
        assert "Grandma's Special Cookies" in str(exc_info.value)

    def test_drop_fg_with_multiple_recipes_shows_all_blocked(self, test_db):
        """DROP_FG error should list all recipes with production."""
        session = test_db()

        # Create two recipes
        recipe1 = Recipe(name="Cookie Recipe", category="Cookies")
        recipe2 = Recipe(name="Brownie Recipe", category="Brownies")
        session.add_all([recipe1, recipe2])
        session.flush()

        # Create finished units
        fu1 = FinishedUnit(
            display_name="Multi Cookie",
            slug="multi-cookie",
            recipe_id=recipe1.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        fu2 = FinishedUnit(
            display_name="Multi Brownie",
            slug="multi-brownie",
            recipe_id=recipe2.id,
            items_per_batch=16,
            item_unit="brownie",
        )
        session.add_all([fu1, fu2])
        session.flush()

        # Create finished good
        fg = FinishedGood(
            display_name="Variety Box Multi",
            slug="variety-box-multi",
        )
        session.add(fg)
        session.flush()

        # Create compositions
        comp1 = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu1.id,
            component_quantity=3,
        )
        comp2 = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu2.id,
            component_quantity=2,
        )
        session.add_all([comp1, comp2])
        session.flush()

        # Create event
        event = Event(
            name="Test Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG to event plan
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg.id,
            quantity=10,
        )
        session.add(event_fg)
        session.flush()

        # Create production runs for BOTH recipes
        prod1 = ProductionRun(
            recipe_id=recipe1.id,
            finished_unit_id=fu1.id,
            event_id=event.id,
            num_batches=2,
            expected_yield=48,
            actual_yield=48,
            total_ingredient_cost=Decimal("10.00"),
            per_unit_cost=Decimal("0.2083"),
        )
        prod2 = ProductionRun(
            recipe_id=recipe2.id,
            finished_unit_id=fu2.id,
            event_id=event.id,
            num_batches=2,
            expected_yield=32,
            actual_yield=32,
            total_ingredient_cost=Decimal("8.00"),
            per_unit_cost=Decimal("0.25"),
        )
        session.add_all([prod1, prod2])
        session.flush()

        # Test - error message should list both recipes
        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.drop_finished_good(
                event.id,
                fg.id,
                reason="Test",
                session=session,
            )

        error_msg = str(exc_info.value)
        assert "Cookie Recipe" in error_msg
        assert "Brownie Recipe" in error_msg
