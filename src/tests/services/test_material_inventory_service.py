import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Dict, Any

from src.models import (
    MaterialInventoryItem,
    MaterialProduct,
    Material,
    Supplier,
    MaterialCategory,
    MaterialSubcategory,
    MaterialPurchase,
)
from src.services.material_inventory_service import adjust_inventory
from src.services.exceptions import (
    MaterialInventoryItemNotFoundError,
    ValidationError as ServiceValidationError,
)


@pytest.fixture
def supplier(test_db):
    s = Supplier(name="Test Supplier", city="Test City", state="TS", zip_code="12345")
    test_db.add(s)
    test_db.commit()
    return s

@pytest.fixture
def material_category(test_db):
    mc = MaterialCategory(name="Test Category", slug="test-category")
    test_db.add(mc)
    test_db.commit()
    return mc

@pytest.fixture
def material_subcategory(test_db, material_category):
    msc = MaterialSubcategory(name="Test Subcategory", slug="test-subcategory", category_id=material_category.id)
    test_db.add(msc)
    test_db.commit()
    return msc

@pytest.fixture
def material(test_db, material_subcategory):
    m = Material(
        name="Test Material",
        slug="test-material",
        description="Test Description",
        subcategory_id=material_subcategory.id,
        base_unit_type="each",
    )
    test_db.add(m)
    test_db.commit()
    return m

@pytest.fixture
def material_product(test_db, material, supplier):
    """Create a test material product."""
    mp = MaterialProduct(
        material_id=material.id,
        supplier_id=supplier.id,
        name="Test Product",
        sku="TP-01",
        package_quantity=12,
        package_unit="each",
        quantity_in_base_units=12,
    )
    test_db.add(mp)
    test_db.commit()
    return mp


class TestInventoryAdjustment:
    """Tests for adjust_inventory() function."""

    @pytest.fixture
    def inventory_item(self, test_db, material_product, supplier):
        """Create a test inventory item with 100 units."""
        purchase = MaterialPurchase(
            product_id=material_product.id,
            supplier_id=supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("6.00"),
            units_added=float(Decimal("100")),
            unit_cost=Decimal("0.50"),
        )
        test_db.add(purchase)
        test_db.commit()

        item = MaterialInventoryItem(
            material_product_id=material_product.id,
            material_purchase_id=purchase.id,
            purchase_date=date.today(),
            quantity_purchased=float(Decimal("100")),
            quantity_remaining=float(Decimal("100")),
            cost_per_unit=Decimal("0.50"),
        )
        test_db.add(item)
        test_db.commit()
        return item

    def test_adjust_add(self, test_db, inventory_item):
        """Test adding to inventory."""
        result = adjust_inventory(
            inventory_item.id, "add", Decimal("25"),
            notes="Found extra", session=test_db
        )
        assert Decimal(str(result["quantity_remaining"])) == Decimal("125")

    def test_adjust_subtract(self, test_db, inventory_item):
        """Test subtracting from inventory."""
        result = adjust_inventory(
            inventory_item.id, "subtract", Decimal("30"),
            notes="Used untracked", session=test_db
        )
        assert Decimal(str(result["quantity_remaining"])) == Decimal("70")

    def test_adjust_set(self, test_db, inventory_item):
        """Test setting exact quantity."""
        result = adjust_inventory(
            inventory_item.id, "set", Decimal("50"),
            notes="Physical count", session=test_db
        )
        assert Decimal(str(result["quantity_remaining"])) == Decimal("50")

    def test_adjust_percentage(self, test_db, inventory_item):
        """Test percentage adjustment (50% remaining)."""
        result = adjust_inventory(
            inventory_item.id, "percentage", Decimal("50"),
            notes="Half used", session=test_db
        )
        assert Decimal(str(result["quantity_remaining"])) == Decimal("50.00")

    def test_adjust_percentage_zero(self, test_db, inventory_item):
        """Test 0% (fully depleted)."""
        result = adjust_inventory(
            inventory_item.id, "percentage", Decimal("0"),
            session=test_db
        )
        assert Decimal(str(result["quantity_remaining"])) == Decimal("0")

    def test_adjust_negative_result_raises(self, test_db, inventory_item):
        """Test that negative result raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc:
            adjust_inventory(
                inventory_item.id, "subtract", Decimal("200"),
                session=test_db
            )
        assert "negative quantity" in str(exc.value).lower()

    def test_adjust_invalid_percentage_raises(self, test_db, inventory_item):
        """Test that percentage > 100 raises ValidationError."""
        with pytest.raises(ServiceValidationError):
            adjust_inventory(
                inventory_item.id, "percentage", Decimal("150"),
                session=test_db
            )

    def test_adjust_notes_stored(self, test_db, inventory_item):
        """Test that adjustment notes are stored."""
        adjust_inventory(
            inventory_item.id, "set", Decimal("75"),
            notes="Inventory recount", session=test_db
        )
        test_db.refresh(inventory_item)
        assert "Inventory recount" in inventory_item.notes

    def test_adjust_item_not_found(self, test_db):
        """Test adjusting non-existent item raises error."""
        with pytest.raises(MaterialInventoryItemNotFoundError):
            adjust_inventory(99999, "set", Decimal("50"), session=test_db)
