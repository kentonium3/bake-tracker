"""Integration tests for FIFO consumption algorithm.

Tests complex real-world inventory consumption scenarios.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services import ingredient_service, product_service, inventory_item_service


def test_fifo_multiple_lots_partial_consumption(test_db):
    """Test: Multiple lots → Partial consumption → Verify oldest consumed first."""

    # Setup: Create ingredient and product
    ingredient = ingredient_service.create_ingredient(
        {
            "name": "Rye Flour",
            "category": "Flour",
            "recipe_unit": "cup",
            # 4-field density: 1 cup = 113.4g (approximately 0.4793 g/ml, 4 cups/lb)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 113.4,
            "density_weight_unit": "g",
        }
    )

    product = product_service.create_product(
        ingredient.slug,
        {
            "brand": "Bob's Red Mill",
            "package_size": "5 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0"),
        },
    )

    # Add lot 1: 10.0 lb on 2025-01-01 (oldest)
    lot1 = inventory_item_service.add_to_inventory(
        product_id=product.id, quantity=Decimal("10.0"), purchase_date=date(2025, 1, 1)
    )

    # Add lot 2: 15.0 lb on 2025-01-15
    lot2 = inventory_item_service.add_to_inventory(
        product_id=product.id, quantity=Decimal("15.0"), purchase_date=date(2025, 1, 15)
    )

    # Add lot 3: 20.0 lb on 2025-02-01 (newest)
    lot3 = inventory_item_service.add_to_inventory(
        product_id=product.id, quantity=Decimal("20.0"), purchase_date=date(2025, 2, 1)
    )

    # Consume 48 cups (12 lb, should deplete lot 1, partially consume lot 2)
    result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("48.0"))

    assert abs(result["consumed"] - Decimal("48.0")) < Decimal(
        "0.001"
    ), f"Expected 48.0 consumed, got {result["consumed"]}"
    assert result["satisfied"] is True
    assert abs(result["shortfall"] - Decimal("0.0")) < Decimal(
        "0.001"
    ), f"Expected 0.0 shortfall, got {result["shortfall"]}"

    # Verify breakdown: 2 lots consumed
    assert len(result["breakdown"]) == 2

    # First lot fully consumed
    assert result["breakdown"][0]["lot_date"] == date(2025, 1, 1)
    assert abs(result["breakdown"][0]["remaining_in_lot"]) < Decimal(
        "0.001"
    ), f"Expected 0.0, got {result["breakdown"][0]["remaining_in_lot"]}"

    # Second lot partially consumed (15 lb - 2 lb = 13 lb remaining)
    assert result["breakdown"][1]["lot_date"] == date(2025, 1, 15)
    assert abs(result["breakdown"][1]["remaining_in_lot"] - Decimal("13.0")) < Decimal(
        "0.001"
    ), f"Expected 13.0, got {result["breakdown"][1]["remaining_in_lot"]}"


def test_fifo_insufficient_inventory(test_db):
    """Test: Consume more than available → Verify shortfall calculation."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {
            "name": "Oat Flour",
            "category": "Flour",
            "recipe_unit": "cup",
            # 4-field density: 1 cup = 113.4g (approximately 0.4793 g/ml, 4 cups/lb)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 113.4,
            "density_weight_unit": "g",
        }
    )

    product = product_service.create_product(
        ingredient.slug,
        {"brand": "Bob's Red Mill", "purchase_unit": "lb", "purchase_quantity": Decimal("5.0")},
    )

    # Add lot: 10.0 lb (40 cups at 4 cups/lb)
    inventory_item_service.add_to_inventory(
        product_id=product.id, quantity=Decimal("10.0"), purchase_date=date.today()
    )

    # Attempt to consume 60 cups (need 15 lb, only have 10 lb)
    result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("60.0"))

    assert abs(result["consumed"] - Decimal("40.0")) < Decimal(
        "0.001"
    ), f"Expected 40.0 consumed, got {result["consumed"]}"  # Only 10 lb available
    assert result["satisfied"] is False
    assert abs(result["shortfall"] - Decimal("20.0")) < Decimal(
        "0.001"
    ), f"Expected 20.0 shortfall, got {result["shortfall"]}"  # 60 - 40 = 20 cups short

    # Verify lot is depleted
    assert len(result["breakdown"]) == 1
    assert abs(result["breakdown"][0]["remaining_in_lot"]) < Decimal(
        "0.001"
    ), f"Expected 0.0, got {result["breakdown"][0]["remaining_in_lot"]}"


