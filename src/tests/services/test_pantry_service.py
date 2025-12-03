"""Tests for PantryService, focusing on dry_run functionality and FIFO costing.

Tests cover:
- dry_run=True does not modify inventory
- dry_run=True returns correct cost calculations
- dry_run=False (default) behaves as before (backward compatibility)
- unit_cost field in breakdown items
- FIFO order is respected in both modes
"""

import pytest
from decimal import Decimal
from datetime import date

from src.services import (
    ingredient_service,
    variant_service,
    pantry_service,
    purchase_service
)


class TestConsumeFifoDryRun:
    """Tests for consume_fifo() dry_run parameter."""

    def test_consume_fifo_dry_run_does_not_modify_inventory(self, test_db):
        """Test: dry_run=True does not change pantry quantities."""
        # Setup: Create ingredient, variant, and pantry item
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Flour DR",
            "category": "Flour",
            "recipe_unit": "lb",  # Same as purchase_unit for simplicity
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        })

        # Add pantry item with known quantity
        initial_quantity = Decimal("10.0")
        pantry_item = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=initial_quantity,
            purchase_date=date(2025, 1, 1)
        )

        # Act: Call consume_fifo with dry_run=True
        result = pantry_service.consume_fifo(
            ingredient.slug,
            Decimal("3.0"),
            dry_run=True
        )

        # Assert: Quantity unchanged
        items = pantry_service.get_pantry_items(ingredient_slug=ingredient.slug)
        assert len(items) == 1
        assert abs(Decimal(str(items[0].quantity)) - initial_quantity) < Decimal("0.001"), \
            f"Expected quantity {initial_quantity}, got {items[0].quantity}"

        # Also verify the result shows consumption was calculated
        assert result["satisfied"] is True
        assert abs(result["consumed"] - Decimal("3.0")) < Decimal("0.001")

    def test_consume_fifo_dry_run_returns_correct_cost(self, test_db):
        """Test: dry_run=True returns correct total_cost based on FIFO."""
        # Setup: Create ingredient and variant
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Flour Cost",
            "category": "Flour",
            "recipe_unit": "lb",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        })

        # Add two pantry items with different unit costs
        # Lot 1: 5 lb at $2.00/lb (older - should be consumed first)
        lot1 = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 1, 1)
        )
        # Set unit_cost directly on the pantry item
        pantry_service.update_pantry_item(lot1.id, {"unit_cost": 2.00})

        # Lot 2: 5 lb at $3.00/lb (newer)
        lot2 = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 2, 1)
        )
        pantry_service.update_pantry_item(lot2.id, {"unit_cost": 3.00})

        # Act: Consume 7 lb (5 from lot1 @ $2, 2 from lot2 @ $3)
        # Expected cost: (5 * $2.00) + (2 * $3.00) = $10.00 + $6.00 = $16.00
        result = pantry_service.consume_fifo(
            ingredient.slug,
            Decimal("7.0"),
            dry_run=True
        )

        # Assert: Cost is correct
        expected_cost = Decimal("16.00")
        assert abs(result["total_cost"] - expected_cost) < Decimal("0.01"), \
            f"Expected total_cost {expected_cost}, got {result['total_cost']}"

    def test_consume_fifo_dry_run_includes_unit_cost_in_breakdown(self, test_db):
        """Test: Each breakdown item includes unit_cost field."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Flour Breakdown",
            "category": "Flour",
            "recipe_unit": "lb",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        })

        # Add pantry item with unit_cost
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 2.50})

        # Act
        result = pantry_service.consume_fifo(
            ingredient.slug,
            Decimal("3.0"),
            dry_run=True
        )

        # Assert: Breakdown items have unit_cost
        assert len(result["breakdown"]) >= 1
        for item in result["breakdown"]:
            assert "unit_cost" in item, "Breakdown item missing unit_cost field"
            assert item["unit_cost"] == Decimal("2.50"), \
                f"Expected unit_cost 2.50, got {item['unit_cost']}"

    def test_consume_fifo_default_still_modifies_inventory(self, test_db):
        """Test: dry_run=False (default) updates pantry quantities (backward compatibility)."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Flour Default",
            "category": "Flour",
            "recipe_unit": "lb",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        })

        initial_quantity = Decimal("10.0")
        pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=initial_quantity,
            purchase_date=date(2025, 1, 1)
        )

        # Act: Call consume_fifo WITHOUT dry_run (default=False)
        consume_amount = Decimal("3.0")
        result = pantry_service.consume_fifo(
            ingredient.slug,
            consume_amount
            # dry_run defaults to False
        )

        # Assert: Quantity WAS changed
        items = pantry_service.get_pantry_items(ingredient_slug=ingredient.slug)
        assert len(items) == 1
        expected_remaining = initial_quantity - consume_amount
        assert abs(Decimal(str(items[0].quantity)) - expected_remaining) < Decimal("0.001"), \
            f"Expected quantity {expected_remaining}, got {items[0].quantity}"

    def test_consume_fifo_dry_run_respects_fifo_order(self, test_db):
        """Test: dry_run mode respects FIFO ordering (oldest lots consumed first)."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Flour FIFO Order",
            "category": "Flour",
            "recipe_unit": "lb",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        })

        # Add lots in non-chronological order but with explicit dates
        # Lot 2 added first but has later date
        lot2 = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 2, 1)  # Newer
        )
        pantry_service.update_pantry_item(lot2.id, {"unit_cost": 3.00})

        # Lot 1 added second but has earlier date (should be consumed first)
        lot1 = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 1, 1)  # Older
        )
        pantry_service.update_pantry_item(lot1.id, {"unit_cost": 2.00})

        # Act: Consume 3 lb (should come from lot1, the older one)
        result = pantry_service.consume_fifo(
            ingredient.slug,
            Decimal("3.0"),
            dry_run=True
        )

        # Assert: Consumption came from older lot (lot1)
        assert len(result["breakdown"]) == 1
        assert result["breakdown"][0]["lot_date"] == date(2025, 1, 1), \
            f"Expected consumption from oldest lot (2025-01-01), got {result['breakdown'][0]['lot_date']}"
        assert result["breakdown"][0]["unit_cost"] == Decimal("2.00"), \
            "Should have used the $2.00/lb lot (oldest)"

    def test_consume_fifo_dry_run_total_cost_zero_when_no_unit_cost(self, test_db):
        """Test: total_cost handles items without unit_cost (defaults to 0)."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Flour No Cost",
            "category": "Flour",
            "recipe_unit": "lb",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        })

        # Add pantry item WITHOUT setting unit_cost
        pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            purchase_date=date(2025, 1, 1)
        )

        # Act
        result = pantry_service.consume_fifo(
            ingredient.slug,
            Decimal("3.0"),
            dry_run=True
        )

        # Assert: total_cost should be 0 (no unit_cost set)
        assert result["total_cost"] == Decimal("0.0"), \
            f"Expected total_cost 0.0 when unit_cost not set, got {result['total_cost']}"

    def test_consume_fifo_dry_run_partial_lot_cost_calculation(self, test_db):
        """Test: Partial consumption from a lot calculates cost correctly."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Flour Partial",
            "category": "Flour",
            "recipe_unit": "lb",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        })

        # Add pantry item: 10 lb at $2.50/lb
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("10.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 2.50})

        # Act: Consume 4 lb (partial - should cost 4 * $2.50 = $10.00)
        result = pantry_service.consume_fifo(
            ingredient.slug,
            Decimal("4.0"),
            dry_run=True
        )

        # Assert
        expected_cost = Decimal("10.00")
        assert abs(result["total_cost"] - expected_cost) < Decimal("0.01"), \
            f"Expected total_cost {expected_cost}, got {result['total_cost']}"

        # Also verify remaining_in_lot is calculated correctly for dry_run
        assert abs(result["breakdown"][0]["remaining_in_lot"] - Decimal("6.0")) < Decimal("0.001"), \
            f"Expected remaining_in_lot 6.0, got {result['breakdown'][0]['remaining_in_lot']}"

    def test_consume_fifo_dry_run_with_shortfall(self, test_db):
        """Test: dry_run handles shortfall scenario correctly."""
        # Setup
        ingredient = ingredient_service.create_ingredient({
            "name": "Test Flour Shortfall",
            "category": "Flour",
            "recipe_unit": "lb",
        })

        variant = variant_service.create_variant(ingredient.slug, {
            "brand": "Test Brand",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0")
        })

        # Add only 5 lb at $2.00/lb
        lot = pantry_service.add_to_pantry(
            variant_id=variant.id,
            quantity=Decimal("5.0"),
            purchase_date=date(2025, 1, 1)
        )
        pantry_service.update_pantry_item(lot.id, {"unit_cost": 2.00})

        # Act: Try to consume 8 lb (more than available)
        result = pantry_service.consume_fifo(
            ingredient.slug,
            Decimal("8.0"),
            dry_run=True
        )

        # Assert
        assert result["satisfied"] is False
        assert abs(result["consumed"] - Decimal("5.0")) < Decimal("0.001"), \
            "Should have consumed all available (5 lb)"
        assert abs(result["shortfall"] - Decimal("3.0")) < Decimal("0.001"), \
            "Shortfall should be 3 lb"
        # Cost should be for consumed portion only (5 * $2.00 = $10.00)
        assert abs(result["total_cost"] - Decimal("10.00")) < Decimal("0.01"), \
            f"Expected total_cost $10.00 for consumed portion, got {result['total_cost']}"

        # Verify inventory unchanged after dry_run
        items = pantry_service.get_pantry_items(ingredient_slug=ingredient.slug)
        assert abs(Decimal(str(items[0].quantity)) - Decimal("5.0")) < Decimal("0.001"), \
            "Pantry quantity should be unchanged after dry_run"
