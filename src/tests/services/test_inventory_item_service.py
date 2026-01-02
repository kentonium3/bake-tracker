"""Tests for InventoryItemService, focusing on dry_run functionality and FIFO costing.

Tests cover:
- dry_run=True does not modify inventory
- dry_run=True returns correct cost calculations
- dry_run=False (default) behaves as before (backward compatibility)
- unit_cost field in breakdown items
- FIFO order is respected in both modes
- F028: add_to_inventory creates linked Purchase records
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services import ingredient_service, product_service, inventory_item_service, purchase_service, supplier_service


@pytest.fixture
def test_supplier(test_db):
    """Create a test supplier for inventory tests."""
    result = supplier_service.create_supplier(
        name="Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
    )
    # create_supplier returns a dict, but we need to return a simple object with .id
    class SupplierObj:
        def __init__(self, supplier_dict):
            self.id = supplier_dict["id"]
            self.name = supplier_dict["name"]
    return SupplierObj(result)

class TestConsumeFifoDryRun:
    """Tests for consume_fifo() dry_run parameter."""

    def test_consume_fifo_dry_run_does_not_modify_inventory(self, test_db, test_supplier):
        """Test: dry_run=True does not change inventory quantities."""
        # Setup: Create ingredient, product, and inventory item
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Test Flour DR",
                "category": "Flour",  # Same as package_unit for simplicity
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        # Add inventory item with known quantity (F028: includes supplier and unit_price)
        initial_quantity = Decimal("10.0")
        inventory_item = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=initial_quantity,
            supplier_id=test_supplier.id,
            unit_price=Decimal("2.00"),
            purchase_date=date(2025, 1, 1),
        )

        # Act: Call consume_fifo with dry_run=True
        result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("3.0"), "lb", dry_run=True)

        # Assert: Quantity unchanged
        items = inventory_item_service.get_inventory_items(ingredient_slug=ingredient.slug)
        assert len(items) == 1
        assert abs(Decimal(str(items[0].quantity)) - initial_quantity) < Decimal(
            "0.001"
        ), f"Expected quantity {initial_quantity}, got {items[0].quantity}"

        # Also verify the result shows consumption was calculated
        assert result["satisfied"] is True
        assert abs(result["consumed"] - Decimal("3.0")) < Decimal("0.001")

    def test_consume_fifo_dry_run_returns_correct_cost(self, test_db, test_supplier):
        """Test: dry_run=True returns correct total_cost based on FIFO."""
        # Setup: Create ingredient and product
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Test Flour Cost",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        # Add two inventory items with different unit costs (F028: unit_cost set from unit_price)
        # Lot 1: 5 lb at $2.00/lb (older - should be consumed first)
        lot1 = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("5.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("2.00"),
            purchase_date=date(2025, 1, 1),
        )

        # Lot 2: 5 lb at $3.00/lb (newer)
        lot2 = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("5.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("3.00"),
            purchase_date=date(2025, 2, 1),
        )

        # Act: Consume 7 lb (5 from lot1 @ $2, 2 from lot2 @ $3)
        # Expected cost: (5 * $2.00) + (2 * $3.00) = $10.00 + $6.00 = $16.00
        result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("7.0"), "lb", dry_run=True)

        # Assert: Cost is correct
        expected_cost = Decimal("16.00")
        assert abs(result["total_cost"] - expected_cost) < Decimal(
            "0.01"
        ), f"Expected total_cost {expected_cost}, got {result['total_cost']}"

    def test_consume_fifo_dry_run_includes_unit_cost_in_breakdown(self, test_db, test_supplier):
        """Test: Each breakdown item includes unit_cost field."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Test Flour Breakdown",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        # Add inventory item with unit_cost (F028: set via unit_price)
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("10.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("2.50"),
            purchase_date=date(2025, 1, 1),
        )

        # Act
        result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("3.0"), "lb", dry_run=True)

        # Assert: Breakdown items have unit_cost
        assert len(result["breakdown"]) >= 1
        for item in result["breakdown"]:
            assert "unit_cost" in item, "Breakdown item missing unit_cost field"
            assert item["unit_cost"] == Decimal(
                "2.50"
            ), f"Expected unit_cost 2.50, got {item['unit_cost']}"

    def test_consume_fifo_default_still_modifies_inventory(self, test_db, test_supplier):
        """Test: dry_run=False (default) updates inventory quantities (backward compatibility)."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Test Flour Default",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        initial_quantity = Decimal("10.0")
        inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=initial_quantity,
            supplier_id=test_supplier.id,
            unit_price=Decimal("2.00"),
            purchase_date=date(2025, 1, 1),
        )

        # Act: Call consume_fifo WITHOUT dry_run (default=False)
        consume_amount = Decimal("3.0")
        result = inventory_item_service.consume_fifo(
            ingredient.slug,
            consume_amount,
            "lb",  # target_unit
            # dry_run defaults to False
        )

        # Assert: Quantity WAS changed
        items = inventory_item_service.get_inventory_items(ingredient_slug=ingredient.slug)
        assert len(items) == 1
        expected_remaining = initial_quantity - consume_amount
        assert abs(Decimal(str(items[0].quantity)) - expected_remaining) < Decimal(
            "0.001"
        ), f"Expected quantity {expected_remaining}, got {items[0].quantity}"

    def test_consume_fifo_dry_run_respects_fifo_order(self, test_db, test_supplier):
        """Test: dry_run mode respects FIFO ordering (oldest lots consumed first)."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Test Flour FIFO Order",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        # Add lots in non-chronological order but with explicit dates
        # Lot 2 added first but has later date
        lot2 = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("5.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("3.00"),
            purchase_date=date(2025, 2, 1),  # Newer
        )

        # Lot 1 added second but has earlier date (should be consumed first)
        lot1 = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("5.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("2.00"),
            purchase_date=date(2025, 1, 1),  # Older
        )

        # Act: Consume 3 lb (should come from lot1, the older one)
        result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("3.0"), "lb", dry_run=True)

        # Assert: Consumption came from older lot (lot1)
        assert len(result["breakdown"]) == 1
        assert result["breakdown"][0]["lot_date"] == date(
            2025, 1, 1
        ), f"Expected consumption from oldest lot (2025-01-01), got {result['breakdown'][0]['lot_date']}"
        assert result["breakdown"][0]["unit_cost"] == Decimal(
            "2.00"
        ), "Should have used the $2.00/lb lot (oldest)"

    def test_consume_fifo_dry_run_total_cost_zero_when_no_unit_cost(self, test_db, test_supplier):
        """Test: total_cost handles items with zero unit_cost correctly."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Test Flour No Cost",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        # Add inventory item with $0.00 unit_price (e.g., donation)
        inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("10.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("0.00"),  # Free item
            purchase_date=date(2025, 1, 1),
        )

        # Act
        result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("3.0"), "lb", dry_run=True)

        # Assert: total_cost should be 0 (no unit_cost set)
        assert result["total_cost"] == Decimal(
            "0.0"
        ), f"Expected total_cost 0.0 when unit_cost not set, got {result['total_cost']}"

    def test_consume_fifo_dry_run_partial_lot_cost_calculation(self, test_db, test_supplier):
        """Test: Partial consumption from a lot calculates cost correctly."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Test Flour Partial",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        # Add inventory item: 10 lb at $2.50/lb
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("10.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("2.50"),
            purchase_date=date(2025, 1, 1),
        )

        # Act: Consume 4 lb (partial - should cost 4 * $2.50 = $10.00)
        result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("4.0"), "lb", dry_run=True)

        # Assert
        expected_cost = Decimal("10.00")
        assert abs(result["total_cost"] - expected_cost) < Decimal(
            "0.01"
        ), f"Expected total_cost {expected_cost}, got {result['total_cost']}"

        # Also verify remaining_in_lot is calculated correctly for dry_run
        assert abs(result["breakdown"][0]["remaining_in_lot"] - Decimal("6.0")) < Decimal(
            "0.001"
        ), f"Expected remaining_in_lot 6.0, got {result['breakdown'][0]['remaining_in_lot']}"

    def test_consume_fifo_dry_run_with_shortfall(self, test_db, test_supplier):
        """Test: dry_run handles shortfall scenario correctly."""
        # Setup
        ingredient = ingredient_service.create_ingredient(
            {
                "display_name": "Test Flour Shortfall",
                "category": "Flour"
            }
        )

        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        # Add only 5 lb at $2.00/lb
        lot = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("5.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("2.00"),
            purchase_date=date(2025, 1, 1),
        )

        # Act: Try to consume 8 lb (more than available)
        result = inventory_item_service.consume_fifo(ingredient.slug, Decimal("8.0"), "lb", dry_run=True)

        # Assert
        assert result["satisfied"] is False
        assert abs(result["consumed"] - Decimal("5.0")) < Decimal(
            "0.001"
        ), "Should have consumed all available (5 lb)"
        assert abs(result["shortfall"] - Decimal("3.0")) < Decimal(
            "0.001"
        ), "Shortfall should be 3 lb"
        # Cost should be for consumed portion only (5 * $2.00 = $10.00)
        assert abs(result["total_cost"] - Decimal("10.00")) < Decimal(
            "0.01"
        ), f"Expected total_cost $10.00 for consumed portion, got {result['total_cost']}"

        # Verify inventory unchanged after dry_run
        items = inventory_item_service.get_inventory_items(ingredient_slug=ingredient.slug)
        assert abs(Decimal(str(items[0].quantity)) - Decimal("5.0")) < Decimal(
            "0.001"
        ), "Inventory quantity should be unchanged after dry_run"


