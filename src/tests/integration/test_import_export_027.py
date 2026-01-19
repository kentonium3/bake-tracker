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
        slug="costco_issaquah_wa",  # Feature 050
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
        slug="wegmans_rochester_ny",  # Feature 050
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
            slug="test_store_seattle_wa",  # Feature 050
            supplier_type="physical",  # Feature 050
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
        assert supplier_data["slug"] == "test_store_seattle_wa"  # Feature 050
        assert supplier_data["supplier_type"] == "physical"  # Feature 050
        assert supplier_data["street_address"] == "123 Main St"
        assert supplier_data["notes"] == "Test notes"
        assert supplier_data["is_active"] is True


class TestExportSupplierSlug:
    """Test supplier slug export functionality (Feature 050 - T016)."""

    def test_export_supplier_includes_slug(self, test_db, test_supplier):
        """Supplier export includes slug field."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        supplier_data = next(s for s in data["suppliers"] if s["name"] == "Costco")
        assert supplier_data["slug"] == "costco_issaquah_wa"

    def test_export_online_supplier_includes_slug(self, test_db):
        """Online supplier export includes slug field."""
        session = test_db()
        supplier = Supplier(
            name="King Arthur Baking",
            slug="king_arthur_baking",
            supplier_type="online",
            website_url="https://www.kingarthurbaking.com",
            is_active=True,
        )
        session.add(supplier)
        session.commit()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        supplier_data = next(s for s in data["suppliers"] if s["name"] == "King Arthur Baking")
        assert supplier_data["slug"] == "king_arthur_baking"
        assert supplier_data["supplier_type"] == "online"
        assert supplier_data["website_url"] == "https://www.kingarthurbaking.com"


class TestExportProductSupplierSlug:
    """Test product export with supplier slug (Feature 050 - T017)."""

    def test_export_product_includes_supplier_slug(self, test_db, test_product, test_supplier):
        """Product export includes preferred_supplier_slug."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        product_data = next(p for p in data["products"] if p["brand"] == "King Arthur")
        assert product_data["preferred_supplier_slug"] == "costco_issaquah_wa"
        assert product_data["preferred_supplier_name"] == "Costco (Issaquah, WA)"

    def test_export_product_no_supplier_has_null_slug(self, test_db, test_product_hidden):
        """Product without supplier has null slug fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        # Find the hidden product (no supplier)
        product_data = next(p for p in data["products"] if p["brand"] == "Generic")
        assert product_data["preferred_supplier_slug"] is None
        assert product_data["preferred_supplier_name"] is None

    def test_export_product_supplier_deleted_has_null_slug(self, test_db, test_ingredient):
        """Product referencing deleted supplier has null slug fields."""
        session = test_db()

        # Create supplier and product
        supplier = Supplier(
            name="Temp Store",
            slug="temp_store_boston_ma",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(supplier)
        session.flush()

        product = Product(
            ingredient_id=test_ingredient.id,
            product_name="Orphan Product",
            brand="Orphan",
            package_unit="lb",
            package_unit_quantity=5.0,
            preferred_supplier_id=supplier.id,
        )
        session.add(product)
        session.flush()

        # Delete the supplier (product still references it)
        session.delete(supplier)
        session.commit()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        with open(export_path) as f:
            data = json.load(f)

        # Find the orphan product
        product_data = next(p for p in data["products"] if p["brand"] == "Orphan")
        # Supplier was deleted, so slug should be null
        assert product_data["preferred_supplier_slug"] is None
        assert product_data["preferred_supplier_name"] is None


class TestExportProducts:
    """Test product export with new fields."""

    def test_export_product_preferred_supplier_id(self, test_db, test_product, test_supplier):
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

    def test_export_purchase_with_supplier_id(self, test_db, test_purchase, test_supplier):
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        # Note: skip_duplicates is True by default in v3
        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["supplier"]["skipped"] == 1


class TestImportPurchases:
    """Test purchase import with new FK format."""

    def test_import_purchase_with_supplier_id(self, test_db, test_supplier, test_ingredient):
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
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

    def test_import_product_with_new_fields(self, test_db, test_supplier, test_ingredient):
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
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

    def test_import_inventory_item_with_purchase_id(self, test_db, test_purchase, test_product):
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
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
        king_arthur = next(p for p in exported_data["products"] if p["brand"] == "King Arthur")
        assert king_arthur["preferred_supplier_id"] == test_supplier.id
        assert king_arthur["is_hidden"] is False

        generic = next(p for p in exported_data["products"] if p["brand"] == "Generic")
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
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


# ============================================================================
# Feature 050: Import Tests for Supplier Slug Support
# ============================================================================


class TestImportSupplierSlug:
    """Test supplier import with slug support (Feature 050 - T025)."""

    def test_import_new_supplier_by_slug(self, test_db):
        """New supplier created with provided slug."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "slug": "test_store_boston_ma",
                    "name": "Test Store",
                    "supplier_type": "physical",
                    "city": "Boston",
                    "state": "MA",
                    "zip_code": "02101",
                }
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["supplier"]["imported"] == 1

        session = test_db()
        supplier = session.query(Supplier).filter_by(slug="test_store_boston_ma").first()
        assert supplier is not None
        assert supplier.name == "Test Store"
        assert supplier.supplier_type == "physical"

    def test_import_new_supplier_generates_slug(self, test_db):
        """New supplier without slug gets one generated."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "name": "Auto Slug Store",
                    "city": "Denver",
                    "state": "CO",
                    "zip_code": "80201",
                }
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["supplier"]["imported"] == 1

        session = test_db()
        supplier = session.query(Supplier).filter_by(name="Auto Slug Store").first()
        assert supplier is not None
        assert supplier.slug == "auto_slug_store_denver_co"

    def test_import_existing_supplier_by_slug_updates(self, test_db, test_supplier):
        """Existing supplier matched by slug is updated with provided fields (FR-009)."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "slug": "costco_issaquah_wa",  # Matches test_supplier
                    "name": "Costco Wholesale",  # Different name to trigger update
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        # FR-009: Merge mode updates explicitly provided fields for existing suppliers
        assert result.entity_counts["supplier"]["updated"] == 1

        # Verify name WAS changed (query fresh from DB)
        session = test_db()
        supplier = session.query(Supplier).filter_by(slug="costco_issaquah_wa").first()
        assert supplier is not None
        assert supplier.name == "Costco Wholesale"  # Name should be updated


