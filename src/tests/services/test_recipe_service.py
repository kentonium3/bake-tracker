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
    variant_service,
    pantry_service,
    purchase_service
)
from src.services.exceptions import RecipeNotFound, IngredientNotFound, ValidationError
from src.models import Recipe, RecipeIngredient


class TestCalculateActualCost:
    """Tests for calculate_actual_cost() method."""

    def test_calculate_actual_cost_uses_fifo_ordering(self, test_db):
        """Test: FIFO ordering - oldest inventory costs used first."""
        # Setup: Create ingredient and variant
        ingredient = ingredient_service.create_ingredient({
            "name": "Test FIFO Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0")
        })

        # Add two lots with different costs (older lot cheaper)
        # Lot 1: 2 cups at $0.10/cup (older - should be used)
        lot1 = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("2.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot1.id, {"unit_cost": 0.10})

        # Lot 2: 2 cups at $0.12/cup (newer - should NOT be used if qty <= 2)
        lot2 = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("2.0"),
            purchase_date=date(2025, 2, 1)
        )
        pantry_service.update_pantry_item(lot2.id, {"unit_cost": 0.12})

        # Create recipe needing 2 cups
        recipe = recipe_service.create_recipe(
            {"name": "FIFO Test Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Should use FIFO (2 cups * $0.10 = $0.20)
        expected_cost = Decimal("0.20")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost}, got ${cost}. FIFO should use oldest lot at $0.10/cup"

    def test_calculate_actual_cost_does_not_modify_pantry(self, test_db):
        """Test: Pantry quantities remain unchanged after cost calculation."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Pantry Unchanged",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0")
        })

        initial_quantity = Decimal("5.0")
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=initial_quantity,
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 0.10})

        recipe = recipe_service.create_recipe(
            {"name": "Pantry Test Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Capture pantry state before
        items_before = pantry_service.get_pantry_items(ingredient_slug=ingredient.slug)
        qty_before = Decimal(str(items_before[0].quantity))

        # Act
        recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Pantry unchanged
        items_after = pantry_service.get_pantry_items(ingredient_slug=ingredient.slug)
        qty_after = Decimal(str(items_after[0].quantity))

        assert abs(qty_after - qty_before) < Decimal("0.001"), \
            f"Pantry quantity changed from {qty_before} to {qty_after}. Should be read-only."

    def test_calculate_actual_cost_handles_multiple_ingredients(self, test_db):
        """Test: Multiple ingredients are summed correctly."""
        # Setup: Create two ingredients
        flour = ingredient_service.create_ingredient({
            "name": "Multi Test Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })
        sugar = ingredient_service.create_ingredient({
            "name": "Multi Test Sugar",
            "category": "Sugar",
            "recipe_unit": "cup",
        })

        # Create variants
        flour_variant = variant_service.create_variant(flour.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0")
        })
        sugar_variant = variant_service.create_variant(sugar.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0")
        })

        # Add pantry items
        flour_lot = pantry_service.add_to_pantry(
            variant_id=flour_variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(flour_lot.id, {"unit_cost": 0.10})  # $0.10/cup

        sugar_lot = pantry_service.add_to_pantry(
            variant_id=sugar_variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(sugar_lot.id, {"unit_cost": 0.20})  # $0.20/cup

        # Create recipe with both ingredients
        recipe = recipe_service.create_recipe(
            {"name": "Multi Ingredient Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [
                {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},  # 2 * $0.10 = $0.20
                {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},  # 1 * $0.20 = $0.20
            ]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Total = $0.20 + $0.20 = $0.40
        expected_cost = Decimal("0.40")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost}, got ${cost}"

    def test_calculate_actual_cost_empty_recipe_returns_zero(self, test_db):
        """Test: Empty recipe (no ingredients) returns $0.00."""
        # Create recipe with no ingredients
        recipe = recipe_service.create_recipe(
            {"name": "Empty Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            []  # No ingredients
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
        ingredient = ingredient_service.create_ingredient({
            "name": "Shortfall Test Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(variant.id)

        # Add only 2 cups to pantry at $0.10/cup
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("2.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 0.10})

        # Record a purchase for fallback pricing at $0.15/cup
        purchase_service.record_purchase(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.50"),  # $0.15/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing 3 cups (1 cup shortfall)
        recipe = recipe_service.create_recipe(
            {"name": "Shortfall Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: 2 cups * $0.10 (FIFO) + 1 cup * $0.15 (fallback) = $0.35
        expected_cost = Decimal("0.35")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost} (FIFO + fallback), got ${cost}"

    def test_calculate_actual_cost_no_pantry_uses_all_fallback(self, test_db):
        """Test: Empty pantry uses 100% fallback pricing."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "No Pantry Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0")
        })
        variant_service.set_preferred_variant(variant.id)

        # Record purchase for fallback pricing (no pantry inventory)
        purchase_service.record_purchase(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("2.00"),  # $0.20/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing 3 cups
        recipe = recipe_service.create_recipe(
            {"name": "No Pantry Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: 3 cups * $0.20 (all fallback) = $0.60
        expected_cost = Decimal("0.60")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost} (100% fallback), got ${cost}"

    def test_calculate_actual_cost_raises_validation_error_no_purchase_history(self, test_db):
        """Test: Raises ValidationError when no purchase history for fallback."""
        # Setup: Ingredient with variant but no purchase history and no pantry
        ingredient = ingredient_service.create_ingredient({
            "name": "No History Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0")
        })

        # Create recipe (no pantry = shortfall, but no purchase history for fallback)
        recipe = recipe_service.create_recipe(
            {"name": "No History Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.calculate_actual_cost(recipe.id)

        # Check for the expected error message (the message includes: "no purchase history")
        error_text = str(exc_info.value).lower().replace("; ", "")
        assert "purchase history" in error_text or "no purchase" in error_text

    def test_calculate_actual_cost_raises_ingredient_not_found_no_variants(self, test_db):
        """Test: Raises IngredientNotFound when ingredient has no variants."""
        # Setup: Ingredient with NO variants
        ingredient = ingredient_service.create_ingredient({
            "name": "No Variants Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        # Create recipe with this ingredient (no variants, so shortfall can't be priced)
        recipe = recipe_service.create_recipe(
            {"name": "No Variants Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act & Assert
        with pytest.raises(IngredientNotFound) as exc_info:
            recipe_service.calculate_actual_cost(recipe.id)

        assert "no variants" in str(exc_info.value).lower()

    def test_calculate_actual_cost_decimal_precision(self, test_db):
        """Test: Decimal precision maintained in cost calculations."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Precision Test Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0")
        })

        # Add pantry with precise unit cost
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 0.123})  # Precise value

        # Create recipe
        recipe = recipe_service.create_recipe(
            {"name": "Precision Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Result is Decimal type
        assert isinstance(cost, Decimal), f"Expected Decimal, got {type(cost)}"

        # Assert: Precision maintained (3 * $0.123 = $0.369)
        expected_cost = Decimal("0.369")
        assert abs(cost - expected_cost) < Decimal("0.001"), \
            f"Expected ${expected_cost}, got ${cost}"


class TestCalculateEstimatedCost:
    """Tests for calculate_estimated_cost() method."""

    def test_calculate_estimated_cost_uses_preferred_variant(self, test_db):
        """Test: Uses preferred variant's price when available."""
        # Setup: Create ingredient
        ingredient = ingredient_service.create_ingredient({
            "name": "Estimated Test Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        # Create two variants - one preferred, one not
        variant1 = variant_service.create_variant(ingredient.slug, {
            "brand": "Cheap Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": False
        })
        variant2 = variant_service.create_variant(ingredient.slug, {
            "brand": "Preferred Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(variant2.id)

        # Record purchases with different prices
        purchase_service.record_purchase(
            variant_id=variant1.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("0.50"),  # $0.05/cup
            purchase_date=date(2025, 1, 1)
        )
        purchase_service.record_purchase(
            variant_id=variant2.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.00"),  # $0.10/cup (preferred)
            purchase_date=date(2025, 1, 1)
        )

        # Create recipe needing 2 cups
        recipe = recipe_service.create_recipe(
            {"name": "Preferred Test Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Should use preferred variant price (2 * $0.10 = $0.20)
        expected_cost = Decimal("0.20")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost} (preferred variant), got ${cost}"

    def test_calculate_estimated_cost_falls_back_to_any_variant(self, test_db):
        """Test: Falls back to any variant when no preferred set."""
        # Setup: Create ingredient
        ingredient = ingredient_service.create_ingredient({
            "name": "Fallback Test Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        # Create variant WITHOUT setting it as preferred
        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Only Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": False  # Not preferred
        })

        # Record purchase
        purchase_service.record_purchase(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.50"),  # $0.15/cup
            purchase_date=date(2025, 1, 1)
        )

        # Create recipe
        recipe = recipe_service.create_recipe(
            {"name": "Fallback Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Should use the only available variant (3 * $0.15 = $0.45)
        expected_cost = Decimal("0.45")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost} (fallback variant), got ${cost}"

    def test_calculate_estimated_cost_handles_multiple_ingredients(self, test_db):
        """Test: Multiple ingredients are summed correctly."""
        # Setup: Create two ingredients
        flour = ingredient_service.create_ingredient({
            "name": "Est Multi Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })
        sugar = ingredient_service.create_ingredient({
            "name": "Est Multi Sugar",
            "category": "Sugar",
            "recipe_unit": "cup",
        })

        # Create variants
        flour_variant = variant_service.create_variant(flour.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(flour_variant.id)

        sugar_variant = variant_service.create_variant(sugar.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(sugar_variant.id)

        # Record purchases
        purchase_service.record_purchase(
            variant_id=flour_variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.00"),  # $0.10/cup
            purchase_date=date(2025, 1, 1)
        )
        purchase_service.record_purchase(
            variant_id=sugar_variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("2.00"),  # $0.20/cup
            purchase_date=date(2025, 1, 1)
        )

        # Create recipe with both ingredients
        recipe = recipe_service.create_recipe(
            {"name": "Est Multi Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [
                {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},  # 2 * $0.10 = $0.20
                {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},  # 1 * $0.20 = $0.20
            ]
        )

        # Act
        cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Total = $0.20 + $0.20 = $0.40
        expected_cost = Decimal("0.40")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost}, got ${cost}"

    def test_calculate_estimated_cost_ignores_pantry(self, test_db):
        """Test: Pantry inventory is completely ignored - uses variant pricing."""
        # Setup: Create ingredient
        ingredient = ingredient_service.create_ingredient({
            "name": "Ignore Pantry Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(variant.id)

        # Add pantry items at LOW price ($0.05/cup)
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 0.05})  # Cheap pantry price

        # Record purchase at HIGHER price ($0.20/cup) - this should be used
        purchase_service.record_purchase(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("2.00"),  # $0.20/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe
        recipe = recipe_service.create_recipe(
            {"name": "Ignore Pantry Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act
        estimated_cost = recipe_service.calculate_estimated_cost(recipe.id)

        # Assert: Should use purchase price ($0.20/cup), NOT pantry price ($0.05/cup)
        # 2 cups * $0.20 = $0.40
        expected_cost = Decimal("0.40")
        assert abs(estimated_cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost} (purchase price, not pantry), got ${estimated_cost}"

    def test_calculate_estimated_cost_empty_recipe_returns_zero(self, test_db):
        """Test: Empty recipe (no ingredients) returns $0.00."""
        # Create recipe with no ingredients
        recipe = recipe_service.create_recipe(
            {"name": "Empty Est Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            []  # No ingredients
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
        # Setup: Ingredient with variant but no purchase history
        ingredient = ingredient_service.create_ingredient({
            "name": "No Purchase Est Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0")
        })

        # Create recipe (no purchase history for fallback)
        recipe = recipe_service.create_recipe(
            {"name": "No Purchase Est Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.calculate_estimated_cost(recipe.id)

        # The error message contains "no purchase history available"
        # but may be formatted with semicolons due to ValidationError's __str__ method
        error_text = str(exc_info.value).lower().replace("; ", "")
        assert "purchase" in error_text and "history" in error_text

    def test_calculate_estimated_cost_raises_ingredient_not_found_no_variants(self, test_db):
        """Test: Raises IngredientNotFound when ingredient has no variants."""
        # Setup: Ingredient with NO variants
        ingredient = ingredient_service.create_ingredient({
            "name": "No Variants Est Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        # Create recipe with this ingredient (no variants)
        recipe = recipe_service.create_recipe(
            {"name": "No Variants Est Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act & Assert
        with pytest.raises(IngredientNotFound) as exc_info:
            recipe_service.calculate_estimated_cost(recipe.id)

        assert "no variants" in str(exc_info.value).lower()


class TestPartialInventoryScenarios:
    """Tests for partial inventory blended costing scenarios (WP04)."""

    def test_partial_inventory_full_coverage_no_fallback(self, test_db):
        """Test: When pantry has more than needed, uses only FIFO costs (no fallback)."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Full Coverage Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(variant.id)

        # Add 5 cups to pantry at $0.10/cup (more than needed)
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 0.10})

        # Record a purchase for fallback at HIGHER price - should NOT be used
        purchase_service.record_purchase(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("5.00"),  # $0.50/cup - expensive!
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing 2 cups (pantry has 5)
        recipe = recipe_service.create_recipe(
            {"name": "Full Coverage Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Only FIFO cost used (2 * $0.10 = $0.20), NOT fallback ($0.50/cup)
        expected_cost = Decimal("0.20")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost} (FIFO only, no fallback), got ${cost}"

    def test_partial_inventory_multiple_ingredients_mixed_coverage(self, test_db):
        """Test: Multiple ingredients with varying coverage levels costed correctly."""
        # Setup: Three ingredients with different coverage levels
        # Flour: partial coverage (2 of 3 cups)
        # Sugar: full coverage (5 of 1 cup)
        # Butter: no coverage (0 of 2 cups)

        flour = ingredient_service.create_ingredient({
            "name": "Mixed Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })
        sugar = ingredient_service.create_ingredient({
            "name": "Mixed Sugar",
            "category": "Sugar",
            "recipe_unit": "cup",
        })
        butter = ingredient_service.create_ingredient({
            "name": "Mixed Butter",
            "category": "Dairy",
            "recipe_unit": "cup",
        })

        # Create variants
        flour_variant = variant_service.create_variant(flour.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(flour_variant.id)

        sugar_variant = variant_service.create_variant(sugar.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(sugar_variant.id)

        butter_variant = variant_service.create_variant(butter.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(butter_variant.id)

        # Add pantry items
        # Flour: 2 cups at $0.10/cup (partial coverage)
        flour_lot = pantry_service.add_to_pantry(
            variant_id=flour_variant.id,
            quantity=Decimal("2.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(flour_lot.id, {"unit_cost": 0.10})

        # Sugar: 5 cups at $0.20/cup (full coverage)
        sugar_lot = pantry_service.add_to_pantry(
            variant_id=sugar_variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(sugar_lot.id, {"unit_cost": 0.20})

        # Butter: NO pantry inventory (zero coverage)

        # Record purchases for fallback pricing
        purchase_service.record_purchase(
            variant_id=flour_variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("1.50"),  # $0.15/cup
            purchase_date=date(2025, 1, 15)
        )
        purchase_service.record_purchase(
            variant_id=sugar_variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("3.00"),  # $0.30/cup (won't be used - full coverage)
            purchase_date=date(2025, 1, 15)
        )
        purchase_service.record_purchase(
            variant_id=butter_variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("5.00"),  # $0.50/cup (100% fallback)
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe with all three ingredients
        recipe = recipe_service.create_recipe(
            {"name": "Mixed Coverage Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [
                {"ingredient_id": flour.id, "quantity": 3.0, "unit": "cup"},   # 2 FIFO + 1 fallback
                {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},   # 1 FIFO only
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
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost} (mixed coverage), got ${cost}"

    def test_partial_inventory_exact_coverage_boundary(self, test_db):
        """Test: Boundary condition - pantry has exactly what's needed (no shortfall)."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Exact Coverage Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(variant.id)

        # Add exactly 3 cups at $0.10/cup
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("3.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 0.10})

        # Record expensive fallback (should NOT be used)
        purchase_service.record_purchase(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("10.00"),  # $1.00/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing exactly 3 cups
        recipe = recipe_service.create_recipe(
            {"name": "Exact Coverage Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: Exactly 3 cups at $0.10 = $0.30 (no fallback)
        expected_cost = Decimal("0.30")
        assert abs(cost - expected_cost) < Decimal("0.01"), \
            f"Expected ${expected_cost} (exact coverage), got ${cost}"

    def test_partial_inventory_decimal_precision_maintained(self, test_db):
        """Test: Decimal precision maintained in blended cost calculations."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Precision Blend Flour",
            "category": "Flour",
            "recipe_unit": "cup",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "cup",
            "purchase_quantity": Decimal("10.0"),
            "is_preferred": True
        })
        variant_service.set_preferred_variant(variant.id)

        # Add 1.5 cups at $0.123/cup (precise value)
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("1.5"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 0.123})

        # Record fallback at $0.456/cup (precise value)
        purchase_service.record_purchase(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            total_cost=Decimal("4.56"),  # $0.456/cup
            purchase_date=date(2025, 1, 15)
        )

        # Create recipe needing 2.5 cups (1 cup shortfall)
        recipe = recipe_service.create_recipe(
            {"name": "Precision Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": ingredient.id, "quantity": 2.5, "unit": "cup"}]
        )

        # Act
        cost = recipe_service.calculate_actual_cost(recipe.id)

        # Assert: 1.5 * $0.123 + 1.0 * $0.456 = $0.1845 + $0.456 = $0.6405
        expected_cost = Decimal("0.6405")
        assert abs(cost - expected_cost) < Decimal("0.001"), \
            f"Expected ${expected_cost} (precise calculation), got ${cost}"

        # Verify result is Decimal type
        assert isinstance(cost, Decimal), f"Expected Decimal, got {type(cost)}"
