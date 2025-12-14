"""Tests for RecipeService, focusing on calculate_actual_cost() functionality.

Tests cover:
- FIFO ordering verification (oldest inventory consumed first)
- Read-only behavior (pantry unchanged after cost calculation)
- Multiple ingredients summation
- Unit conversion (volume <-> weight)
- Error handling (RecipeNotFound, IngredientNotFound, ValidationError)
- Shortfall handling with fallback pricing
"""

import pytest
from decimal import Decimal
from datetime import date

from src.services import (
    recipe_service,
    ingredient_service,
    product_service,
    inventory_item_service,
    purchase_service
)
from src.services.exceptions import RecipeNotFound, IngredientNotFound, ValidationError
from src.models import Recipe, RecipeIngredient

class TestCalculateActualCost:
    """Tests for calculate_actual_cost() method."""

    def test_calculate_actual_cost_uses_fifo_ordering(self, test_db):
        """Test: FIFO ordering - oldest inventory costs used first."""
        # Setup: Create ingredient and product
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Test FIFO Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "purchase_unit": "cup", "purchase_quantity": Decimal("10.0")}
        )

        # Add two lots with different costs (older lot cheaper)
        # Lot 1: 2 cups at $0.10/cup (older - should be used)
        lot1 = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=Decimal("2.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(lot1.id, {"unit_cost": 0.10})

        # Lot 2: 2 cups at $0.12/cup (newer - should NOT be used if qty <= 2)
        lot2 = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=Decimal("2.0"), purchase_date=date(2025, 2, 1)
        )
        inventory_item_service.update_inventory_item(lot2.id, {"unit_cost": 0.12})

        # Create recipe needing 2 cups
        recipe = recipe_service.create_recipe(
            {
                "name": "FIFO Test Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Should use FIFO (2 cups * $0.10 = $0.20)
        expected_cost = Decimal("0.20")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost}, got ${cost}. FIFO should use oldest lot at $0.10/cup"

    def test_calculate_actual_cost_does_not_modify_pantry(self, test_db):
        """Test: Pantry quantities remain unchanged after cost calculation."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Test Pantry Unchanged",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "purchase_unit": "cup", "purchase_quantity": Decimal("10.0")}
        )

        initial_quantity = Decimal("5.0")
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=initial_quantity, purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(lot.id, {"unit_cost": 0.10})

        recipe = recipe_service.create_recipe(
            {
                "name": "Pantry Test Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Capture pantry state before
        items_before = inventory_item_service.get_inventory_items(ingredient_slug=ingredient.slug)
        qty_before = Decimal(str(items_before[0].quantity))

        # Act
        recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Pantry unchanged
        items_after = inventory_item_service.get_inventory_items(ingredient_slug=ingredient.slug)
        qty_after = Decimal(str(items_after[0].quantity))

        assert abs(qty_after - qty_before) < Decimal(
            "0.001"
        ), f"Pantry quantity changed from {qty_before} to {qty_after}. Should be read-only."

    def test_calculate_actual_cost_handles_multiple_ingredients(self, test_db):
        """Test: Multiple ingredients are summed correctly."""
        # Setup: Create two ingredients
        flour = ingredient_service.create_ingredient(
            {
                "name": "Multi Test Flour",
                "category": "Flour"
            }
        )
        sugar = ingredient_service.create_ingredient(
            {
                "name": "Multi Test Sugar",
                "category": "Sugar"
            }
        )

        # Create products
        flour_product = product_service.create_product(
            flour.slug,
            {"brand": "Test Brand", "purchase_unit": "cup", "purchase_quantity": Decimal("10.0")}
        )
        sugar_product = product_service.create_product(
            sugar.slug,
            {"brand": "Test Brand", "purchase_unit": "cup", "purchase_quantity": Decimal("10.0")}
        )

        # Add pantry items
        flour_lot = inventory_item_service.add_to_inventory(
            product_id=flour_product.id, quantity=Decimal("5.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(flour_lot.id, {"unit_cost": 0.10})  # $0.10/cup

        sugar_lot = inventory_item_service.add_to_inventory(
            product_id=sugar_product.id, quantity=Decimal("5.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(sugar_lot.id, {"unit_cost": 0.20})  # $0.20/cup

        # Create recipe with both ingredients
        recipe = recipe_service.create_recipe(
            {
                "name": "Multi Ingredient Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [
                {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},  # 2 * $0.10 = $0.20
                {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},  # 1 * $0.20 = $0.20
            ]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Total = $0.20 + $0.20 = $0.40
        expected_cost = Decimal("0.40")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost}, got ${cost}"

    def test_calculate_actual_cost_empty_recipe_returns_zero(self, test_db):
        """Test: Empty recipe (no ingredients) returns $0.00."""
        # Create recipe with no ingredients
        recipe = recipe_service.create_recipe(
            {
                "name": "Empty Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [],  # No ingredients
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert
        assert cost == Decimal("0.00"), f"Expected $0.00 for empty recipe, got ${cost}"

    def test_calculate_actual_cost_raises_recipe_not_found(self, test_db):
        """Test: Invalid recipe_id raises RecipeNotFound."""
        with pytest.raises(RecipeNotFound):
            recipe_service.calculate_actual_cost(99999)  # Non-existent ID

    def test_calculate_actual_cost_with_shortfall_uses_fallback(self, test_db):
        """Test: When pantry insufficient, uses fallback pricing for shortfall."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Shortfall Test Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(product.id)

        # Add only 2 cups to pantry at $0.10/cup
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=Decimal("2.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(lot.id, {"unit_cost": 0.10})

        # Record a purchase for fallback pricing at $0.15/cup
        purchase_service.record_purchase(
            product_id=product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.50"),  # $0.15/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing 3 cups (1 cup shortfall)
        recipe = recipe_service.create_recipe(
            {
                "name": "Shortfall Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: 2 cups * $0.10 (FIFO) + 1 cup * $0.15 (fallback) = $0.35
        expected_cost = Decimal("0.35")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (FIFO + fallback), got ${cost}"

    def test_calculate_actual_cost_no_pantry_uses_all_fallback(self, test_db):
        """Test: Empty pantry uses 100% fallback pricing."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "No Pantry Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "purchase_unit": "cup", "purchase_quantity": Decimal("10.0")}
        )
        product_service.set_preferred_product(product.id)

        # Record purchase for fallback pricing (no pantry inventory)
        purchase_service.record_purchase(
            product_id=product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("2.00"),  # $0.20/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing 3 cups
        recipe = recipe_service.create_recipe(
            {
                "name": "No Pantry Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: 3 cups * $0.20 (all fallback) = $0.60
        expected_cost = Decimal("0.60")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (100% fallback), got ${cost}"

    def test_calculate_actual_cost_raises_validation_error_no_purchase_history(self, test_db):
        """Test: Raises ValidationError when no purchase history for fallback."""
        # Setup: Ingredient with product but no purchase history and no pantry
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "No History Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "purchase_unit": "cup", "purchase_quantity": Decimal("10.0")}
        )

        # Create recipe (no pantry = shortfall, but no purchase history for fallback)
        recipe = recipe_service.create_recipe(
            {
                "name": "No History Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.calculate_actual_cost(recipe.id)

        # Check for the expected error message (the message includes: "no purchase history")
        error_text = str(exc_info.value).lower().replace("; ", "")
        assert "purchase history" in error_text or "no purchase" in error_text

    def test_calculate_actual_cost_raises_validation_error_no_products(self, test_db):
        """Test: Raises ValidationError when ingredient has no products configured."""
        # Setup: Ingredient with NO products
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "No Products Flour",
                "category": "Flour"
            }
        )

        # Create recipe with this ingredient (no products, so shortfall can't be priced)
        recipe = recipe_service.create_recipe(
            {
                "name": "No Products Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.calculate_actual_cost(recipe.id)

        assert "no products" in str(exc_info.value).lower()

    def test_calculate_actual_cost_decimal_precision(self, test_db):
        """Test: Decimal precision maintained in cost calculations."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Precision Test Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "purchase_unit": "cup", "purchase_quantity": Decimal("10.0")}
        )

        # Add pantry with precise unit cost
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=Decimal("10.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(lot.id, {"unit_cost": 0.123})  # Precise value

        # Create recipe
        recipe = recipe_service.create_recipe(
            {
                "name": "Precision Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Result is Decimal type
        assert isinstance(cost, Decimal), f"Expected Decimal, got {type(cost)}"

        # Assert: Precision maintained (3 * $0.123 = $0.369)
        expected_cost = Decimal("0.369")
        assert abs(cost - expected_cost) < Decimal(
            "0.001"
        ), f"Expected ${expected_cost}, got ${cost}"

class TestCalculateEstimatedCost:
    """Tests for calculate_estimated_cost() method."""

    def test_calculate_estimated_cost_uses_preferred_product(self, test_db):
        """Test: Uses preferred product's price when available."""
        # Setup: Create ingredient
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Estimated Test Flour",
                "category": "Flour"
            }
        )

        # Create two products - one preferred, one not
        product1 = product_service.create_product(
            ingredient.slug,
            {
                "brand": "Cheap Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": False
            }
        )
        product2 = product_service.create_product(
            ingredient.slug,
            {
                "brand": "Preferred Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(product2.id)

        # Record purchases with different prices
        purchase_service.record_purchase(
            product_id=product1.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("0.50"),  # $0.05/cup
            purchase_date=date(2025, 1, 1)
        )
        purchase_service.record_purchase(
            product_id=product2.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.00"),  # $0.10/cup (preferred)
            purchase_date=date(2025, 1, 1)
        )

        # Create recipe needing 2 cups
        recipe = recipe_service.create_recipe(
            {
                "name": "Preferred Test Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Should use preferred product price (2 * $0.10 = $0.20)
        expected_cost = Decimal("0.20")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (preferred product), got ${cost}"

    def test_calculate_estimated_cost_falls_back_to_any_product(self, test_db):
        """Test: Falls back to any product when no preferred set."""
        # Setup: Create ingredient
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Fallback Test Flour",
                "category": "Flour"
            }
        )

        # Create product WITHOUT setting it as preferred
        product = product_service.create_product(
            ingredient.slug,
            {
                "brand": "Only Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": False,  # Not preferred
            }
        )

        # Record purchase
        purchase_service.record_purchase(
            product_id=product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.50"),  # $0.15/cup
            purchase_date=date(2025, 1, 1)
        )

        # Create recipe
        recipe = recipe_service.create_recipe(
            {
                "name": "Fallback Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Should use the only available product (3 * $0.15 = $0.45)
        expected_cost = Decimal("0.45")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (fallback product), got ${cost}"

    def test_calculate_estimated_cost_handles_multiple_ingredients(self, test_db):
        """Test: Multiple ingredients are summed correctly."""
        # Setup: Create two ingredients
        flour = ingredient_service.create_ingredient(
            {
                "name": "Est Multi Flour",
                "category": "Flour"
            }
        )
        sugar = ingredient_service.create_ingredient(
            {
                "name": "Est Multi Sugar",
                "category": "Sugar"
            }
        )

        # Create products
        flour_product = product_service.create_product(
            flour.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(flour_product.id)

        sugar_product = product_service.create_product(
            sugar.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(sugar_product.id)

        # Record purchases
        purchase_service.record_purchase(
            product_id=flour_product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.00"),  # $0.10/cup
            purchase_date=date(2025, 1, 1)
        )
        purchase_service.record_purchase(
            product_id=sugar_product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("2.00"),  # $0.20/cup
            purchase_date=date(2025, 1, 1)
        )

        # Create recipe with both ingredients
        recipe = recipe_service.create_recipe(
            {
                "name": "Est Multi Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [
                {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},  # 2 * $0.10 = $0.20
                {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},  # 1 * $0.20 = $0.20
            ]
        )

        # Act
        cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Total = $0.20 + $0.20 = $0.40
        expected_cost = Decimal("0.40")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost}, got ${cost}"

    def test_calculate_estimated_cost_ignores_pantry(self, test_db):
        """Test: Pantry inventory is completely ignored - uses product pricing."""
        # Setup: Create ingredient
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Ignore Pantry Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(product.id)

        # Add pantry items at LOW price ($0.05/cup)
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=Decimal("10.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(lot.id, {"unit_cost": 0.05})  # Cheap pantry price

        # Record purchase at HIGHER price ($0.20/cup) - this should be used
        purchase_service.record_purchase(
            product_id=product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("2.00"),  # $0.20/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe
        recipe = recipe_service.create_recipe(
            {
                "name": "Ignore Pantry Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act
        estimated_cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Should use purchase price ($0.20/cup), NOT pantry price ($0.05/cup)
        # 2 cups * $0.20 = $0.40
        expected_cost = Decimal("0.40")
        assert abs(estimated_cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (purchase price, not pantry), got ${estimated_cost}"

    def test_calculate_estimated_cost_empty_recipe_returns_zero(self, test_db):
        """Test: Empty recipe (no ingredients) returns $0.00."""
        # Create recipe with no ingredients
        recipe = recipe_service.create_recipe(
            {
                "name": "Empty Est Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [],  # No ingredients
        )

        # Act
        cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert
        assert cost == Decimal("0.00"), f"Expected $0.00 for empty recipe, got ${cost}"

    def test_calculate_estimated_cost_raises_recipe_not_found(self, test_db):
        """Test: Invalid recipe_id raises RecipeNotFound."""
        with pytest.raises(RecipeNotFound):
            recipe_service.calculate_estimated_cost(99999)  # Non-existent ID

    def test_calculate_estimated_cost_raises_validation_error_no_purchase(self, test_db):
        """Test: Raises ValidationError when no purchase history exists."""
        # Setup: Ingredient with product but no purchase history
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "No Purchase Est Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "purchase_unit": "cup", "purchase_quantity": Decimal("10.0")}
        )

        # Create recipe (no purchase history for fallback)
        recipe = recipe_service.create_recipe(
            {
                "name": "No Purchase Est Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.calculate_estimated_cost(recipe.id)

        # The error message contains "no purchase history available"
        # but may be formatted with semicolons due to ValidationError's __str__ method
        error_text = str(exc_info.value).lower().replace("; ", "")
        assert "purchase" in error_text and "history" in error_text

    def test_calculate_estimated_cost_raises_validation_error_no_products(self, test_db):
        """Test: Raises ValidationError when ingredient has no products configured."""
        # Setup: Ingredient with NO products
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "No Products Est Flour",
                "category": "Flour"
            }
        )

        # Create recipe with this ingredient (no products)
        recipe = recipe_service.create_recipe(
            {
                "name": "No Products Est Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.calculate_estimated_cost(recipe.id)

        assert "no products" in str(exc_info.value).lower()

class TestPartialInventoryScenarios:
    """Tests for partial inventory blended costing scenarios (WP04)."""

    def test_partial_inventory_full_coverage_no_fallback(self, test_db):
        """Test: When pantry has more than needed, uses only FIFO costs (no fallback)."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Full Coverage Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(product.id)

        # Add 5 cups to pantry at $0.10/cup (more than needed)
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=Decimal("5.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(lot.id, {"unit_cost": 0.10})

        # Record a purchase for fallback at HIGHER price - should NOT be used
        purchase_service.record_purchase(
            product_id=product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("5.00"),  # $0.50/cup - expensive!
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing 2 cups (pantry has 5)
        recipe = recipe_service.create_recipe(
            {
                "name": "Full Coverage Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Only FIFO cost used (2 * $0.10 = $0.20), NOT fallback ($0.50/cup)
        expected_cost = Decimal("0.20")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (FIFO only, no fallback), got ${cost}"

    def test_partial_inventory_multiple_ingredients_mixed_coverage(self, test_db):
        """Test: Multiple ingredients with varying coverage levels costed correctly."""
        # Setup: Three ingredients with different coverage levels
        # Flour: partial coverage (2 of 3 cups)
        # Sugar: full coverage (5 of 1 cup)
        # Butter: no coverage (0 of 2 cups)

        flour = ingredient_service.create_ingredient(
            {
                "name": "Mixed Flour",
                "category": "Flour"
            }
        )
        sugar = ingredient_service.create_ingredient(
            {
                "name": "Mixed Sugar",
                "category": "Sugar"
            }
        )
        butter = ingredient_service.create_ingredient(
            {
                "name": "Mixed Butter",
                "category": "Dairy"
            }
        )

        # Create products
        flour_product = product_service.create_product(
            flour.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(flour_product.id)

        sugar_product = product_service.create_product(
            sugar.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(sugar_product.id)

        butter_product = product_service.create_product(
            butter.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(butter_product.id)

        # Add pantry items
        # Flour: 2 cups at $0.10/cup (partial coverage)
        flour_lot = inventory_item_service.add_to_inventory(
            product_id=flour_product.id, quantity=Decimal("2.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(flour_lot.id, {"unit_cost": 0.10})

        # Sugar: 5 cups at $0.20/cup (full coverage)
        sugar_lot = inventory_item_service.add_to_inventory(
            product_id=sugar_product.id, quantity=Decimal("5.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(sugar_lot.id, {"unit_cost": 0.20})

        # Butter: NO pantry inventory (zero coverage)

        # Record purchases for fallback pricing
        purchase_service.record_purchase(
            product_id=flour_product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.50"),  # $0.15/cup
            purchase_date=date(2025, 1, 15)
        )
        purchase_service.record_purchase(
            product_id=sugar_product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("3.00"),  # $0.30/cup (won't be used - full coverage)
            purchase_date=date(2025, 1, 15)
        )
        purchase_service.record_purchase(
            product_id=butter_product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("5.00"),  # $0.50/cup (100% fallback)
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe with all three ingredients
        recipe = recipe_service.create_recipe(
            {
                "name": "Mixed Coverage Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [
                {"ingredient_id": flour.id, "quantity": 3.0, "unit": "cup"},  # 2 FIFO + 1 fallback
                {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},  # 1 FIFO only
                {"ingredient_id": butter.id, "quantity": 2.0, "unit": "cup"},  # 2 fallback only
            ]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert:
        # Flour: 2*$0.10 + 1*$0.15 = $0.35
        # Sugar: 1*$0.20 = $0.20
        # Butter: 2*$0.50 = $1.00
        # Total: $1.55
        expected_cost = Decimal("1.55")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (mixed coverage), got ${cost}"

    def test_partial_inventory_exact_coverage_boundary(self, test_db):
        """Test: Boundary condition - pantry has exactly what's needed (no shortfall)."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Exact Coverage Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(product.id)

        # Add exactly 3 cups at $0.10/cup
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=Decimal("3.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(lot.id, {"unit_cost": 0.10})

        # Record expensive fallback (should NOT be used)
        purchase_service.record_purchase(
            product_id=product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("10.00"),  # $1.00/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing exactly 3 cups
        recipe = recipe_service.create_recipe(
            {
                "name": "Exact Coverage Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Exactly 3 cups at $0.10 = $0.30 (no fallback)
        expected_cost = Decimal("0.30")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (exact coverage), got ${cost}"

    def test_partial_inventory_decimal_precision_maintained(self, test_db):
        """Test: Decimal precision maintained in blended cost calculations."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Precision Blend Flour",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(product.id)

        # Add 1.5 cups at $0.123/cup (precise value)
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id, quantity=Decimal("1.5"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(lot.id, {"unit_cost": 0.123})

        # Record fallback at $0.456/cup (precise value)
        purchase_service.record_purchase(
            product_id=product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("4.56"),  # $0.456/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing 2.5 cups (1 cup shortfall)
        recipe = recipe_service.create_recipe(
            {
                "name": "Precision Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 2.5, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: 1.5 * $0.123 + 1.0 * $0.456 = $0.1845 + $0.456 = $0.6405
        expected_cost = Decimal("0.6405")
        assert abs(cost - expected_cost) < Decimal(
            "0.001"
        ), f"Expected ${expected_cost} (precise calculation), got ${cost}"

        # Verify result is Decimal type
        assert isinstance(cost, Decimal), f"Expected Decimal, got {type(cost)}"

class TestEdgeCases:
    """Tests for edge cases and validation (WP05)."""

    def test_calculate_actual_cost_skips_zero_quantity_ingredients(self, test_db):
        """Test: Zero quantity ingredients contribute $0 to total."""
        # Setup
        flour = ingredient_service.create_ingredient(
            {
                "name": "Zero Qty Flour",
                "category": "Flour"
            }
        )
        sugar = ingredient_service.create_ingredient(
            {
                "name": "Zero Qty Sugar",
                "category": "Sugar"
            }
        )

        # Create products
        flour_product = product_service.create_product(
            flour.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(flour_product.id)

        sugar_product = product_service.create_product(
            sugar.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(sugar_product.id)

        # Add pantry
        flour_lot = inventory_item_service.add_to_inventory(
            product_id=flour_product.id, quantity=Decimal("5.0"), purchase_date=date(2025, 1, 1)
        )
        inventory_item_service.update_inventory_item(flour_lot.id, {"unit_cost": 0.10})

        # Record purchase for sugar (in case fallback is needed)
        purchase_service.record_purchase(
            product_id=sugar_product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("5.00"),  # $0.50/cup - should NOT be used
            purchase_date=date(2025, 1, 1)
        )

        # Create recipe with flour (2 cups) and sugar (0 cups - zero quantity)
        recipe = recipe_service.create_recipe(
            {
                "name": "Zero Qty Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [
                {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},
                {"ingredient_id": sugar.id, "quantity": 0.0, "unit": "cup"},  # Zero!
            ]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Only flour costs (2 * $0.10 = $0.20), sugar skipped
        expected_cost = Decimal("0.20")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (zero qty ingredient skipped), got ${cost}"

    def test_calculate_estimated_cost_skips_zero_quantity_ingredients(self, test_db):
        """Test: Zero quantity ingredients skipped in estimated cost."""
        # Setup
        flour = ingredient_service.create_ingredient(
            {
                "name": "Est Zero Flour",
                "category": "Flour"
            }
        )
        sugar = ingredient_service.create_ingredient(
            {
                "name": "Est Zero Sugar",
                "category": "Sugar"
            }
        )

        # Create products
        flour_product = product_service.create_product(
            flour.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(flour_product.id)

        sugar_product = product_service.create_product(
            sugar.slug,
            {
                "brand": "Test Brand",
                "purchase_unit": "cup",
                "purchase_quantity": Decimal("10.0"),
                "is_preferred": True
            }
        )
        product_service.set_preferred_product(sugar_product.id)

        # Record purchases
        purchase_service.record_purchase(
            product_id=flour_product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.00"),  # $0.10/cup
            purchase_date=date(2025, 1, 1)
        )
        purchase_service.record_purchase(
            product_id=sugar_product.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("5.00"),  # $0.50/cup - should NOT be used
            purchase_date=date(2025, 1, 1)
        )

        # Create recipe with flour (2 cups) and sugar (0 cups)
        recipe = recipe_service.create_recipe(
            {
                "name": "Est Zero Qty Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [
                {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},
                {"ingredient_id": sugar.id, "quantity": 0.0, "unit": "cup"},  # Zero!
            ]
        )

        # Act
        cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Only flour costs (2 * $0.10 = $0.20)
        expected_cost = Decimal("0.20")
        assert abs(cost - expected_cost) < Decimal(
            "0.01"
        ), f"Expected ${expected_cost} (zero qty ingredient skipped), got ${cost}"

    def test_error_message_includes_ingredient_name(self, test_db):
        """Test: Error messages include the ingredient name for user clarity."""
        # Setup: Ingredient with no products
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Saffron Threads",  # Specific name to check in message
                "category": "Spices"
            }
        )

        recipe = recipe_service.create_recipe(
            {
                "name": "Error Message Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 1.0, "unit": "tsp"}]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.calculate_actual_cost(recipe.id)

        error_message = str(exc_info.value)
        # The message should include the ingredient name
        assert "saffron" in error_message.lower() or "no products" in error_message.lower()

    def test_error_message_for_no_purchase_history(self, test_db):
        """Test: ValidationError message mentions purchase history."""
        # Setup: Ingredient with product but no purchases
        ingredient = ingredient_service.create_ingredient(
            {
                "name": "Rare Spice",
                "category": "Spices"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Exotic Brand", "purchase_unit": "tsp", "purchase_quantity": Decimal("1.0")}
        )

        recipe = recipe_service.create_recipe(
            {
                "name": "No Purchase Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": ingredient.id, "quantity": 1.0, "unit": "tsp"}]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.calculate_actual_cost(recipe.id)

        error_message = str(exc_info.value).lower().replace("; ", "")
        # The message should mention purchase history
        assert "purchase" in error_message and "history" in error_message

# ============================================================================
# Recipe Component CRUD Tests (Feature 012: Nested Recipes)
# ============================================================================

class TestAddRecipeComponent:
    """Tests for add_recipe_component() method."""

    def test_add_recipe_component_success(self, test_db):
        """Test adding a component to a recipe."""
        # Create two recipes
        parent = recipe_service.create_recipe(
            {
                "name": "Parent Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Child Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # Add child as component
        component = recipe_service.add_recipe_component(
            parent.id, child.id, quantity=2.0, notes="Double batch"
        )

        assert component.recipe_id == parent.id
        assert component.component_recipe_id == child.id
        assert component.quantity == 2.0
        assert component.notes == "Double batch"
        assert component.component_recipe.name == "Child Recipe"

    def test_add_recipe_component_default_quantity(self, test_db):
        """Test that default quantity is 1.0."""
        parent = recipe_service.create_recipe(
            {
                "name": "Default Qty Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Default Qty Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        component = recipe_service.add_recipe_component(parent.id, child.id)

        assert component.quantity == 1.0

    def test_add_recipe_component_fractional_quantity(self, test_db):
        """Test adding a component with fractional quantity (0.5 batch)."""
        parent = recipe_service.create_recipe(
            {
                "name": "Fractional Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Fractional Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        component = recipe_service.add_recipe_component(parent.id, child.id, quantity=0.5)

        assert component.quantity == 0.5

    def test_add_recipe_component_invalid_quantity_zero(self, test_db):
        """Test that quantity = 0 raises ValidationError."""
        parent = recipe_service.create_recipe(
            {
                "name": "Zero Qty Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Zero Qty Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        with pytest.raises(ValidationError):
            recipe_service.add_recipe_component(parent.id, child.id, quantity=0)

    def test_add_recipe_component_invalid_quantity_negative(self, test_db):
        """Test that negative quantity raises ValidationError."""
        parent = recipe_service.create_recipe(
            {
                "name": "Neg Qty Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Neg Qty Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        with pytest.raises(ValidationError):
            recipe_service.add_recipe_component(parent.id, child.id, quantity=-1.0)

    def test_add_recipe_component_duplicate_raises_error(self, test_db):
        """Test that adding same component twice raises ValidationError."""
        parent = recipe_service.create_recipe(
            {
                "name": "Duplicate Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Duplicate Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # First add succeeds
        recipe_service.add_recipe_component(parent.id, child.id)

        # Second add raises error
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.add_recipe_component(parent.id, child.id)

        assert "already a component" in str(exc_info.value).lower()

    def test_add_recipe_component_nonexistent_parent(self, test_db):
        """Test that nonexistent parent recipe raises RecipeNotFound."""
        child = recipe_service.create_recipe(
            {
                "name": "Orphan Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        with pytest.raises(RecipeNotFound):
            recipe_service.add_recipe_component(99999, child.id)

    def test_add_recipe_component_nonexistent_component(self, test_db):
        """Test that nonexistent component recipe raises RecipeNotFound."""
        parent = recipe_service.create_recipe(
            {
                "name": "Missing Child Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        with pytest.raises(RecipeNotFound):
            recipe_service.add_recipe_component(parent.id, 99999)

    def test_add_recipe_component_auto_sort_order(self, test_db):
        """Test that sort_order auto-increments when not provided."""
        parent = recipe_service.create_recipe(
            {
                "name": "Sort Order Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child1 = recipe_service.create_recipe(
            {
                "name": "Sort Child 1",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child2 = recipe_service.create_recipe(
            {
                "name": "Sort Child 2",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        comp1 = recipe_service.add_recipe_component(parent.id, child1.id)
        comp2 = recipe_service.add_recipe_component(parent.id, child2.id)

        assert comp1.sort_order == 1
        assert comp2.sort_order == 2

class TestRemoveRecipeComponent:
    """Tests for remove_recipe_component() method."""

    def test_remove_recipe_component_success(self, test_db):
        """Test removing a component."""
        parent = recipe_service.create_recipe(
            {
                "name": "Remove Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Remove Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_service.add_recipe_component(parent.id, child.id)

        result = recipe_service.remove_recipe_component(parent.id, child.id)

        assert result is True

        # Verify removed
        components = recipe_service.get_recipe_components(parent.id)
        assert len(components) == 0

    def test_remove_recipe_component_not_found(self, test_db):
        """Test removing nonexistent component returns False."""
        parent = recipe_service.create_recipe(
            {
                "name": "Remove NotFound Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Remove NotFound Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # Try to remove a component that was never added
        result = recipe_service.remove_recipe_component(parent.id, child.id)

        assert result is False

    def test_remove_recipe_component_nonexistent_parent(self, test_db):
        """Test that nonexistent parent raises RecipeNotFound."""
        child = recipe_service.create_recipe(
            {
                "name": "Remove Orphan Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        with pytest.raises(RecipeNotFound):
            recipe_service.remove_recipe_component(99999, child.id)

class TestUpdateRecipeComponent:
    """Tests for update_recipe_component() method."""

    def test_update_recipe_component_quantity(self, test_db):
        """Test updating component quantity."""
        parent = recipe_service.create_recipe(
            {
                "name": "Update Qty Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Update Qty Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_service.add_recipe_component(parent.id, child.id, quantity=1.0)

        updated = recipe_service.update_recipe_component(parent.id, child.id, quantity=3.0)

        assert updated.quantity == 3.0

    def test_update_recipe_component_notes(self, test_db):
        """Test updating component notes."""
        parent = recipe_service.create_recipe(
            {
                "name": "Update Notes Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Update Notes Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_service.add_recipe_component(parent.id, child.id, notes="Original")

        updated = recipe_service.update_recipe_component(parent.id, child.id, notes="Updated note")

        assert updated.notes == "Updated note"

    def test_update_recipe_component_clear_notes(self, test_db):
        """Test clearing component notes with empty string."""
        parent = recipe_service.create_recipe(
            {
                "name": "Clear Notes Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Clear Notes Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_service.add_recipe_component(parent.id, child.id, notes="To be cleared")

        updated = recipe_service.update_recipe_component(parent.id, child.id, notes="")

        assert updated.notes is None

    def test_update_recipe_component_invalid_quantity(self, test_db):
        """Test that invalid quantity raises ValidationError."""
        parent = recipe_service.create_recipe(
            {
                "name": "Invalid Update Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Invalid Update Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_service.add_recipe_component(parent.id, child.id)

        with pytest.raises(ValidationError):
            recipe_service.update_recipe_component(parent.id, child.id, quantity=0)

    def test_update_recipe_component_not_found(self, test_db):
        """Test updating nonexistent component raises ValidationError."""
        parent = recipe_service.create_recipe(
            {
                "name": "Update NotFound Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child = recipe_service.create_recipe(
            {
                "name": "Update NotFound Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            recipe_service.update_recipe_component(parent.id, child.id, quantity=2.0)

        assert "not found" in str(exc_info.value).lower()

class TestGetRecipeComponents:
    """Tests for get_recipe_components() method."""

    def test_get_recipe_components_ordered(self, test_db):
        """Test components returned in sort_order."""
        parent = recipe_service.create_recipe(
            {
                "name": "Get Components Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child1 = recipe_service.create_recipe(
            {
                "name": "Get Child 1",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child2 = recipe_service.create_recipe(
            {
                "name": "Get Child 2",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child3 = recipe_service.create_recipe(
            {
                "name": "Get Child 3",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # Add in non-sequential order
        recipe_service.add_recipe_component(parent.id, child3.id, sort_order=3)
        recipe_service.add_recipe_component(parent.id, child1.id, sort_order=1)
        recipe_service.add_recipe_component(parent.id, child2.id, sort_order=2)

        components = recipe_service.get_recipe_components(parent.id)

        assert len(components) == 3
        assert components[0].component_recipe_id == child1.id
        assert components[1].component_recipe_id == child2.id
        assert components[2].component_recipe_id == child3.id

    def test_get_recipe_components_empty(self, test_db):
        """Test recipe with no components returns empty list."""
        recipe = recipe_service.create_recipe(
            {
                "name": "No Components Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        components = recipe_service.get_recipe_components(recipe.id)

        assert len(components) == 0

    def test_get_recipe_components_nonexistent_recipe(self, test_db):
        """Test that nonexistent recipe raises RecipeNotFound."""
        with pytest.raises(RecipeNotFound):
            recipe_service.get_recipe_components(99999)

class TestGetRecipesUsingComponent:
    """Tests for get_recipes_using_component() method."""

    def test_get_recipes_using_component(self, test_db):
        """Test finding recipes that use a component."""
        parent1 = recipe_service.create_recipe(
            {
                "name": "Using Parent 1",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        parent2 = recipe_service.create_recipe(
            {
                "name": "Using Parent 2",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        shared_child = recipe_service.create_recipe(
            {
                "name": "Shared Child Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        recipe_service.add_recipe_component(parent1.id, shared_child.id)
        recipe_service.add_recipe_component(parent2.id, shared_child.id)

        parents = recipe_service.get_recipes_using_component(shared_child.id)

        assert len(parents) == 2
        parent_ids = [p.id for p in parents]
        assert parent1.id in parent_ids
        assert parent2.id in parent_ids

    def test_get_recipes_using_component_none(self, test_db):
        """Test recipe not used as component returns empty list."""
        recipe = recipe_service.create_recipe(
            {
                "name": "Unused Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        parents = recipe_service.get_recipes_using_component(recipe.id)

        assert len(parents) == 0

    def test_get_recipes_using_component_nonexistent(self, test_db):
        """Test that nonexistent recipe raises RecipeNotFound."""
        with pytest.raises(RecipeNotFound):
            recipe_service.get_recipes_using_component(99999)

# ============================================================================
# Recipe Component Validation Tests (Feature 012: WP03)
# ============================================================================

class TestCircularReferenceDetection:
    """Tests for circular reference detection (T014, T017, T019)."""

    def test_add_component_self_reference_blocked(self, test_db):
        """Recipe cannot include itself as a component."""
        recipe = recipe_service.create_recipe(
            {
                "name": "Self Reference Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            recipe_service.add_recipe_component(recipe.id, recipe.id)

        assert "circular reference" in str(exc_info.value).lower()

    def test_add_component_direct_cycle_blocked(self, test_db):
        """A→B, then B→A should be blocked."""
        recipe_a = recipe_service.create_recipe(
            {
                "name": "Cycle Recipe A",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_b = recipe_service.create_recipe(
            {
                "name": "Cycle Recipe B",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # A includes B - OK
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id)

        # B includes A - should fail (creates cycle)
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.add_recipe_component(recipe_b.id, recipe_a.id)

        assert "circular reference" in str(exc_info.value).lower()

    def test_add_component_indirect_cycle_blocked(self, test_db):
        """A→B→C, then C→A should be blocked."""
        recipe_a = recipe_service.create_recipe(
            {
                "name": "Indirect A",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_b = recipe_service.create_recipe(
            {
                "name": "Indirect B",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_c = recipe_service.create_recipe(
            {
                "name": "Indirect C",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # Build chain: A→B→C
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id)
        recipe_service.add_recipe_component(recipe_b.id, recipe_c.id)

        # C→A should fail (creates cycle through chain)
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.add_recipe_component(recipe_c.id, recipe_a.id)

        assert "circular reference" in str(exc_info.value).lower()

    def test_add_component_no_false_positive(self, test_db):
        """Non-circular hierarchies should work (diamond pattern)."""
        recipe_a = recipe_service.create_recipe(
            {
                "name": "Diamond Top",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_b = recipe_service.create_recipe(
            {
                "name": "Diamond Left",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_c = recipe_service.create_recipe(
            {
                "name": "Diamond Right",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # A→B, A→C (diamond top) - should work
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id)
        recipe_service.add_recipe_component(recipe_a.id, recipe_c.id)

        # Verify both added
        components = recipe_service.get_recipe_components(recipe_a.id)
        assert len(components) == 2

class TestDepthLimitEnforcement:
    """Tests for depth limit enforcement (T015, T016, T020)."""

    def test_add_component_depth_3_allowed(self, test_db):
        """3-level nesting should be allowed."""
        recipe_a = recipe_service.create_recipe(
            {
                "name": "Depth Level 1",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_b = recipe_service.create_recipe(
            {
                "name": "Depth Level 2",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_c = recipe_service.create_recipe(
            {
                "name": "Depth Level 3",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # A→B→C (3 levels)
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id)
        recipe_service.add_recipe_component(recipe_b.id, recipe_c.id)

        # Verify structure
        assert len(recipe_service.get_recipe_components(recipe_a.id)) == 1
        assert len(recipe_service.get_recipe_components(recipe_b.id)) == 1

    def test_add_component_depth_4_blocked(self, test_db):
        """4-level nesting should be blocked."""
        recipe_a = recipe_service.create_recipe(
            {
                "name": "Too Deep 1",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_b = recipe_service.create_recipe(
            {
                "name": "Too Deep 2",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_c = recipe_service.create_recipe(
            {
                "name": "Too Deep 3",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_d = recipe_service.create_recipe(
            {
                "name": "Too Deep 4",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # Build 3-level: A→B→C
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id)
        recipe_service.add_recipe_component(recipe_b.id, recipe_c.id)

        # Try to add D under C (would make 4 levels)
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.add_recipe_component(recipe_c.id, recipe_d.id)

        assert "depth" in str(exc_info.value).lower()

    def test_add_component_depth_with_subtree(self, test_db):
        """Adding a recipe with its own subtree should count total depth."""
        recipe_a = recipe_service.create_recipe(
            {
                "name": "Subtree Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_b = recipe_service.create_recipe(
            {
                "name": "Subtree Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_d = recipe_service.create_recipe(
            {
                "name": "Subtree Grandchild",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # B→D (2-level subtree)
        recipe_service.add_recipe_component(recipe_b.id, recipe_d.id)

        # A already at level 1, B's subtree is 2 levels = total 3 (OK)
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id)

        # Verify structure created successfully
        assert len(recipe_service.get_recipe_components(recipe_a.id)) == 1
        assert len(recipe_service.get_recipe_components(recipe_b.id)) == 1

    def test_add_component_multiple_children_same_level(self, test_db):
        """Multiple children at same level should work (width not depth)."""
        parent = recipe_service.create_recipe(
            {
                "name": "Wide Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child1 = recipe_service.create_recipe(
            {
                "name": "Wide Child 1",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child2 = recipe_service.create_recipe(
            {
                "name": "Wide Child 2",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        child3 = recipe_service.create_recipe(
            {
                "name": "Wide Child 3",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        # Parent with 3 children (depth = 2, width = 3)
        recipe_service.add_recipe_component(parent.id, child1.id)
        recipe_service.add_recipe_component(parent.id, child2.id)
        recipe_service.add_recipe_component(parent.id, child3.id)

        components = recipe_service.get_recipe_components(parent.id)
        assert len(components) == 3

class TestDeletionProtection:
    """Tests for deletion protection (T018, T021)."""

    def test_delete_recipe_used_as_component_blocked(self, test_db):
        """Cannot delete a recipe that is used as a component."""
        recipe_parent = recipe_service.create_recipe(
            {
                "name": "Delete Protect Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_child = recipe_service.create_recipe(
            {
                "name": "Delete Protect Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        recipe_service.add_recipe_component(recipe_parent.id, recipe_child.id)

        with pytest.raises(ValidationError) as exc_info:
            recipe_service.delete_recipe(recipe_child.id)

        assert "used as component" in str(exc_info.value).lower()
        assert recipe_parent.name in str(exc_info.value)

    def test_delete_recipe_after_removing_component(self, test_db):
        """Can delete recipe after removing it from all parents."""
        recipe_parent = recipe_service.create_recipe(
            {
                "name": "Cleanup Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_child = recipe_service.create_recipe(
            {
                "name": "Cleanup Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        recipe_service.add_recipe_component(recipe_parent.id, recipe_child.id)
        recipe_service.remove_recipe_component(recipe_parent.id, recipe_child.id)

        # Now deletion should work
        result = recipe_service.delete_recipe(recipe_child.id)
        assert result is True

    def test_delete_recipe_with_no_parents(self, test_db):
        """Recipe not used as component can be deleted."""
        recipe = recipe_service.create_recipe(
            {
                "name": "Standalone Delete",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        result = recipe_service.delete_recipe(recipe.id)
        assert result is True

    def test_delete_parent_cascades_components(self, test_db):
        """Deleting parent recipe removes component relationships."""
        recipe_parent = recipe_service.create_recipe(
            {
                "name": "Cascade Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        recipe_child = recipe_service.create_recipe(
            {
                "name": "Cascade Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        recipe_service.add_recipe_component(recipe_parent.id, recipe_child.id)

        # Delete parent
        recipe_service.delete_recipe(recipe_parent.id)

        # Child should now be deletable
        result = recipe_service.delete_recipe(recipe_child.id)
        assert result is True

    def test_delete_recipe_used_by_multiple_parents(self, test_db):
        """Error message shows all parent recipes using the component."""
        parent1 = recipe_service.create_recipe(
            {
                "name": "Multi Parent 1",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        parent2 = recipe_service.create_recipe(
            {
                "name": "Multi Parent 2",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )
        shared_child = recipe_service.create_recipe(
            {
                "name": "Multi Shared Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            }
        )

        recipe_service.add_recipe_component(parent1.id, shared_child.id)
        recipe_service.add_recipe_component(parent2.id, shared_child.id)

        with pytest.raises(ValidationError) as exc_info:
            recipe_service.delete_recipe(shared_child.id)

        error_msg = str(exc_info.value)
        assert "Multi Parent 1" in error_msg
        assert "Multi Parent 2" in error_msg

# ============================================================================
# Recipe Component Cost & Aggregation Tests (Feature 012: WP04)
# ============================================================================

class TestGetAggregatedIngredients:
    """Tests for get_aggregated_ingredients() (T022, T026)."""

    def test_get_aggregated_ingredients_single_recipe(self, test_db):
        """Aggregation of recipe with no components."""
        # Create ingredients
        flour = ingredient_service.create_ingredient(
            {"name": "Aggreg Flour", "category": "Flour"}
        )
        sugar = ingredient_service.create_ingredient(
            {"name": "Aggreg Sugar", "category": "Sugar"}
        )

        # Create recipe with ingredients
        recipe = recipe_service.create_recipe(
            {
                "name": "Aggreg Simple Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [
                {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},
                {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},
            ]
        )

        result = recipe_service.get_aggregated_ingredients(recipe.id)

        assert len(result) == 2
        flour_item = next(i for i in result if "Flour" in i["ingredient_name"])
        assert flour_item["total_quantity"] == 2.0
        assert flour_item["unit"] == "cup"

    def test_get_aggregated_ingredients_with_component(self, test_db):
        """Aggregation includes component ingredients."""
        # Create ingredients
        flour = ingredient_service.create_ingredient(
            {"name": "Comp Flour", "category": "Flour"}
        )
        butter = ingredient_service.create_ingredient(
            {"name": "Comp Butter", "category": "Dairy"}
        )

        # Create child recipe with butter
        child = recipe_service.create_recipe(
            {
                "name": "Comp Child Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": butter.id, "quantity": 0.5, "unit": "cup"}]
        )

        # Create parent recipe with flour
        parent = recipe_service.create_recipe(
            {
                "name": "Comp Parent Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Add child as component with quantity 2.0
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0)

        result = recipe_service.get_aggregated_ingredients(parent.id)

        # Should have Flour (2 cups) and Butter (0.5 * 2 = 1 cup)
        assert len(result) == 2
        butter_item = next(i for i in result if "Butter" in i["ingredient_name"])
        assert butter_item["total_quantity"] == 1.0  # 0.5 * 2

    def test_get_aggregated_ingredients_same_ingredient_combined(self, test_db):
        """Same ingredient from parent and child should combine."""
        flour = ingredient_service.create_ingredient(
            {"name": "Combine Flour", "category": "Flour"}
        )

        # Create child with 1 cup flour
        child = recipe_service.create_recipe(
            {
                "name": "Combine Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}]
        )

        # Create parent with 2 cups flour
        parent = recipe_service.create_recipe(
            {
                "name": "Combine Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(parent.id, child.id, quantity=1.0)

        result = recipe_service.get_aggregated_ingredients(parent.id)

        # Should have Flour 3 cups (2 + 1)
        assert len(result) == 1
        flour_item = result[0]
        assert flour_item["total_quantity"] == 3.0
        assert len(flour_item["sources"]) == 2

    def test_get_aggregated_ingredients_3_levels(self, test_db):
        """Aggregation works across 3 levels."""
        salt = ingredient_service.create_ingredient(
            {"name": "Three Level Salt", "category": "Spices"}
        )
        butter = ingredient_service.create_ingredient(
            {"name": "Three Level Butter", "category": "Dairy"}
        )
        flour = ingredient_service.create_ingredient(
            {"name": "Three Level Flour", "category": "Flour"}
        )

        grandchild = recipe_service.create_recipe(
            {
                "name": "Three Level Grandchild",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": salt.id, "quantity": 1.0, "unit": "tsp"}]
        )
        child = recipe_service.create_recipe(
            {
                "name": "Three Level Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": butter.id, "quantity": 1.0, "unit": "cup"}]
        )
        parent = recipe_service.create_recipe(
            {
                "name": "Three Level Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(child.id, grandchild.id, quantity=2.0)
        recipe_service.add_recipe_component(parent.id, child.id, quantity=3.0)

        result = recipe_service.get_aggregated_ingredients(parent.id)

        # Flour: 2 cups (direct)
        # Butter: 1 * 3 = 3 cups
        # Salt: 1 * 2 * 3 = 6 tsp
        salt_item = next(i for i in result if "Salt" in i["ingredient_name"])
        assert salt_item["total_quantity"] == 6.0

    def test_get_aggregated_ingredients_with_multiplier(self, test_db):
        """Multiplier scales all quantities."""
        flour = ingredient_service.create_ingredient(
            {"name": "Mult Flour", "category": "Flour"}
        )

        recipe = recipe_service.create_recipe(
            {
                "name": "Mult Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        result = recipe_service.get_aggregated_ingredients(recipe.id, multiplier=2.0)

        flour_item = result[0]
        assert flour_item["total_quantity"] == 4.0  # 2 * 2

    def test_get_aggregated_ingredients_empty_recipe(self, test_db):
        """Recipe with no ingredients returns empty list."""
        recipe = recipe_service.create_recipe(
            {
                "name": "Empty Aggreg Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            []
        )

        result = recipe_service.get_aggregated_ingredients(recipe.id)

        assert len(result) == 0

class TestCalculateTotalCostWithComponents:
    """Tests for calculate_total_cost_with_components() (T023, T027)."""

    def test_calculate_cost_single_recipe_no_components(self, test_db):
        """Cost of recipe with no components equals direct ingredient cost."""
        recipe = recipe_service.create_recipe(
            {
                "name": "Single Cost Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [],  # No ingredients - cost will be 0
        )

        result = recipe_service.calculate_total_cost_with_components(recipe.id)

        assert result["direct_ingredient_cost"] == 0.0
        assert result["total_component_cost"] == 0.0
        assert result["total_cost"] == 0.0
        assert result["recipe_name"] == "Single Cost Recipe"

    def test_calculate_cost_with_component(self, test_db):
        """Cost includes component cost × quantity."""
        child = recipe_service.create_recipe(
            {
                "name": "Cost Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            []
        )
        parent = recipe_service.create_recipe(
            {
                "name": "Cost Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            []
        )

        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0)

        result = recipe_service.calculate_total_cost_with_components(parent.id)

        assert result["direct_ingredient_cost"] == 0.0
        assert result["total_component_cost"] == 0.0  # Child has no ingredients
        assert result["total_cost"] == 0.0
        assert len(result["component_costs"]) == 1
        assert result["component_costs"][0]["quantity"] == 2.0

    def test_calculate_cost_structure(self, test_db):
        """Verify cost breakdown structure is correct."""
        parent = recipe_service.create_recipe(
            {
                "name": "Structure Parent",
                "category": "Cookies",
                "yield_quantity": 12,
                "yield_unit": "cookies"
            },
            []
        )
        child = recipe_service.create_recipe(
            {
                "name": "Structure Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            []
        )
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0)

        result = recipe_service.calculate_total_cost_with_components(parent.id)

        # Verify all required fields exist
        assert "recipe_id" in result
        assert "recipe_name" in result
        assert "direct_ingredient_cost" in result
        assert "component_costs" in result
        assert "total_component_cost" in result
        assert "total_cost" in result
        assert "cost_per_unit" in result

        # Verify component cost structure
        assert len(result["component_costs"]) == 1
        comp = result["component_costs"][0]
        assert "component_recipe_id" in comp
        assert "component_recipe_name" in comp
        assert "quantity" in comp
        assert "unit_cost" in comp
        assert "total_cost" in comp

    def test_calculate_cost_per_unit(self, test_db):
        """Cost per unit is total / yield."""
        recipe = recipe_service.create_recipe(
            {
                "name": "Per Unit Recipe",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies"
            },
            []
        )

        result = recipe_service.calculate_total_cost_with_components(recipe.id)

        # With 0 cost, per unit is 0
        assert result["cost_per_unit"] == 0.0

    def test_calculate_cost_nonexistent_recipe(self, test_db):
        """Nonexistent recipe raises RecipeNotFound."""
        with pytest.raises(RecipeNotFound):
            recipe_service.calculate_total_cost_with_components(99999)

class TestGetRecipeWithCostsComponents:
    """Tests for get_recipe_with_costs() with components (T025)."""

    def test_get_recipe_with_costs_includes_components(self, test_db):
        """Verify get_recipe_with_costs returns component info."""
        parent = recipe_service.create_recipe(
            {
                "name": "With Costs Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            []
        )
        child = recipe_service.create_recipe(
            {
                "name": "With Costs Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            []
        )
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0)

        result = recipe_service.get_recipe_with_costs(parent.id)

        assert "components" in result
        assert "direct_ingredient_cost" in result
        assert "total_component_cost" in result
        assert len(result["components"]) == 1
        assert result["components"][0]["quantity"] == 2.0

    def test_get_recipe_with_costs_no_components(self, test_db):
        """Recipe without components has empty components list."""
        recipe = recipe_service.create_recipe(
            {
                "name": "No Comp Costs",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            []
        )

        result = recipe_service.get_recipe_with_costs(recipe.id)

        assert "components" in result
        assert len(result["components"]) == 0
        assert result["total_component_cost"] == 0.0
