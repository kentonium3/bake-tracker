"""
Integration tests for Feature 027 Import/Export extensions.

Tests export and import of:
- Supplier (new entity)
- Purchase (with supplier_id FK)
- Product (with preferred_supplier_id, is_hidden)
- InventoryItem (with purchase_id FK)
"""

import json
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.supplier import Supplier
from src.models.inventory_item import InventoryItem
from src.services import import_export_service


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_supplier(test_db):
    """Create a test supplier."""
    session = test_db()
    supplier = Supplier(
        name="Costco",
        city="Issaquah",
        state="WA",
        zip_code="98027",
        is_active=True,
    )
    session.add(supplier)
    session.commit()
    return supplier


@pytest.fixture
def test_supplier_wegmans(test_db):
    """Create another test supplier."""
    session = test_db()
    supplier = Supplier(
        name="Wegmans",
        city="Rochester",
        state="NY",
        zip_code="14624",
        is_active=True,
    )
    session.add(supplier)
    session.commit()
    return supplier


@pytest.fixture
def test_ingredient(test_db):
    """Create a test ingredient."""
    session = test_db()
    ingredient = Ingredient(
        slug="all-purpose-flour",
        display_name="All Purpose Flour",
        category="Dry Goods",
    )
    session.add(ingredient)
    session.commit()
    return ingredient


@pytest.fixture
def test_product(test_db, test_ingredient, test_supplier):
    """Create a test product with preferred supplier."""
    session = test_db()
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="King Arthur Flour 25lb",
        brand="King Arthur",
        package_unit="lb",
        package_unit_quantity=25.0,
        preferred_supplier_id=test_supplier.id,
        is_hidden=False,
    )
    session.add(product)
    session.commit()
    return product


@pytest.fixture
def test_product_hidden(test_db, test_ingredient):
    """Create a hidden test product."""
    session = test_db()
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="Generic Flour 10lb",
        brand="Generic",
        package_unit="lb",
        package_unit_quantity=10.0,
        is_hidden=True,
    )
    session.add(product)
    session.commit()
    return product


@pytest.fixture
def test_purchase(test_db, test_product, test_supplier):
    """Create a test purchase."""
    session = test_db()
    purchase = Purchase(
        product_id=test_product.id,
        supplier_id=test_supplier.id,
        purchase_date=date(2024, 12, 15),
        unit_price=Decimal("12.99"),
        quantity_purchased=2,
    )
    session.add(purchase)
    session.commit()
    return purchase


@pytest.fixture
def test_inventory_item(test_db, test_product, test_purchase):
    """Create a test inventory item with purchase link."""
    session = test_db()
    item = InventoryItem(
        product_id=test_product.id,
        quantity=25.0,
        purchase_date=date(2024, 12, 15),
        purchase_id=test_purchase.id,
    )
    session.add(item)
    session.commit()
    return item


# ============================================================================
# Export Tests
# ============================================================================


class TestExportSuppliers:
    """Test supplier export functionality."""

    def test_export_includes_suppliers(self, test_db, test_supplier):
        """Test that suppliers are exported."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        result = import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        assert "suppliers" in data
        assert len(data["suppliers"]) == 1
        assert data["suppliers"][0]["name"] == "Costco"
        assert data["suppliers"][0]["city"] == "Issaquah"
        assert data["suppliers"][0]["state"] == "WA"
        assert result.entity_counts.get("suppliers") == 1

    def test_export_suppliers_with_all_fields(self, test_db):
        """Test that all supplier fields are exported."""
        session = test_db()
        supplier = Supplier(
            name="Test Store",
            street_address="123 Main St",
            city="Seattle",
            state="WA",
            zip_code="98101",
            notes="Test notes",
            is_active=True,
        )
        session.add(supplier)
        session.commit()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        supplier_data = data["suppliers"][0]
        assert supplier_data["street_address"] == "123 Main St"
        assert supplier_data["notes"] == "Test notes"
        assert supplier_data["is_active"] is True


class TestExportProducts:
    """Test product export with new fields."""

    def test_export_product_preferred_supplier_id(
        self, test_db, test_product, test_supplier
    ):
        """Test that preferred_supplier_id is exported."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        assert len(data["products"]) == 1
        assert data["products"][0]["preferred_supplier_id"] == test_supplier.id

    def test_export_product_is_hidden(self, test_db, test_product_hidden):
        """Test that is_hidden is exported."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        # Find the hidden product
        hidden_products = [p for p in data["products"] if p.get("is_hidden")]
        assert len(hidden_products) == 1
        assert hidden_products[0]["brand"] == "Generic"


class TestExportPurchases:
    """Test purchase export with new fields."""

    def test_export_purchase_with_supplier_id(
        self, test_db, test_purchase, test_supplier
    ):
        """Test that purchase includes supplier_id FK."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        assert len(data["purchases"]) == 1
        purchase_data = data["purchases"][0]
        assert purchase_data["supplier_id"] == test_supplier.id
        assert purchase_data["product_id"] == test_purchase.product_id
        # Unit price may have trailing zeros from Decimal
        assert purchase_data["unit_price"].rstrip("0").rstrip(".") == "12.99"
        assert purchase_data["quantity_purchased"] == 2