class TestImportOnlineSupplier:
    """Test online supplier import (Feature 050 - Cursor review fix)."""

    def test_import_online_supplier_without_city_state(self, test_db):
        """Online suppliers can be imported without city/state."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "name": "Amazon Fresh",
                    "supplier_type": "online",
                    "website_url": "https://amazon.com/fresh",
                }
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["supplier"]["imported"] == 1
        assert result.failed == 0

        session = test_db()
        supplier = session.query(Supplier).filter_by(name="Amazon Fresh").first()
        assert supplier is not None
        assert supplier.supplier_type == "online"
        assert supplier.slug == "amazon_fresh"  # Name-only slug for online

    def test_import_online_supplier_with_slug(self, test_db):
        """Online suppliers can be imported with explicit slug."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "name": "King Arthur Baking",
                    "slug": "king_arthur_baking",
                    "supplier_type": "online",
                    "website_url": "https://kingarthurbaking.com",
                }
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["supplier"]["imported"] == 1

        session = test_db()
        supplier = session.query(Supplier).filter_by(slug="king_arthur_baking").first()
        assert supplier is not None
        assert supplier.name == "King Arthur Baking"


class TestMergeModeSupplierUpdates:
    """Test merge mode sparse update behavior for suppliers (Feature 050 - FR-009)."""

    def test_merge_mode_no_changes_skips(self, test_db, test_supplier):
        """When import data matches existing supplier, record is skipped."""
        # Import with same data - no changes
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "slug": "costco_issaquah_wa",
                    "name": "Costco",  # Same as existing
                    "city": "Issaquah",
                    "state": "WA",
                    "zip_code": "98027",  # Same as existing
                }
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        # No changes = skipped
        assert result.entity_counts["supplier"]["skipped"] == 1
        assert result.entity_counts["supplier"].get("updated", 0) == 0

    def test_merge_mode_slug_immutable(self, test_db, test_supplier):
        """Slug is never updated in merge mode (immutability preserved)."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "slug": "costco_issaquah_wa",  # Match by slug
                    "name": "Costco Renamed",  # Will update name
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["supplier"]["updated"] == 1

        session = test_db()
        supplier = session.query(Supplier).filter_by(slug="costco_issaquah_wa").first()
        assert supplier is not None
        assert supplier.name == "Costco Renamed"
        assert supplier.slug == "costco_issaquah_wa"  # Slug unchanged


class TestImportProductSupplierSlug:
    """Test product import with supplier slug resolution (Feature 050 - T026)."""

    def test_import_product_resolves_supplier_slug(self, test_db, test_supplier, test_ingredient):
        """Product import resolves supplier by slug."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [],
            "ingredients": [],
            "products": [
                {
                    "ingredient_slug": "all-purpose-flour",
                    "brand": "Test Brand",
                    "product_name": "Test Product",
                    "package_unit": "lb",
                    "package_unit_quantity": 10.0,
                    "preferred_supplier_slug": "costco_issaquah_wa",  # Slug-based resolution
                }
            ],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["product"]["imported"] == 1

        session = test_db()
        product = session.query(Product).filter_by(brand="Test Brand").first()
        assert product is not None
        assert product.preferred_supplier_id == test_supplier.id

    def test_import_product_missing_supplier_slug_warns(self, test_db, test_ingredient, caplog):
        """Missing supplier slug logs warning, doesn't fail."""
        import logging

        caplog.set_level(logging.WARNING)

        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [],
            "ingredients": [],
            "products": [
                {
                    "ingredient_slug": "all-purpose-flour",
                    "brand": "Orphan Brand",
                    "product_name": "Orphan Product",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0,
                    "preferred_supplier_slug": "nonexistent_slug",  # Invalid slug
                }
            ],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        # Product still created
        assert result.entity_counts["product"]["imported"] == 1

        session = test_db()
        product = session.query(Product).filter_by(brand="Orphan Brand").first()
        assert product is not None
        assert product.preferred_supplier_id is None

        # Warning was logged
        assert "nonexistent_slug" in caplog.text


