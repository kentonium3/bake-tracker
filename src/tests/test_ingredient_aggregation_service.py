"""Unit tests for ingredient aggregation service (F074)."""

import pytest
from datetime import date

from src.models import (
    Event,
    Recipe,
    Ingredient,
    RecipeIngredient,
    FinishedUnit,
    BatchDecision,
)
from src.models.finished_unit import YieldMode
from src.services.ingredient_aggregation_service import (
    aggregate_ingredients_for_event,
    IngredientTotal,
)
from src.services.exceptions import ValidationError


@pytest.fixture
def sample_event(test_db):
    """Create a test event."""
    event = Event(name="Test Event", event_date=date(2026, 1, 1), year=2026)
    test_db.add(event)
    test_db.flush()
    return event


@pytest.fixture
def sample_recipe_with_ingredients(test_db):
    """Create a recipe with 2 ingredients."""
    # Create ingredients
    flour = Ingredient(display_name="Flour", slug="flour", category="Dry")
    sugar = Ingredient(display_name="Sugar", slug="sugar", category="Dry")
    test_db.add_all([flour, sugar])
    test_db.flush()

    # Create recipe
    recipe = Recipe(name="Test Cookies", category="Cookies")
    test_db.add(recipe)
    test_db.flush()

    # Add recipe ingredients
    ri_flour = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=flour.id,
        quantity=2.0,
        unit="cups",
    )
    ri_sugar = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=sugar.id,
        quantity=1.0,
        unit="cups",
    )
    test_db.add_all([ri_flour, ri_sugar])
    test_db.flush()

    return recipe, flour, sugar


@pytest.fixture
def sample_finished_unit(test_db, sample_recipe_with_ingredients):
    """Create a FinishedUnit linked to the recipe."""
    recipe, _, _ = sample_recipe_with_ingredients
    fu = FinishedUnit(
        slug="test-cookies",
        display_name="Test Cookies",
        recipe_id=recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookie",
    )
    test_db.add(fu)
    test_db.flush()
    return fu


class TestSingleRecipeAggregation:
    """Tests for single-recipe ingredient aggregation."""

    def test_single_recipe_single_batch(
        self, test_db, sample_event, sample_recipe_with_ingredients, sample_finished_unit
    ):
        """Single batch should return base ingredient quantities."""
        recipe, flour, sugar = sample_recipe_with_ingredients
        fu = sample_finished_unit
        event = sample_event

        # Create batch decision: 1 batch
        bd = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=1,
        )
        test_db.add(bd)
        test_db.flush()

        result = aggregate_ingredients_for_event(event.id, session=test_db)

        assert len(result) == 2
        assert result[(flour.id, "cups")].total_quantity == 2.0
        assert result[(sugar.id, "cups")].total_quantity == 1.0

    def test_single_recipe_multiple_batches(
        self, test_db, sample_event, sample_recipe_with_ingredients, sample_finished_unit
    ):
        """Multiple batches should multiply ingredient quantities."""
        recipe, flour, sugar = sample_recipe_with_ingredients
        fu = sample_finished_unit
        event = sample_event

        # Create batch decision: 3 batches
        bd = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=3,
        )
        test_db.add(bd)
        test_db.flush()

        result = aggregate_ingredients_for_event(event.id, session=test_db)

        assert len(result) == 2
        assert result[(flour.id, "cups")].total_quantity == 6.0  # 2 × 3
        assert result[(sugar.id, "cups")].total_quantity == 3.0  # 1 × 3

    def test_ingredient_total_dataclass_fields(
        self, test_db, sample_event, sample_recipe_with_ingredients, sample_finished_unit
    ):
        """IngredientTotal should have all expected fields."""
        recipe, flour, _ = sample_recipe_with_ingredients
        fu = sample_finished_unit
        event = sample_event

        bd = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=1,
        )
        test_db.add(bd)
        test_db.flush()

        result = aggregate_ingredients_for_event(event.id, session=test_db)
        flour_total = result[(flour.id, "cups")]

        assert flour_total.ingredient_id == flour.id
        assert flour_total.ingredient_name == flour.display_name
        assert flour_total.unit == "cups"
        assert flour_total.total_quantity == 2.0

    def test_event_not_found_raises_error(self, test_db):
        """Non-existent event should raise ValidationError."""
        with pytest.raises(ValidationError):
            aggregate_ingredients_for_event(99999, session=test_db)

    def test_empty_event_returns_empty_dict(self, test_db, sample_event):
        """Event with no batch decisions should return empty dict."""
        result = aggregate_ingredients_for_event(sample_event.id, session=test_db)
        assert result == {}