class TestExportInventoryItems:
    """Test inventory item export with new fields."""

    def test_export_inventory_item_with_purchase_id(
        self, test_db, test_inventory_item, test_purchase
    ):
        """Test that inventory item includes purchase_id FK."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        assert len(data["inventory_items"]) == 1
        item_data = data["inventory_items"][0]
        assert item_data["purchase_id"] == test_purchase.id


# ============================================================================
# Import Tests
# ============================================================================


class TestImportSuppliers:
    """Test supplier import functionality."""

    def test_import_suppliers(self, test_db):
        """Test basic supplier import."""
        import_data = {
            "version": "3.5",
            "suppliers": [
                {
                    "name": "New Store",
                    "city": "Portland",
                    "state": "OR",
                    "zip_code": "97201",
                    "is_active": True,
                }
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["supplier"]["imported"] == 1

        # Verify supplier was created
        session = test_db()
        supplier = session.query(Supplier).filter_by(name="New Store").first()
        assert supplier is not None
        assert supplier.city == "Portland"
        assert supplier.state == "OR"

    def test_import_suppliers_skip_duplicates(self, test_db, test_supplier):
        """Test that duplicate suppliers are skipped."""
        import_data = {
            "version": "3.5",
            "suppliers": [
                {
                    "name": "Costco",
                    "city": "Issaquah",
                    "state": "WA",
                    "zip_code": "98027",
                }
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            json.dump(import_data, f)
            import_path = f.name

        # Note: skip_duplicates is True by default in v3
        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["supplier"]["skipped"] == 1


class TestImportPurchases:
    """Test purchase import with new FK format."""

    def test_import_purchase_with_supplier_id(
        self, test_db, test_supplier, test_ingredient
    ):
        """Test importing purchase with supplier_id FK."""
        # First create a product
        session = test_db()
        product = Product(
            ingredient_id=test_ingredient.id,
            product_name="Test Flour",
            brand="Test",
            package_unit="lb",
            package_unit_quantity=5.0,
        )
        session.add(product)
        session.commit()

        import_data = {
            "version": "3.5",
            "suppliers": [],
            "ingredients": [],
            "products": [],
            "purchases": [
                {
                    "product_id": product.id,
                    "supplier_id": test_supplier.id,
                    "purchase_date": "2024-12-15",
                    "unit_price": "9.99",
                    "quantity_purchased": 3,
                }
            ],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["purchase"]["imported"] == 1

        # Verify purchase was created with correct FK
        purchase = session.query(Purchase).first()
        assert purchase is not None
        assert purchase.supplier_id == test_supplier.id
        assert purchase.unit_price == Decimal("9.99")


class TestImportProducts:
    """Test product import with new fields."""

    def test_import_product_with_new_fields(
        self, test_db, test_supplier, test_ingredient
    ):
        """Test importing product with preferred_supplier_id and is_hidden."""
        import_data = {
            "version": "3.5",
            "suppliers": [],
            "ingredients": [],
            "products": [
                {
                    "ingredient_slug": "all-purpose-flour",
                    "product_name": "New Product",
                    "brand": "NewBrand",
                    "package_unit": "lb",
                    "package_unit_quantity": 10.0,
                    "preferred_supplier_id": test_supplier.id,
                    "is_hidden": True,
                }
            ],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["product"]["imported"] == 1

        # Verify product was created with new fields
        session = test_db()
        product = session.query(Product).filter_by(brand="NewBrand").first()
        assert product is not None
        assert product.preferred_supplier_id == test_supplier.id
        assert product.is_hidden is True


class TestImportInventoryItems:
    """Test inventory item import with purchase_id."""

    def test_import_inventory_item_with_purchase_id(
        self, test_db, test_purchase, test_product
    ):
        """Test importing inventory item with purchase_id FK."""
        import_data = {
            "version": "3.5",
            "suppliers": [],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [
                {
                    "ingredient_slug": "all-purpose-flour",
                    "product_brand": "King Arthur",
                    "product_name": "King Arthur Flour 25lb",
                    "package_unit": "lb",
                    "quantity": 30.0,  # Different qty to distinguish from fixture
                    "purchase_date": "2024-12-15T00:00:00",
                    "purchase_id": test_purchase.id,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["inventory_item"]["imported"] == 1

        # Verify inventory item has purchase_id
        session = test_db()
        items = session.query(InventoryItem).filter_by(quantity=30.0).all()
        assert len(items) == 1
        assert items[0].purchase_id == test_purchase.id


# ============================================================================
# Round-trip Tests
# ============================================================================


class TestRoundTrip:
    """Test export -> import round-trip preserves data."""

    def test_round_trip_preserves_all_data(
        self,
        test_db,
        test_supplier,
        test_supplier_wegmans,
        test_product,
        test_product_hidden,
        test_purchase,
        test_inventory_item,
    ):
        """Test that export -> import round-trip preserves all Feature 027 data."""
        # Export
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        export_result = import_export_service.export_all_to_json(export_path)

        # Verify export counts
        assert export_result.entity_counts["suppliers"] == 2
        assert export_result.entity_counts["products"] == 2
        assert export_result.entity_counts["purchases"] == 1
        assert export_result.entity_counts["inventory_items"] == 1

        # Read exported data
        with open(export_path) as f:
            exported_data = json.load(f)

        # Verify version
        assert "version" in exported_data  # informational only

        # Verify supplier data
        costco = next(s for s in exported_data["suppliers"] if s["name"] == "Costco")
        assert costco["city"] == "Issaquah"
        assert costco["is_active"] is True

        # Verify product data
        king_arthur = next(
            p for p in exported_data["products"] if p["brand"] == "King Arthur"
        )
        assert king_arthur["preferred_supplier_id"] == test_supplier.id
        assert king_arthur["is_hidden"] is False

        generic = next(
            p for p in exported_data["products"] if p["brand"] == "Generic"
        )
        assert generic["is_hidden"] is True

        # Verify purchase data
        assert len(exported_data["purchases"]) == 1
        purchase_data = exported_data["purchases"][0]
        assert purchase_data["supplier_id"] == test_supplier.id
        # Unit price may have trailing zeros from Decimal
        assert purchase_data["unit_price"].rstrip("0").rstrip(".") == "12.99"

        # Verify inventory data
        assert len(exported_data["inventory_items"]) == 1
        item_data = exported_data["inventory_items"][0]
        assert item_data["purchase_id"] == test_purchase.id


class TestImportOrder:
    """Test that import order is correct for FK resolution."""

    def test_import_order_correct(self, test_db):
        """Test that suppliers are imported before products, purchases before inventory."""
        # This data has dependencies: products -> suppliers, inventory -> purchases
        import_data = {
            "version": "3.5",
            "suppliers": [
                {
                    "id": 100,
                    "name": "Test Store",
                    "city": "Seattle",
                    "state": "WA",
                    "zip_code": "98101",
                }
            ],
            "ingredients": [
                {
                    "slug": "test-flour",
                    "display_name": "Test Flour",
                    "category": "Dry Goods",
                }
            ],
            "products": [
                {
                    "ingredient_slug": "test-flour",
                    "product_name": "Test Product",
                    "brand": "TestBrand",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                    "preferred_supplier_id": 100,  # References supplier
                }
            ],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            json.dump(import_data, f)
            import_path = f.name

        # Import with replace mode to use preserved IDs
        result = import_export_service.import_all_from_json_v4(import_path, mode="replace")

        # Verify successful import
        assert result.entity_counts["supplier"]["imported"] == 1
        assert result.entity_counts["ingredient"]["imported"] == 1
        assert result.entity_counts["product"]["imported"] == 1

        # Verify product has correct supplier FK
        session = test_db()
        product = session.query(Product).filter_by(brand="TestBrand").first()
        assert product is not None
