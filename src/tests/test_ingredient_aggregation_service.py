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


class TestCrossRecipeAggregation:
    """Tests for cross-recipe ingredient aggregation (WP02 T009)."""

    @pytest.fixture
    def two_recipes_shared_ingredient(self, test_db):
        """Create two recipes sharing flour ingredient."""
        # Shared ingredient
        flour = Ingredient(display_name="Flour", slug="flour", category="Dry")
        # Recipe-specific ingredients
        sugar = Ingredient(display_name="Sugar", slug="sugar", category="Dry")
        butter = Ingredient(display_name="Butter", slug="butter", category="Dairy")
        test_db.add_all([flour, sugar, butter])
        test_db.flush()

        # Recipe 1: Cookies (2 cups flour, 1 cup sugar)
        recipe1 = Recipe(name="Cookies", category="Cookies")
        test_db.add(recipe1)
        test_db.flush()
        test_db.add_all([
            RecipeIngredient(recipe_id=recipe1.id, ingredient_id=flour.id, quantity=2.0, unit="cups"),
            RecipeIngredient(recipe_id=recipe1.id, ingredient_id=sugar.id, quantity=1.0, unit="cups"),
        ])

        # Recipe 2: Bread (3 cups flour, 0.5 cups butter)
        recipe2 = Recipe(name="Bread", category="Bread")
        test_db.add(recipe2)
        test_db.flush()
        test_db.add_all([
            RecipeIngredient(recipe_id=recipe2.id, ingredient_id=flour.id, quantity=3.0, unit="cups"),
            RecipeIngredient(recipe_id=recipe2.id, ingredient_id=butter.id, quantity=0.5, unit="cups"),
        ])
        test_db.flush()

        return recipe1, recipe2, flour, sugar, butter

    def test_same_ingredient_same_unit_combined(
        self, test_db, sample_event, two_recipes_shared_ingredient
    ):
        """Same ingredient + unit from different recipes should combine."""
        recipe1, recipe2, flour, sugar, butter = two_recipes_shared_ingredient
        event = sample_event

        # Create FUs and batch decisions
        fu1 = FinishedUnit(
            slug="test-cookies", display_name="Test Cookies",
            recipe_id=recipe1.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24, item_unit="cookie",
        )
        fu2 = FinishedUnit(
            slug="test-bread", display_name="Test Bread",
            recipe_id=recipe2.id, yield_mode=YieldMode.BATCH_PORTION,
            batch_percentage=100,
        )
        test_db.add_all([fu1, fu2])
        test_db.flush()

        # 2 batches each
        test_db.add_all([
            BatchDecision(event_id=event.id, recipe_id=recipe1.id, finished_unit_id=fu1.id, batches=2),
            BatchDecision(event_id=event.id, recipe_id=recipe2.id, finished_unit_id=fu2.id, batches=2),
        ])
        test_db.flush()

        result = aggregate_ingredients_for_event(event.id, session=test_db)

        # Flour: (2 cups × 2) + (3 cups × 2) = 10 cups
        assert result[(flour.id, "cups")].total_quantity == 10.0
        # Sugar: 1 cup × 2 = 2 cups (only in recipe1)
        assert result[(sugar.id, "cups")].total_quantity == 2.0
        # Butter: 0.5 cups × 2 = 1 cup (only in recipe2)
        assert result[(butter.id, "cups")].total_quantity == 1.0

    def test_same_ingredient_different_units_separate(self, test_db, sample_event):
        """Same ingredient in different units should remain separate."""
        flour = Ingredient(display_name="Flour", slug="flour", category="Dry")
        test_db.add(flour)
        test_db.flush()

        # Recipe with flour in cups
        recipe1 = Recipe(name="Recipe Cups", category="Test")
        test_db.add(recipe1)
        test_db.flush()
        test_db.add(RecipeIngredient(
            recipe_id=recipe1.id, ingredient_id=flour.id, quantity=2.0, unit="cups"
        ))

        # Recipe with flour in tablespoons
        recipe2 = Recipe(name="Recipe Tbsp", category="Test")
        test_db.add(recipe2)
        test_db.flush()
        test_db.add(RecipeIngredient(
            recipe_id=recipe2.id, ingredient_id=flour.id, quantity=3.0, unit="tablespoons"
        ))
        test_db.flush()

        # Create FUs and decisions
        fu1 = FinishedUnit(
            slug="fu-cups", display_name="FU Cups",
            recipe_id=recipe1.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1, item_unit="item",
        )
        fu2 = FinishedUnit(
            slug="fu-tbsp", display_name="FU Tbsp",
            recipe_id=recipe2.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1, item_unit="item",
        )
        test_db.add_all([fu1, fu2])
        test_db.flush()

        event = sample_event
        test_db.add_all([
            BatchDecision(event_id=event.id, recipe_id=recipe1.id, finished_unit_id=fu1.id, batches=1),
            BatchDecision(event_id=event.id, recipe_id=recipe2.id, finished_unit_id=fu2.id, batches=1),
        ])
        test_db.flush()

        result = aggregate_ingredients_for_event(event.id, session=test_db)

        # Should have 2 separate entries for flour
        assert len(result) == 2
        assert result[(flour.id, "cups")].total_quantity == 2.0
        assert result[(flour.id, "tablespoons")].total_quantity == 3.0


