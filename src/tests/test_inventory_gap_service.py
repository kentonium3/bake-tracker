"""Unit tests for inventory gap analysis service (F075)."""

import pytest
from datetime import date
from decimal import Decimal

from src.models import (
    Event,
    Recipe,
    Ingredient,
    RecipeIngredient,
    FinishedUnit,
    BatchDecision,
    Product,
    InventoryItem,
)
from src.models.finished_unit import YieldMode
from src.services.inventory_gap_service import (
    analyze_inventory_gaps,
    GapItem,
    GapAnalysisResult,
)


@pytest.fixture
def sample_event(test_db):
    """Create a test event."""
    event = Event(name="Test Event", event_date=date(2026, 1, 1), year=2026)
    test_db.add(event)
    test_db.flush()
    return event


@pytest.fixture
def flour_ingredient(test_db):
    """Create flour ingredient."""
    flour = Ingredient(display_name="Flour", slug="flour", category="Dry")
    test_db.add(flour)
    test_db.flush()
    return flour


@pytest.fixture
def recipe_with_flour(test_db, flour_ingredient):
    """Create a recipe using 2 cups flour."""
    recipe = Recipe(name="Test Cookies", category="Cookies")
    test_db.add(recipe)
    test_db.flush()

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=flour_ingredient.id,
        quantity=2.0,
        unit="cups",
    )
    test_db.add(ri)
    test_db.flush()
    return recipe