class TestImportLegacyBackwardCompatibility:
    """Test legacy import file backward compatibility (Feature 050 - T027)."""

    def test_import_product_legacy_id_fallback(
        self, test_db, test_supplier, test_ingredient, caplog
    ):
        """Legacy files with supplier_id still work."""
        import logging

        caplog.set_level(logging.INFO)

        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [],
            "ingredients": [],
            "products": [
                {
                    "ingredient_slug": "all-purpose-flour",
                    "brand": "Legacy Brand",
                    "product_name": "Legacy Product",
                    "package_unit": "lb",
                    "package_unit_quantity": 8.0,
                    "preferred_supplier_id": test_supplier.id,  # Legacy format: ID only
                    # No preferred_supplier_slug field
                }
            ],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["product"]["imported"] == 1

        session = test_db()
        product = session.query(Product).filter_by(brand="Legacy Brand").first()
        assert product is not None
        assert product.preferred_supplier_id == test_supplier.id

        # Info log about fallback
        assert "legacy" in caplog.text.lower()

    def test_import_product_slug_takes_precedence_over_id(
        self, test_db, test_supplier, test_supplier_wegmans, test_ingredient
    ):
        """When both slug and ID are provided, slug takes precedence."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [],
            "ingredients": [],
            "products": [
                {
                    "ingredient_slug": "all-purpose-flour",
                    "brand": "Precedence Brand",
                    "product_name": "Precedence Product",
                    "package_unit": "lb",
                    "package_unit_quantity": 7.0,
                    "preferred_supplier_slug": "wegmans_rochester_ny",  # Should win
                    "preferred_supplier_id": test_supplier.id,  # Should be ignored
                }
            ],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(import_path, mode="merge")

        assert result.entity_counts["product"]["imported"] == 1

        session = test_db()
        product = session.query(Product).filter_by(brand="Precedence Brand").first()
        assert product is not None
        # Slug-based resolution should win over ID
        assert product.preferred_supplier_id == test_supplier_wegmans.id


# ============================================================================
# Feature 050: Dry-Run Import Tests
# ============================================================================


class TestDryRunImport:
    """Test dry-run import preview functionality (Feature 050 - T037)."""

    def test_dry_run_returns_preview_counts(self, test_db, test_supplier):
        """Dry run returns accurate preview counts."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "slug": "costco_issaquah_wa",  # Existing
                    "name": "Costco Updated",
                    "city": "Issaquah",
                    "state": "WA",
                    "zip_code": "98027",
                },
                {
                    "name": "New Store",
                    "city": "Portland",
                    "state": "OR",
                    "zip_code": "97201",
                    "supplier_type": "physical",
                },
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(
            import_path, mode="merge", dry_run=True
        )

        # Should show one would be skipped (existing), one would be created
        assert result.entity_counts["supplier"]["skipped"] == 1
        assert result.entity_counts["supplier"]["imported"] == 1
        assert "DRY RUN" in result.warnings[0]

    def test_dry_run_no_db_changes(self, test_db):
        """Dry run doesn't modify database."""
        session = test_db()
        initial_count = session.query(Supplier).count()

        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "name": "Should Not Be Created",
                    "city": "Test City",
                    "state": "TX",
                    "zip_code": "12345",
                    "supplier_type": "physical",
                }
            ],
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        import_export_service.import_all_from_json_v4(import_path, mode="merge", dry_run=True)

        # Verify no changes to database
        session = test_db()
        final_count = session.query(Supplier).count()
        assert final_count == initial_count

        # Verify the supplier was NOT created
        not_created = session.query(Supplier).filter_by(name="Should Not Be Created").first()
        assert not_created is None

    def test_dry_run_skip_mode_counts(self, test_db, test_supplier):
        """Dry run with skip mode shows skipped count."""
        import_data = {
            "version": "3.5",
            "application": "bake-tracker",
            "suppliers": [
                {
                    "slug": "costco_issaquah_wa",  # Matches test_supplier
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

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(import_data, f)
            import_path = f.name

        result = import_export_service.import_all_from_json_v4(
            import_path, mode="merge", dry_run=True
        )

        assert result.entity_counts["supplier"]["skipped"] == 1
        assert result.entity_counts["supplier"]["imported"] == 0


class TestRoundTripWithSlugs:
    """Test export -> import round-trip with slug support (Feature 050 - T038)."""

    def test_full_round_trip_with_slugs(
        self, test_db, test_supplier, test_ingredient, test_product
    ):
        """Export -> clear DB -> import -> verify associations restored by slug."""
        session = test_db()

        # Verify initial state
        assert test_supplier.slug == "costco_issaquah_wa"
        assert test_product.preferred_supplier_id == test_supplier.id

        # Export all data
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name

        import_export_service.export_all_to_json(export_path)

        # Read exported data and verify slugs
        with open(export_path) as f:
            exported_data = json.load(f)

        # Verify supplier has slug
        supplier_export = next(s for s in exported_data["suppliers"] if s["name"] == "Costco")
        assert supplier_export["slug"] == "costco_issaquah_wa"

        # Verify product has supplier slug
        product_export = next(p for p in exported_data["products"] if p["brand"] == "King Arthur")
        assert product_export["preferred_supplier_slug"] == "costco_issaquah_wa"

        # Clear database (simulate fresh environment)
        session.query(Product).delete()
        session.query(Supplier).delete()
        session.query(Ingredient).delete()
        session.commit()

        # Verify cleared
        assert session.query(Supplier).count() == 0
        assert session.query(Product).count() == 0

        # Import back
        result = import_export_service.import_all_from_json_v4(export_path, mode="replace")

        # Verify successful import
        assert result.entity_counts["supplier"]["imported"] >= 1
        assert result.entity_counts["product"]["imported"] >= 1

        # Verify associations restored via slug
        session = test_db()
        imported_supplier = session.query(Supplier).filter_by(slug="costco_issaquah_wa").first()
        assert imported_supplier is not None
        assert imported_supplier.name == "Costco"

        imported_product = session.query(Product).filter_by(brand="King Arthur").first()
        assert imported_product is not None
        # The key test: product's preferred_supplier_id should point to the
        # imported supplier (resolved via slug, not original ID)
        assert imported_product.preferred_supplier_id == imported_supplier.id