class TestEdgeCases:
    """Tests for edge cases (WP02 T010)."""

    def test_recipe_with_no_ingredients(self, test_db, sample_event):
        """Recipe with no ingredients should be handled gracefully."""
        # Recipe with no ingredients
        recipe = Recipe(name="Empty Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="empty-fu", display_name="Empty FU",
            recipe_id=recipe.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1, item_unit="item",
        )
        test_db.add(fu)
        test_db.flush()

        event = sample_event
        test_db.add(BatchDecision(
            event_id=event.id, recipe_id=recipe.id, finished_unit_id=fu.id, batches=2
        ))
        test_db.flush()

        result = aggregate_ingredients_for_event(event.id, session=test_db)
        assert result == {}

    # Note: test_zero_batches_skipped removed because database has CHECK constraint
    # (ck_batch_decision_batches_positive) that prevents zero/negative batches.
    # The service's defensive check (bd.batches <= 0: continue) handles any edge
    # case that might bypass DB validation.


class TestPrecision:
    """Tests for precision handling (WP02 T010)."""

    def test_precision_maintained_to_three_decimals(self, test_db, sample_event):
        """Quantities should be rounded to 3 decimal places."""
        ingredient = Ingredient(display_name="Test Ingredient", slug="test-ing", category="Test")
        test_db.add(ingredient)
        test_db.flush()

        recipe = Recipe(name="Precision Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        # Use a quantity that would show precision issues: 0.333...
        test_db.add(RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=0.3333333,  # More than 3 decimals
            unit="cups",
        ))
        test_db.flush()

        fu = FinishedUnit(
            slug="precision-fu", display_name="Precision FU",
            recipe_id=recipe.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1, item_unit="item",
        )
        test_db.add(fu)
        test_db.flush()

        event = sample_event
        test_db.add(BatchDecision(
            event_id=event.id, recipe_id=recipe.id, finished_unit_id=fu.id, batches=3
        ))
        test_db.flush()

        result = aggregate_ingredients_for_event(event.id, session=test_db)

        # 0.3333333 × 3 = 0.9999999 → should round to 1.0
        total = result[(ingredient.id, "cups")].total_quantity
        assert total == 1.0

    def test_multiple_small_quantities_no_drift(self, test_db, sample_event):
        """Many small additions should not cause precision drift."""
        ingredient = Ingredient(display_name="Drift Test", slug="drift-test", category="Test")
        test_db.add(ingredient)
        test_db.flush()

        # Create 10 recipes each with 0.1 cups
        fus = []
        for i in range(10):
            recipe = Recipe(name=f"Recipe {i}", category="Test")
            test_db.add(recipe)
            test_db.flush()
            test_db.add(RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=0.1,
                unit="cups",
            ))

            fu = FinishedUnit(
                slug=f"fu-{i}", display_name=f"FU {i}",
                recipe_id=recipe.id, yield_mode=YieldMode.DISCRETE_COUNT,
                items_per_batch=1, item_unit="item",
            )
            test_db.add(fu)
            fus.append(fu)

        test_db.flush()

        event = sample_event
        for fu in fus:
            test_db.add(BatchDecision(
                event_id=event.id, recipe_id=fu.recipe_id,
                finished_unit_id=fu.id, batches=1
            ))
        test_db.flush()

        result = aggregate_ingredients_for_event(event.id, session=test_db)

        # 10 × 0.1 = 1.0 exactly
        total = result[(ingredient.id, "cups")].total_quantity
        assert total == 1.0
