"""
Tests for F079 Production-Aware Planning Calculations - Remaining Needs.

Tests cover:
- ProductionProgress DTO remaining_batches and overage_batches fields
- get_remaining_production_needs() helper function
- Edge cases: partial completion, exact completion, overage, zero target
"""

from datetime import date

import pytest

from src.models import Event, EventProductionTarget, FinishedUnit, ProductionRun, Recipe
from src.services.planning.progress import (
    get_production_progress,
    get_remaining_production_needs,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def progress_event(test_db):
    """Create a test event for progress tests."""
    event = Event(
        name="Progress Test Event",
        event_date=date(2026, 12, 25),
        year=2026,
    )
    test_db.add(event)
    test_db.flush()
    return event


@pytest.fixture
def progress_recipe(test_db):
    """Create a test recipe for production targets."""
    recipe = Recipe(name="Test Cookie Recipe", category="Cookies")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def progress_finished_unit(test_db, progress_recipe):
    """Create a finished unit linked to the progress recipe."""
    fu = FinishedUnit(
        slug="test-cookies-batch",
        display_name="Test Cookies (batch)",
        recipe_id=progress_recipe.id,
        items_per_batch=10,
        inventory_count=0,
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def event_with_partial_production(test_db, progress_event, progress_recipe, progress_finished_unit):
    """Create event with 5 target batches, 3 completed."""
    # Create production target
    target = EventProductionTarget(
        event_id=progress_event.id,
        recipe_id=progress_recipe.id,
        target_batches=5,
    )
    test_db.add(target)

    # Create production run (3 batches completed)
    run = ProductionRun(
        event_id=progress_event.id,
        recipe_id=progress_recipe.id,
        finished_unit_id=progress_finished_unit.id,
        num_batches=3,
        expected_yield=30,
        actual_yield=30,
    )
    test_db.add(run)
    test_db.commit()

    return progress_event


@pytest.fixture
def event_with_exact_completion(test_db, progress_event, progress_recipe, progress_finished_unit):
    """Create event with 5 target batches, 5 completed."""
    target = EventProductionTarget(
        event_id=progress_event.id,
        recipe_id=progress_recipe.id,
        target_batches=5,
    )
    test_db.add(target)

    run = ProductionRun(
        event_id=progress_event.id,
        recipe_id=progress_recipe.id,
        finished_unit_id=progress_finished_unit.id,
        num_batches=5,
        expected_yield=50,
        actual_yield=50,
    )
    test_db.add(run)
    test_db.commit()

    return progress_event


@pytest.fixture
def event_with_overage(test_db, progress_event, progress_recipe, progress_finished_unit):
    """Create event with 5 target batches, 7 completed (overage)."""
    target = EventProductionTarget(
        event_id=progress_event.id,
        recipe_id=progress_recipe.id,
        target_batches=5,
    )
    test_db.add(target)

    run = ProductionRun(
        event_id=progress_event.id,
        recipe_id=progress_recipe.id,
        finished_unit_id=progress_finished_unit.id,
        num_batches=7,
        expected_yield=70,
        actual_yield=70,
    )
    test_db.add(run)
    test_db.commit()

    return progress_event


@pytest.fixture
def event_with_no_production(test_db, progress_event, progress_recipe, progress_finished_unit):
    """Create event with 5 target batches, 0 completed."""
    target = EventProductionTarget(
        event_id=progress_event.id,
        recipe_id=progress_recipe.id,
        target_batches=5,
    )
    test_db.add(target)
    test_db.commit()

    return progress_event


@pytest.fixture
def event_with_multiple_recipes(test_db, progress_event):
    """Create event with multiple recipes at different progress levels."""
    # Recipe 1: partial completion
    recipe1 = Recipe(name="Cookie Recipe", category="Cookies")
    test_db.add(recipe1)
    test_db.flush()

    fu1 = FinishedUnit(
        slug="cookie-batch",
        display_name="Cookie Batch",
        recipe_id=recipe1.id,
        items_per_batch=10,
        inventory_count=0,
    )
    test_db.add(fu1)
    test_db.flush()

    target1 = EventProductionTarget(
        event_id=progress_event.id,
        recipe_id=recipe1.id,
        target_batches=10,
    )
    test_db.add(target1)

    run1 = ProductionRun(
        event_id=progress_event.id,
        recipe_id=recipe1.id,
        finished_unit_id=fu1.id,
        num_batches=3,
        expected_yield=30,
        actual_yield=30,
    )
    test_db.add(run1)

    # Recipe 2: complete
    recipe2 = Recipe(name="Brownie Recipe", category="Brownies")
    test_db.add(recipe2)
    test_db.flush()

    fu2 = FinishedUnit(
        slug="brownie-batch",
        display_name="Brownie Batch",
        recipe_id=recipe2.id,
        items_per_batch=10,
        inventory_count=0,
    )
    test_db.add(fu2)
    test_db.flush()

    target2 = EventProductionTarget(
        event_id=progress_event.id,
        recipe_id=recipe2.id,
        target_batches=5,
    )
    test_db.add(target2)

    run2 = ProductionRun(
        event_id=progress_event.id,
        recipe_id=recipe2.id,
        finished_unit_id=fu2.id,
        num_batches=5,
        expected_yield=50,
        actual_yield=50,
    )
    test_db.add(run2)

    # Recipe 3: overage
    recipe3 = Recipe(name="Fudge Recipe", category="Fudge")
    test_db.add(recipe3)
    test_db.flush()

    fu3 = FinishedUnit(
        slug="fudge-batch",
        display_name="Fudge Batch",
        recipe_id=recipe3.id,
        items_per_batch=10,
        inventory_count=0,
    )
    test_db.add(fu3)
    test_db.flush()

    target3 = EventProductionTarget(
        event_id=progress_event.id,
        recipe_id=recipe3.id,
        target_batches=4,
    )
    test_db.add(target3)

    run3 = ProductionRun(
        event_id=progress_event.id,
        recipe_id=recipe3.id,
        finished_unit_id=fu3.id,
        num_batches=6,
        expected_yield=60,
        actual_yield=60,
    )
    test_db.add(run3)

    test_db.commit()

    return {
        "event": progress_event,
        "recipe1": recipe1,  # 10 target, 3 completed, 7 remaining
        "recipe2": recipe2,  # 5 target, 5 completed, 0 remaining
        "recipe3": recipe3,  # 4 target, 6 completed, 0 remaining, 2 overage
    }


# ============================================================================
# Tests for ProductionProgress DTO Fields
# ============================================================================


class TestRemainingBatchesCalculation:
    """Tests for remaining_batches and overage_batches calculation."""

    def test_partial_completion_shows_remaining(
        self, test_db, event_with_partial_production, progress_recipe
    ):
        """Given 5 target batches and 3 completed, remaining should be 2."""
        progress = get_production_progress(
            event_with_partial_production.id, session=test_db
        )

        assert len(progress) == 1
        recipe_progress = progress[0]

        assert recipe_progress.target_batches == 5
        assert recipe_progress.completed_batches == 3
        assert recipe_progress.remaining_batches == 2
        assert recipe_progress.overage_batches == 0
        assert recipe_progress.is_complete is False

    def test_exact_completion_shows_zero_remaining(
        self, test_db, event_with_exact_completion, progress_recipe
    ):
        """Given 5 target and 5 completed, remaining should be 0."""
        progress = get_production_progress(
            event_with_exact_completion.id, session=test_db
        )

        assert len(progress) == 1
        recipe_progress = progress[0]

        assert recipe_progress.target_batches == 5
        assert recipe_progress.completed_batches == 5
        assert recipe_progress.remaining_batches == 0
        assert recipe_progress.overage_batches == 0
        assert recipe_progress.is_complete is True

    def test_overage_shows_zero_remaining_with_overage_count(
        self, test_db, event_with_overage, progress_recipe
    ):
        """Given 5 target and 7 completed, remaining=0 and overage=2."""
        progress = get_production_progress(event_with_overage.id, session=test_db)

        assert len(progress) == 1
        recipe_progress = progress[0]

        assert recipe_progress.target_batches == 5
        assert recipe_progress.completed_batches == 7
        assert recipe_progress.remaining_batches == 0  # Never negative
        assert recipe_progress.overage_batches == 2
        assert recipe_progress.is_complete is True

    def test_no_production_shows_full_remaining(
        self, test_db, event_with_no_production, progress_recipe
    ):
        """Given 5 target and 0 completed, remaining equals target."""
        progress = get_production_progress(
            event_with_no_production.id, session=test_db
        )

        assert len(progress) == 1
        recipe_progress = progress[0]

        assert recipe_progress.target_batches == 5
        assert recipe_progress.completed_batches == 0
        assert recipe_progress.remaining_batches == 5
        assert recipe_progress.overage_batches == 0
        assert recipe_progress.is_complete is False

class TestGetRemainingProductionNeeds:
    """Tests for get_remaining_production_needs() helper function."""

    def test_returns_dict_of_recipe_id_to_remaining(
        self, test_db, event_with_partial_production, progress_recipe
    ):
        """Function returns {recipe_id: remaining_batches} dict."""
        needs = get_remaining_production_needs(
            event_with_partial_production.id, session=test_db
        )

        assert isinstance(needs, dict)
        assert progress_recipe.id in needs
        assert needs[progress_recipe.id] == 2  # 5 target - 3 completed

    def test_multiple_recipes_returns_all(self, test_db, event_with_multiple_recipes):
        """All recipes in event are included in result with correct remaining."""
        data = event_with_multiple_recipes
        needs = get_remaining_production_needs(data["event"].id, session=test_db)

        assert len(needs) == 3

        # Recipe 1: 10 target, 3 completed = 7 remaining
        assert needs[data["recipe1"].id] == 7

        # Recipe 2: 5 target, 5 completed = 0 remaining
        assert needs[data["recipe2"].id] == 0

        # Recipe 3: 4 target, 6 completed = 0 remaining (overage doesn't count)
        assert needs[data["recipe3"].id] == 0

    def test_empty_event_returns_empty_dict(self, test_db, progress_event):
        """Event with no production targets returns empty dict."""
        needs = get_remaining_production_needs(progress_event.id, session=test_db)

        assert needs == {}

    def test_all_values_are_integers(self, test_db, event_with_multiple_recipes):
        """All remaining values should be integers."""
        data = event_with_multiple_recipes
        needs = get_remaining_production_needs(data["event"].id, session=test_db)

        assert all(isinstance(v, int) for v in needs.values())

    def test_no_negative_values(self, test_db, event_with_overage, progress_recipe):
        """Remaining should never be negative even with overage."""
        needs = get_remaining_production_needs(event_with_overage.id, session=test_db)

        assert needs[progress_recipe.id] == 0  # Not negative
        assert all(v >= 0 for v in needs.values())


class TestProgressPercentWithNewFields:
    """Ensure progress_percent still works correctly with new fields."""

    def test_progress_percent_partial(
        self, test_db, event_with_partial_production, progress_recipe
    ):
        """Progress percent should be 60% for 3 of 5 batches."""
        progress = get_production_progress(
            event_with_partial_production.id, session=test_db
        )

        assert progress[0].progress_percent == 60.0

    def test_progress_percent_overage(
        self, test_db, event_with_overage, progress_recipe
    ):
        """Progress percent should exceed 100% for overage."""
        progress = get_production_progress(event_with_overage.id, session=test_db)

        assert progress[0].progress_percent == 140.0  # 7/5 * 100
