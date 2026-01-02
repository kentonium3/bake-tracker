"""Integration tests for ingredient -> product -> inventory workflow.

Tests the complete inventory management flow across multiple services.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services import ingredient_service, product_service, inventory_item_service, supplier_service
from src.services.exceptions import IngredientNotFoundBySlug, ProductNotFound, ValidationError


@pytest.fixture
def test_supplier(test_db):
    """Create a test supplier for F028 inventory tracking."""
    result = supplier_service.create_supplier(
        name="Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
    )
    class SupplierObj:
        def __init__(self, data):
            self.id = data["id"]
    return SupplierObj(result)


def test_complete_inventory_workflow(test_db, test_supplier):
    """Test: Create ingredient -> Create product -> Add to inventory -> Query inventory."""

    # 1. Create ingredient
    ingredient_data = {
        "display_name": "All-Purpose Flour",
        "category": "Flour",
        # 4-field density: 1 cup = 113.4g (approximately 0.4793 g/ml, 4 cups/lb)
        "density_volume_value": 1.0,
        "density_volume_unit": "cup",
        "density_weight_value": 113.4,
        "density_weight_unit": "g"
    }
    ingredient = ingredient_service.create_ingredient(ingredient_data)
    assert ingredient.slug == "all_purpose_flour"
    assert ingredient.display_name == "All-Purpose Flour"
    # 2. Create product
    product_data = {
        "brand": "King Arthur",
        "package_size": "25 lb bag",
        "package_unit": "lb",
        "package_unit_quantity": Decimal("25.0"),
        "preferred": True
    }
    product = product_service.create_product(ingredient.slug, product_data)
    assert product.preferred is True
    assert product.brand == "King Arthur"
    assert product.ingredient_id == ingredient.id

    # 3. Add to inventory
    inventory_item = inventory_item_service.add_to_inventory(
        product_id=product.id,
        quantity=Decimal("25.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("24.99"),
        purchase_date=date.today(),
        expiration_date=date.today() + timedelta(days=365),
        location="Main Storage"
    )
    assert inventory_item.quantity == 25.0
    assert inventory_item.product_id == product.id
    assert inventory_item.location == "Main Storage"

    # 4. Query total inventory by unit
    totals = inventory_item_service.get_total_quantity(ingredient.slug)
    # Returns dict grouped by unit - should have 25 lb
    assert "lb" in totals, f"Expected 'lb' in totals, got {totals}"
    assert abs(totals["lb"] - Decimal("25.0")) < Decimal("0.01"), f"Expected 25.0 lb, got {totals['lb']}"

    # 5. Get preferred product
    preferred = product_service.get_preferred_product(ingredient.slug)
    assert preferred.id == product.id
    assert preferred.preferred is True

def test_multiple_products_preferred_toggle(test_db):
    """Test: Create multiple products -> Toggle preferred -> Verify atomicity."""

    # Create ingredient
    ingredient_data = {"display_name": "Granulated Sugar", "category": "Sugar"}
    ingredient = ingredient_service.create_ingredient(ingredient_data)

    # Create product 1 (preferred)
    product1_data = {
        "brand": "C&H",
        "package_size": "4 lb bag",
        "package_unit": "lb",
        "package_unit_quantity": Decimal("4.0"),
        "preferred": True
    }
    product1 = product_service.create_product(ingredient.slug, product1_data)
    assert product1.preferred is True

    # Create product 2 (not preferred initially)
    product2_data = {
        "brand": "Domino",
        "package_size": "5 lb bag",
        "package_unit": "lb",
        "package_unit_quantity": Decimal("5.0"),
        "preferred": False
    }
    product2 = product_service.create_product(ingredient.slug, product2_data)
    assert product2.preferred is False

    # Toggle preferred to product 2
    product_service.set_preferred_product(product2.id)

    # Verify atomicity: only product2 should be preferred
    products = product_service.get_products_for_ingredient(ingredient.slug)
    preferred_count = sum(1 for p in products if p.preferred)
    assert preferred_count == 1
    assert products[0].id == product2.id  # Preferred first
    assert products[0].preferred is True

def test_inventory_items_filtering(test_db, test_supplier):
    """Test: Add multiple inventory items -> Filter by location and ingredient."""

    # Setup: Create ingredient and product
    ingredient = ingredient_service.create_ingredient(
        {
            "display_name": "Bread Flour",
            "category": "Flour",
            # 4-field density: 1 cup = 113.4g (approximately 0.4793 g/ml, 4 cups/lb)
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 113.4,
            "density_weight_unit": "g"
        }
    )

    product = product_service.create_product(
        ingredient.slug,
        {
            "brand": "Bob's Red Mill",
            "package_size": "5 lb bag",
            "package_unit": "lb",
            "package_unit_quantity": Decimal("5.0")
        }
    )

    # Add inventory items to different locations
    item1 = inventory_item_service.add_to_inventory(
        product_id=product.id,
        quantity=Decimal("5.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("8.99"),
        purchase_date=date.today() - timedelta(days=30),
        location="Main Storage"
    )

    item2 = inventory_item_service.add_to_inventory(
        product_id=product.id,
        quantity=Decimal("10.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("9.49"),
        purchase_date=date.today() - timedelta(days=15),
        location="Basement"
    )

    item3 = inventory_item_service.add_to_inventory(
        product_id=product.id,
        quantity=Decimal("3.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("8.99"),
        purchase_date=date.today(),
        location="Main Storage"
    )

    # Filter by location
    main_storage_items = inventory_item_service.get_inventory_items(
        ingredient_slug=ingredient.slug, location="Main Storage"
    )
    assert len(main_storage_items) == 2

    basement_items = inventory_item_service.get_inventory_items(
        ingredient_slug=ingredient.slug, location="Basement"
    )
    assert len(basement_items) == 1

    # Verify total quantity by unit
    totals = inventory_item_service.get_total_quantity(ingredient.slug)
    # Returns dict grouped by unit - should have 18 lb total (5 + 10 + 3)
    assert "lb" in totals, f"Expected 'lb' in totals, got {totals}"
    assert abs(totals["lb"] - Decimal("18.0")) < Decimal("0.01"), f"Expected 18.0 lb, got {totals['lb']}"

def test_expiring_items_detection(test_db, test_supplier):
    """Test: Add items with various expiration dates -> Get expiring soon."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {"display_name": "Yeast", "category": "Misc"}
    )

    product = product_service.create_product(
        ingredient.slug,
        {
            "brand": "Red Star",
            "package_size": "4 oz jar",
            "package_unit": "oz",
            "package_unit_quantity": Decimal("4.0")
        }
    )

    # Add item expiring in 7 days
    expiring_soon = inventory_item_service.add_to_inventory(
        product_id=product.id,
        quantity=Decimal("2.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("5.99"),
        purchase_date=date.today() - timedelta(days=60),
        expiration_date=date.today() + timedelta(days=7)
    )

    # Add item expiring in 30 days
    expiring_later = inventory_item_service.add_to_inventory(
        product_id=product.id,
        quantity=Decimal("4.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("5.99"),
        purchase_date=date.today() - timedelta(days=30),
        expiration_date=date.today() + timedelta(days=30)
    )

    # Add item with no expiration
    no_expiration = inventory_item_service.add_to_inventory(
        product_id=product.id,
        quantity=Decimal("1.0"),
        supplier_id=test_supplier.id,
        unit_price=Decimal("5.99"),
        purchase_date=date.today()
    )

    # Get items expiring within 14 days
    expiring = inventory_item_service.get_expiring_soon(days=14)
    assert len(expiring) == 1
    assert expiring[0].id == expiring_soon.id

    # Get items expiring within 60 days
    expiring_60 = inventory_item_service.get_expiring_soon(days=60)
    assert len(expiring_60) == 2

def test_ingredient_deletion_blocked_by_products(test_db):
    """Test: Create product -> Attempt to delete ingredient -> Verify blocked."""

    # Create ingredient and product
    ingredient = ingredient_service.create_ingredient(
        {"display_name": "Baking Powder", "category": "Misc"}
    )

    product = product_service.create_product(
        ingredient.slug,
        {"brand": "Rumford", "package_unit": "oz", "package_unit_quantity": Decimal("8.0")}
    )

    # Attempt to delete ingredient should fail
    with pytest.raises(Exception):  # IngredientInUse exception
        ingredient_service.delete_ingredient(ingredient.slug)

    # Verify ingredient still exists
    retrieved = ingredient_service.get_ingredient(ingredient.slug)
    assert retrieved.slug == ingredient.slug