@pytest.fixture
def finished_unit_for_recipe(test_db, recipe_with_flour):
    """Create a FinishedUnit linked to the recipe."""
    fu = FinishedUnit(
        slug="test-cookies",
        display_name="Test Cookies",
        recipe_id=recipe_with_flour.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookie",
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def flour_product(test_db, flour_ingredient):
    """Create a product for flour inventory."""
    product = Product(
        product_name="Test Flour",
        ingredient_id=flour_ingredient.id,
        package_unit="cups",
        package_unit_quantity=5.0,
    )
    test_db.add(product)
    test_db.flush()
    return product


class TestGapCalculation:
    """Tests for gap calculation logic."""

    def test_gap_calculation_shortfall(
        self,
        test_db,
        sample_event,
        recipe_with_flour,
        finished_unit_for_recipe,
        flour_ingredient,
        flour_product,
    ):
        """Gap should equal needed - on_hand when inventory is insufficient."""
        # Setup: 3 batches x 2 cups = 6 cups needed
        bd = BatchDecision(
            event_id=sample_event.id,
            recipe_id=recipe_with_flour.id,
            finished_unit_id=finished_unit_for_recipe.id,
            batches=3,
        )
        test_db.add(bd)

        # Setup: 2 cups on hand
        inv = InventoryItem(
            product_id=flour_product.id,
            quantity=2.0,
            purchase_date=date(2026, 1, 1),
        )
        test_db.add(inv)
        test_db.flush()

        result = analyze_inventory_gaps(sample_event.id, session=test_db)

        # Verify: 6 needed - 2 on hand = 4 gap
        assert len(result.purchase_items) == 1
        assert len(result.sufficient_items) == 0

        flour_gap = result.purchase_items[0]
        assert flour_gap.ingredient_id == flour_ingredient.id
        assert flour_gap.quantity_needed == 6.0
        assert flour_gap.quantity_on_hand == 2.0
        assert flour_gap.gap == 4.0

    def test_gap_calculation_sufficient(
        self,
        test_db,
        sample_event,
        recipe_with_flour,
        finished_unit_for_recipe,
        flour_ingredient,
        flour_product,
    ):
        """Gap should be zero when inventory exceeds or equals need."""
        # Setup: 2 batches x 2 cups = 4 cups needed
        bd = BatchDecision(
            event_id=sample_event.id,
            recipe_id=recipe_with_flour.id,
            finished_unit_id=finished_unit_for_recipe.id,
            batches=2,
        )
        test_db.add(bd)

        # Setup: 5 cups on hand (more than needed)
        inv = InventoryItem(
            product_id=flour_product.id,
            quantity=5.0,
            purchase_date=date(2026, 1, 1),
        )
        test_db.add(inv)
        test_db.flush()

        result = analyze_inventory_gaps(sample_event.id, session=test_db)

        # Verify: sufficient inventory
        assert len(result.purchase_items) == 0
        assert len(result.sufficient_items) == 1

        flour_item = result.sufficient_items[0]
        assert flour_item.quantity_needed == 4.0
        assert flour_item.quantity_on_hand == 5.0
        assert flour_item.gap == 0.0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_missing_inventory_treated_as_zero(
        self,
        test_db,
        sample_event,
        recipe_with_flour,
        finished_unit_for_recipe,
        flour_ingredient,
    ):
        """Missing inventory should be treated as zero, not raise error."""
        # Setup: Need 4 cups, NO inventory records exist
        bd = BatchDecision(
            event_id=sample_event.id,
            recipe_id=recipe_with_flour.id,
            finished_unit_id=finished_unit_for_recipe.id,
            batches=2,
        )
        test_db.add(bd)
        test_db.flush()

        # No InventoryItem created for flour

        result = analyze_inventory_gaps(sample_event.id, session=test_db)

        # Verify: treated as 0 on hand, full amount is gap
        assert len(result.purchase_items) == 1
        assert len(result.sufficient_items) == 0

        flour_gap = result.purchase_items[0]
        assert flour_gap.quantity_needed == 4.0
        assert flour_gap.quantity_on_hand == 0.0
        assert flour_gap.gap == 4.0

    def test_all_items_categorized(
        self, test_db, sample_event, flour_ingredient, flour_product
    ):
        """Every input ingredient must appear in exactly one output list."""
        # Create second ingredient (sugar)
        sugar = Ingredient(display_name="Sugar", slug="sugar", category="Dry")
        test_db.add(sugar)
        test_db.flush()

        # Recipe with both ingredients
        recipe = Recipe(name="Mixed Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        test_db.add_all(
            [
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=flour_ingredient.id,
                    quantity=2.0,
                    unit="cups",
                ),
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=sugar.id,
                    quantity=1.0,
                    unit="cups",
                ),
            ]
        )

        fu = FinishedUnit(
            slug="mixed-cookies",
            display_name="Mixed Cookies",
            recipe_id=recipe.id,
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
        )
        test_db.add(fu)
        test_db.flush()

        bd = BatchDecision(
            event_id=sample_event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=1,
        )
        test_db.add(bd)

        # Add inventory for flour only (sugar will be missing)
        inv = InventoryItem(
            product_id=flour_product.id,
            quantity=5.0,
            purchase_date=date(2026, 1, 1),
        )
        test_db.add(inv)
        test_db.flush()

        result = analyze_inventory_gaps(sample_event.id, session=test_db)

        # Verify: 2 total items, each in exactly one list
        total_items = len(result.purchase_items) + len(result.sufficient_items)
        assert total_items == 2

        # Flour should be sufficient (2 needed, 5 on hand)
        # Sugar should need purchase (1 needed, 0 on hand)
        all_ids = [
            i.ingredient_id for i in result.purchase_items + result.sufficient_items
        ]
        assert flour_ingredient.id in all_ids
        assert sugar.id in all_ids

    def test_empty_event_returns_empty(self, test_db, sample_event):
        """Event with no batch decisions should return empty result."""
        # No batch decisions added

        result = analyze_inventory_gaps(sample_event.id, session=test_db)

        assert result.purchase_items == []
        assert result.sufficient_items == []

    def test_unit_mismatch_treated_as_zero(
        self, test_db, sample_event, flour_ingredient
    ):
        """Inventory in different unit should not count toward need."""
        # Recipe needs flour in "cups"
        recipe = Recipe(name="Cups Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        test_db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=flour_ingredient.id,
                quantity=2.0,
                unit="cups",  # Need cups
            )
        )

        fu = FinishedUnit(
            slug="cups-recipe",
            display_name="Cups Recipe",
            recipe_id=recipe.id,
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1,
            item_unit="item",
        )
        test_db.add(fu)
        test_db.flush()

        bd = BatchDecision(
            event_id=sample_event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=1,
        )
        test_db.add(bd)

        # Create inventory in POUNDS, not cups
        product_lb = Product(
            product_name="Flour Pounds",
            ingredient_id=flour_ingredient.id,
            package_unit="lb",  # Different unit!
            package_unit_quantity=5.0,
        )
        test_db.add(product_lb)
        test_db.flush()

        inv = InventoryItem(
            product_id=product_lb.id,
            quantity=10.0,  # 10 lb on hand, but we need cups
            purchase_date=date(2026, 1, 1),
        )
        test_db.add(inv)
        test_db.flush()

        result = analyze_inventory_gaps(sample_event.id, session=test_db)

        # Verify: lb inventory doesn't count toward cups need
        assert len(result.purchase_items) == 1
        flour_gap = result.purchase_items[0]
        assert flour_gap.unit == "cups"
        assert flour_gap.quantity_on_hand == 0.0  # No cups inventory
        assert flour_gap.gap == 2.0