class TestAddToInventoryWithPurchase:
    """Tests for F028 inventory-purchase integration (WP02).

    These tests verify that add_to_inventory():
    - Creates linked Purchase records
    - Sets InventoryItem.purchase_id correctly
    - Sets InventoryItem.unit_cost from unit_price
    - Stores notes on InventoryItem (not Purchase)
    - Validates supplier_id and product_id
    - Defaults purchase_date to today
    """

    def test_add_to_inventory_creates_purchase(self, test_db, test_supplier):
        """Adding inventory creates a linked Purchase record (FR-001)."""
        from src.models import Purchase

        ingredient = ingredient_service.create_ingredient({
            "display_name": "Test Flour Purchase",
            "category": "Flour",
        })
        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        item = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("10.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("8.99"),
            purchase_date=date(2025, 1, 15),
        )

        # Verify InventoryItem created
        assert item is not None
        assert item.id is not None

        # Verify Purchase created and linked
        assert item.purchase_id is not None
        purchase = purchase_service.get_purchase(item.purchase_id)
        assert purchase is not None
        # get_purchase returns an ORM object
        assert purchase.product_id == product.id
        assert purchase.supplier_id == test_supplier.id
        assert Decimal(str(purchase.unit_price)) == Decimal("8.99")

    def test_add_to_inventory_sets_unit_cost(self, test_db, test_supplier):
        """InventoryItem.unit_cost is set from unit_price for FIFO costing."""
        ingredient = ingredient_service.create_ingredient({
            "display_name": "Test Flour Unit Cost",
            "category": "Flour",
        })
        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        item = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("5.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("12.50"),
        )

        assert item.unit_cost == 12.50

    def test_add_to_inventory_defaults_purchase_date_to_today(self, test_db, test_supplier):
        """Purchase date defaults to today when not provided (FR-013)."""
        from src.models import Purchase

        ingredient = ingredient_service.create_ingredient({
            "display_name": "Test Flour Today",
            "category": "Flour",
        })
        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        item = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("1.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("5.00"),
            # purchase_date not provided - should default to today
        )

        purchase = purchase_service.get_purchase(item.purchase_id)
        assert purchase.purchase_date == date.today()

    def test_add_to_inventory_invalid_supplier_raises(self, test_db):
        """Invalid supplier_id raises validation error."""
        from src.services.exceptions import ValidationError

        ingredient = ingredient_service.create_ingredient({
            "display_name": "Test Flour Invalid Supplier",
            "category": "Flour",
        })
        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        with pytest.raises(ValidationError, match="Supplier"):
            inventory_item_service.add_to_inventory(
                product_id=product.id,
                quantity=Decimal("1.0"),
                supplier_id=99999,  # Non-existent
                unit_price=Decimal("5.00"),
            )

    def test_add_to_inventory_invalid_product_raises(self, test_db, test_supplier):
        """Invalid product_id raises ProductNotFound error."""
        from src.services.exceptions import ProductNotFound

        with pytest.raises(ProductNotFound):
            inventory_item_service.add_to_inventory(
                product_id=99999,  # Non-existent
                quantity=Decimal("1.0"),
                supplier_id=test_supplier.id,
                unit_price=Decimal("5.00"),
            )

    def test_add_to_inventory_stores_notes_on_item(self, test_db, test_supplier):
        """Notes are stored on InventoryItem, not Purchase (FR-014)."""
        ingredient = ingredient_service.create_ingredient({
            "display_name": "Test Flour Notes",
            "category": "Flour",
        })
        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        item = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("1.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("5.00"),
            notes="Test note - on sale",
        )

        assert item.notes == "Test note - on sale"

        # Purchase should NOT have notes per FR-014
        purchase = purchase_service.get_purchase(item.purchase_id)
        assert purchase.notes is None

    def test_add_to_inventory_negative_price_raises(self, test_db, test_supplier):
        """Negative unit_price raises validation error (FR-008)."""
        from src.services.exceptions import ValidationError

        ingredient = ingredient_service.create_ingredient({
            "display_name": "Test Flour Negative",
            "category": "Flour",
        })
        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        with pytest.raises(ValidationError, match="negative"):
            inventory_item_service.add_to_inventory(
                product_id=product.id,
                quantity=Decimal("1.0"),
                supplier_id=test_supplier.id,
                unit_price=Decimal("-5.00"),  # Invalid
            )

    def test_add_to_inventory_zero_price_allowed(self, test_db, test_supplier):
        """Zero unit_price is allowed (e.g., donations) - FR-007."""
        ingredient = ingredient_service.create_ingredient({
            "display_name": "Test Flour Zero Price",
            "category": "Flour",
        })
        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        item = inventory_item_service.add_to_inventory(
            product_id=product.id,
            quantity=Decimal("1.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("0.00"),  # Donation/free
        )

        assert item is not None
        assert item.unit_cost == 0.0

    def test_add_to_inventory_with_session_composability(self, test_db, test_supplier):
        """Function accepts session parameter for transaction composability."""
        from src.services.database import session_scope

        ingredient = ingredient_service.create_ingredient({
            "display_name": "Test Flour Session",
            "category": "Flour",
        })
        product = product_service.create_product(
            ingredient.slug,
            {"brand": "Test Brand", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
        )

        with session_scope() as session:
            item = inventory_item_service.add_to_inventory(
                product_id=product.id,
                quantity=Decimal("1.0"),
                supplier_id=test_supplier.id,
                unit_price=Decimal("5.00"),
                session=session,  # Pass session for composability
            )

            # Verify item created within same transaction
            assert item.id is not None
            assert item.purchase_id is not None


# =============================================================================
# Recency Intelligence Tests (Feature 029)
# =============================================================================


@pytest.fixture
def recency_test_data(test_db, test_supplier):
    """Create inventory items with specific dates for recency testing.

    Creates:
    - Product A: Added yesterday (temporal recent)
    - Product B: Added 45 days ago, only once (not recent)
    - Product C: Added 60 days ago but 4 times (frequency recent)
    """
    # Create ingredient in Flour category
    ingredient = ingredient_service.create_ingredient({
        "display_name": "Test Flour Recency",
        "category": "Flour",
    })

    today = date.today()

    # Product A: Added yesterday (temporal recent)
    product_a = product_service.create_product(
        ingredient.slug,
        {"brand": "Brand A", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
    )
    inventory_item_service.add_to_inventory(
        product_id=product_a.id,
        quantity=Decimal("1.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("5.00"),
        purchase_date=today - timedelta(days=1),
    )

    # Product B: Added 45 days ago, only once (not recent - outside 30 days, only 1 time)
    product_b = product_service.create_product(
        ingredient.slug,
        {"brand": "Brand B", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
    )
    inventory_item_service.add_to_inventory(
        product_id=product_b.id,
        quantity=Decimal("1.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("5.00"),
        purchase_date=today - timedelta(days=45),
    )

    # Product C: Added 60 days ago but 4 times (frequency recent - 4 >= 3 within 90 days)
    product_c = product_service.create_product(
        ingredient.slug,
        {"brand": "Brand C", "package_unit": "lb", "package_unit_quantity": Decimal("5.0")}
    )
    for i in range(4):
        inventory_item_service.add_to_inventory(
            product_id=product_c.id,
            quantity=Decimal("1.0"),
            supplier_id=test_supplier.id,
            unit_price=Decimal("5.00"),
            purchase_date=today - timedelta(days=60 + i),
        )

    return {
        "ingredient": ingredient,
        "product_a": product_a,
        "product_b": product_b,
        "product_c": product_c,
        "category": "Flour",
    }


class TestGetRecentProducts:
    """Tests for get_recent_products() recency query."""

    def test_get_recent_products_temporal(self, recency_test_data):
        """Product A should be recent (temporal - added yesterday)."""
        from src.services.inventory_item_service import get_recent_products

        ingredient = recency_test_data["ingredient"]
        product_a = recency_test_data["product_a"]

        recent_ids = get_recent_products(ingredient.id)

        assert product_a.id in recent_ids, "Product A should be recent (temporal)"

    def test_get_recent_products_not_recent(self, recency_test_data):
        """Product B should NOT be recent (45 days ago, only once)."""
        from src.services.inventory_item_service import get_recent_products

        ingredient = recency_test_data["ingredient"]
        product_b = recency_test_data["product_b"]

        recent_ids = get_recent_products(ingredient.id)

        assert product_b.id not in recent_ids, "Product B should NOT be recent"

    def test_get_recent_products_frequency(self, recency_test_data):
        """Product C should be recent (frequency - added 4 times in 90 days)."""
        from src.services.inventory_item_service import get_recent_products

        ingredient = recency_test_data["ingredient"]
        product_c = recency_test_data["product_c"]

        recent_ids = get_recent_products(ingredient.id)

        assert product_c.id in recent_ids, "Product C should be recent (frequency)"

    def test_get_recent_products_sorted_by_date(self, recency_test_data):
        """Results should be sorted by most recent first."""
        from src.services.inventory_item_service import get_recent_products

        ingredient = recency_test_data["ingredient"]
        product_a = recency_test_data["product_a"]
        product_c = recency_test_data["product_c"]

        recent_ids = get_recent_products(ingredient.id)

        # Both A and C should be recent
        if product_a.id in recent_ids and product_c.id in recent_ids:
            a_idx = recent_ids.index(product_a.id)
            c_idx = recent_ids.index(product_c.id)
            # Product A (yesterday) should come before Product C (60 days ago)
            assert a_idx < c_idx, "Product A should come before Product C"

    def test_get_recent_products_respects_limit(self, recency_test_data):
        """Results should respect the limit parameter."""
        from src.services.inventory_item_service import get_recent_products

        ingredient = recency_test_data["ingredient"]

        recent_ids = get_recent_products(ingredient.id, limit=1)

        assert len(recent_ids) <= 1, "Should respect limit parameter"

    def test_get_recent_products_with_session(self, recency_test_data):
        """Function should work with provided session."""
        from src.services.inventory_item_service import get_recent_products
        from src.services.database import session_scope

        ingredient = recency_test_data["ingredient"]

        with session_scope() as session:
            recent_ids = get_recent_products(ingredient.id, session=session)

        # Should return results without error
        assert isinstance(recent_ids, list)

    def test_get_recent_products_empty_for_nonexistent_ingredient(self, test_db):
        """Should return empty list for ingredient with no inventory."""
        from src.services.inventory_item_service import get_recent_products

        # Use a non-existent ingredient ID
        recent_ids = get_recent_products(ingredient_id=99999)

        assert recent_ids == [], "Should return empty list for nonexistent ingredient"


class TestGetRecentIngredients:
    """Tests for get_recent_ingredients() recency query."""

    def test_get_recent_ingredients_temporal(self, recency_test_data):
        """Ingredient should be recent when product was added recently."""
        from src.services.inventory_item_service import get_recent_ingredients

        ingredient = recency_test_data["ingredient"]
        category = recency_test_data["category"]

        recent_ids = get_recent_ingredients(category)

        assert ingredient.id in recent_ids, "Ingredient should be recent"

    def test_get_recent_ingredients_empty_for_nonexistent_category(self, test_db):
        """Should return empty list for category with no inventory."""
        from src.services.inventory_item_service import get_recent_ingredients

        recent_ids = get_recent_ingredients(category="NonexistentCategory")

        assert recent_ids == [], "Should return empty list for nonexistent category"

    def test_get_recent_ingredients_with_session(self, recency_test_data):
        """Function should work with provided session."""
        from src.services.inventory_item_service import get_recent_ingredients
        from src.services.database import session_scope

        category = recency_test_data["category"]

        with session_scope() as session:
            recent_ids = get_recent_ingredients(category, session=session)

        # Should return results without error
        assert isinstance(recent_ids, list)
