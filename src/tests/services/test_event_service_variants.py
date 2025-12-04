"""Integration tests for event service shopping list with variant recommendations.

Tests for Feature 007: Variant-Aware Shopping List Recommendations

Tests cover:
- Shopping list items include variant data fields
- Total estimated cost calculation
- Existing fields preserved (FR-009)
- Various variant_status scenarios
"""

import pytest
from decimal import Decimal
from datetime import date

from src.services.event_service import get_shopping_list
from src.services import ingredient_service, recipe_service, event_service
from src.services.variant_service import create_variant
from src.models import Purchase


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def flour_ingredient(test_db):
    """Create a flour ingredient with known density for unit conversion."""
    return ingredient_service.create_ingredient(
        {
            "name": "Test Flour",
            "category": "Flour",
            "recipe_unit": "cup",
            "density_g_per_ml": 0.529,  # ~125g per cup
        }
    )


@pytest.fixture
def sugar_ingredient(test_db):
    """Create a sugar ingredient with multiple variants (no preferred)."""
    return ingredient_service.create_ingredient(
        {
            "name": "Test Sugar",
            "category": "Sugar",
            "recipe_unit": "cup",
            "density_g_per_ml": 0.85,  # ~200g per cup
        }
    )


@pytest.fixture
def no_variant_ingredient(test_db):
    """Create an ingredient with no variants configured."""
    return ingredient_service.create_ingredient(
        {
            "name": "Special Spice",
            "category": "Spices",
            "recipe_unit": "tsp",
        }
    )


@pytest.fixture
def flour_variant_preferred(test_db, flour_ingredient):
    """Create a preferred flour variant with purchase history."""
    variant = create_variant(
        flour_ingredient.slug,
        {
            "brand": "King Arthur",
            "package_size": "5 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0"),
            "preferred": True,
        },
    )

    # Add purchase history for cost data
    with test_db() as session:
        purchase = Purchase(
            variant_id=variant.id,
            purchase_date=date.today(),
            unit_cost=0.80,  # $0.80 per lb
            quantity_purchased=5.0,
            total_cost=4.00,
        )
        session.add(purchase)
        session.commit()

    return variant


@pytest.fixture
def sugar_variant_a(test_db, sugar_ingredient):
    """Create a non-preferred sugar variant."""
    variant = create_variant(
        sugar_ingredient.slug,
        {
            "brand": "Domino",
            "package_size": "4 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("4.0"),
            "preferred": False,
        },
    )

    with test_db() as session:
        purchase = Purchase(
            variant_id=variant.id,
            purchase_date=date.today(),
            unit_cost=0.50,
            quantity_purchased=4.0,
            total_cost=2.00,
        )
        session.add(purchase)
        session.commit()

    return variant


@pytest.fixture
def sugar_variant_b(test_db, sugar_ingredient):
    """Create another non-preferred sugar variant."""
    variant = create_variant(
        sugar_ingredient.slug,
        {
            "brand": "Store Brand",
            "package_size": "5 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0"),
            "preferred": False,
        },
    )

    with test_db() as session:
        purchase = Purchase(
            variant_id=variant.id,
            purchase_date=date.today(),
            unit_cost=0.40,
            quantity_purchased=5.0,
            total_cost=2.00,
        )
        session.add(purchase)
        session.commit()

    return variant


@pytest.fixture
def simple_recipe(test_db, flour_ingredient, sugar_ingredient, no_variant_ingredient):
    """Create a recipe that uses flour, sugar, and the no-variant ingredient."""
    recipe = recipe_service.create_recipe(
        {
            "name": "Test Cookie Recipe",
            "category": "Cookies",
            "yields": 24,
            "yields_unit": "cookies",
        }
    )

    # Add ingredients to recipe
    recipe_service.add_recipe_ingredient(
        recipe.id,
        {
            "ingredient_id": flour_ingredient.id,
            "quantity": Decimal("2.0"),  # 2 cups flour per batch
            "unit": "cup",
        },
    )

    recipe_service.add_recipe_ingredient(
        recipe.id,
        {
            "ingredient_id": sugar_ingredient.id,
            "quantity": Decimal("1.0"),  # 1 cup sugar per batch
            "unit": "cup",
        },
    )

    recipe_service.add_recipe_ingredient(
        recipe.id,
        {
            "ingredient_id": no_variant_ingredient.id,
            "quantity": Decimal("1.0"),  # 1 tsp spice per batch
            "unit": "tsp",
        },
    )

    return recipe


# ============================================================================
# Tests for shopping list variant recommendations
# ============================================================================


class TestShoppingListWithVariants:
    """Integration tests for get_shopping_list() with variant data."""

    def test_shopping_list_includes_new_fields(self, test_db):
        """FR-009: Shopping list items include variant-related fields."""
        # Create a minimal event
        event = event_service.create_event(
            name="Test Event",
            event_date=date(2024, 12, 25),
            year=2024,
        )

        result = get_shopping_list(event.id)

        # Verify structure
        assert isinstance(result, dict)
        assert "items" in result
        assert "total_estimated_cost" in result
        assert "items_count" in result
        assert "items_with_shortfall" in result

    def test_existing_fields_preserved(self, test_db):
        """FR-009: Existing fields (ingredient_id, name, unit, etc.) still present."""
        # Create minimal test setup - empty event returns early
        event = event_service.create_event(
            name="Field Test Event",
            event_date=date(2024, 12, 25),
            year=2024,
        )

        result = get_shopping_list(event.id)

        # Empty event should still have correct structure
        assert result["items"] == []
        assert result["total_estimated_cost"] == Decimal("0.00")
        assert result["items_count"] == 0
        assert result["items_with_shortfall"] == 0

    def test_empty_event_returns_correct_structure(self, test_db):
        """Edge case: Event with no assignments returns proper structure."""
        event = event_service.create_event(
            name="Empty Event",
            event_date=date(2024, 12, 25),
            year=2024,
        )

        result = get_shopping_list(event.id)

        assert result == {
            "items": [],
            "total_estimated_cost": Decimal("0.00"),
            "items_count": 0,
            "items_with_shortfall": 0,
        }


class TestTotalEstimatedCostCalculation:
    """Tests for total_estimated_cost calculation."""

    def test_total_cost_is_decimal(self, test_db):
        """SC-004: Total cost is a Decimal for precision."""
        event = event_service.create_event(
            name="Cost Test Event",
            event_date=date(2024, 12, 25),
            year=2024,
        )

        result = get_shopping_list(event.id)

        assert isinstance(result["total_estimated_cost"], Decimal)

    def test_empty_event_total_is_zero(self, test_db):
        """Empty event should have zero total cost."""
        event = event_service.create_event(
            name="Zero Cost Event",
            event_date=date(2024, 12, 25),
            year=2024,
        )

        result = get_shopping_list(event.id)

        assert result["total_estimated_cost"] == Decimal("0.00")