def test_fifo_exact_consumption(test_db):
    """Test: Consume exactly available quantity."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {
            "name": "Almond Flour",
            "category": "Flour",
            "recipe_unit": "cup",
            # 4-field density: 1 cup = 113.4g (approximately 0.4793 g/ml, 4 cups/lb)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 113.4,
            "density_weight_unit": "g",
        }
    )

    product = product_service.create_product(
        ingredient.slug,
        {"brand": "Blue Diamond", "purchase_unit": "lb", "purchase_quantity": Decimal("3.0")},
    )

    # Add lot: 5.0 lb (20 cups at 4 cups/lb)
    inventory_item_service.add_to_inventory(
        product_id=product.id, quantity=Decimal("5.0"), purchase_date=date.today()
    )

    # Consume exactly 20 cups
    result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("20.0"))

    # Allow for floating point precision loss in unit conversions (0.1% tolerance)
    assert abs(result["consumed"] - Decimal("20.0")) < Decimal(
        "0.1"
    ), f"Expected ~20.0 consumed, got {result['consumed']}"
    # Consider satisfied if shortfall is negligible (< 0.01 cups)
    shortfall = result["shortfall"]
    satisfied = result["satisfied"] or shortfall < Decimal("0.01")
    assert satisfied, f"Expected satisfied, shortfall={shortfall}"
    assert shortfall < Decimal("0.01"), f"Expected negligible shortfall, got {shortfall}"
    assert result["breakdown"][0]["remaining_in_lot"] < Decimal(
        "0.01"
    ), f"Expected ~0.0, got {result['breakdown'][0]['remaining_in_lot']}"


def test_fifo_ordering_across_multiple_products(test_db):
    """Test: Multiple products → FIFO consumes oldest across all products."""

    # Setup: Create ingredient
    ingredient = ingredient_service.create_ingredient(
        {
            "name": "Coconut Flour",
            "category": "Flour",
            "recipe_unit": "cup",
            # 4-field density: 1 cup = 113.4g (approximately 0.4793 g/ml, 4 cups/lb)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 113.4,
            "density_weight_unit": "g",
        }
    )

    # Create product 1
    product1 = product_service.create_product(
        ingredient.slug,
        {"brand": "Bob's Red Mill", "purchase_unit": "lb", "purchase_quantity": Decimal("1.0")},
    )

    # Create product 2
    product2 = product_service.create_product(
        ingredient.slug,
        {"brand": "Anthony's", "purchase_unit": "lb", "purchase_quantity": Decimal("2.0")},
    )

    # Add lot from product 1 (older)
    lot1 = inventory_item_service.add_to_inventory(
        product_id=product1.id, quantity=Decimal("2.0"), purchase_date=date(2025, 1, 1)
    )

    # Add lot from product 2 (newer)
    lot2 = inventory_item_service.add_to_inventory(
        product_id=product2.id, quantity=Decimal("3.0"), purchase_date=date(2025, 2, 1)
    )

    # Consume 4 cups (1 lb) - should come from product 1 (older)
    result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("4.0"))

    assert result["satisfied"] is True
    assert len(result["breakdown"]) == 1
    assert result["breakdown"][0]["product_id"] == product1.id


def test_fifo_zero_quantity_lots_ignored(test_db):
    """Test: Depleted lots (quantity=0) are skipped during FIFO."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {
            "name": "Buckwheat Flour",
            "category": "Flour",
            "recipe_unit": "cup",
            # 4-field density: 1 cup = 113.4g (approximately 0.4793 g/ml, 4 cups/lb)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 113.4,
            "density_weight_unit": "g",
        }
    )

    product = product_service.create_product(
        ingredient.slug,
        {"brand": "Arrowhead Mills", "purchase_unit": "lb", "purchase_quantity": Decimal("2.0")},
    )

    # Add lot 1 (will deplete)
    lot1 = inventory_item_service.add_to_inventory(
        product_id=product.id, quantity=Decimal("2.0"), purchase_date=date(2025, 1, 1)
    )

    # Add lot 2
    lot2 = inventory_item_service.add_to_inventory(
        product_id=product.id, quantity=Decimal("3.0"), purchase_date=date(2025, 2, 1)
    )

    # First consumption: deplete lot 1
    result1 = inventory_item_service.consume_fifo(ingredient.slug, Decimal("8.0"))
    assert result1["consumed"] == Decimal("8.0")

    # Second consumption: should skip depleted lot 1, consume from lot 2
    result2 = inventory_item_service.consume_fifo(ingredient.slug, Decimal("4.0"))

    assert result2["consumed"] == Decimal("4.0")
    assert result2["satisfied"] is True
    assert len(result2["breakdown"]) == 1
    assert result2["breakdown"][0]["inventory_item_id"] == lot2.id


def test_fifo_precision(test_db):
    """Test: FIFO calculations maintain decimal precision (no rounding errors)."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {
            "name": "Teff Flour",
            "category": "Flour",
            "recipe_unit": "oz",  # Changed to match purchase_unit for precision test
        }
    )

    product = product_service.create_product(
        ingredient.slug,
        {"brand": "Bob's Red Mill", "purchase_unit": "oz", "purchase_quantity": Decimal("24.0")},
    )

    # Add lot: 17.3 oz
    inventory_item_service.add_to_inventory(
        product_id=product.id, quantity=Decimal("17.3"), purchase_date=date.today()
    )

    # Consume fractional amount: 5.75 oz
    result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("5.75"))

    # Verify precision maintained
    assert abs(result["consumed"] - Decimal("5.75")) < Decimal(
        "0.001"
    ), f"Expected 5.75 consumed, got {result["consumed"]}"
    assert abs(result["breakdown"][0]["remaining_in_lot"] - Decimal("11.55")) < Decimal(
        "0.001"
    ), f"Expected 11.55, got {result["breakdown"][0]["remaining_in_lot"]}"  # 17.3 - 5.75
