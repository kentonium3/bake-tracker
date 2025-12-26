"""
Tests for the Denormalized Export Service.

Tests cover:
- Products view export with context fields
- Inventory view export with product/purchase context
- Purchases view export with product/supplier context
- _meta editable/readonly field definitions
"""

import json
import os
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.models.ingredient import Ingredient
from src.models.inventory_item import InventoryItem
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.supplier import Supplier
from src.services.database import session_scope
from src.services.denormalized_export_service import (
    INVENTORY_VIEW_EDITABLE,
    INVENTORY_VIEW_READONLY,
    PRODUCTS_VIEW_EDITABLE,
    PRODUCTS_VIEW_READONLY,
    PURCHASES_VIEW_EDITABLE,
    PURCHASES_VIEW_READONLY,
    ExportResult,
    export_all_views,
    export_inventory_view,
    export_products_view,
    export_purchases_view,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cleanup_test_data(test_db):
    """Cleanup test data after each test."""
    yield
    with session_scope() as session:
        # Delete in reverse dependency order
        session.query(InventoryItem).delete(synchronize_session=False)
        session.query(Purchase).delete(synchronize_session=False)
        session.query(Product).delete(synchronize_session=False)
        session.query(Ingredient).delete(synchronize_session=False)
        session.query(Supplier).delete(synchronize_session=False)


@pytest.fixture
def sample_supplier(test_db):
    """Create a sample supplier for tests."""
    with session_scope() as session:
        supplier = Supplier(
            name="Costco",
            city="Boston",
            state="MA",
            zip_code="02101",
            notes="Bulk supplier",
        )
        session.add(supplier)
        session.flush()
        supplier_id = supplier.id
    return supplier_id


@pytest.fixture
def sample_ingredient(test_db):
    """Create a sample ingredient for tests."""
    with session_scope() as session:
        ingredient = Ingredient(
            slug="test_flour",
            display_name="All-Purpose Flour",
            category="Flour",
            description="Standard baking flour",
        )
        session.add(ingredient)
        session.flush()
        ingredient_id = ingredient.id
    return ingredient_id


@pytest.fixture
def sample_product(test_db, sample_ingredient, sample_supplier):
    """Create a sample product with preferred supplier for tests."""
    with session_scope() as session:
        product = Product(
            ingredient_id=sample_ingredient,
            brand="King Arthur",
            product_name="All-Purpose Flour",
            package_unit="lb",
            package_unit_quantity=5.0,
            package_size="5 lb bag",
            upc_code="123456789012",
            preferred_supplier_id=sample_supplier,
        )
        session.add(product)
        session.flush()
        product_id = product.id
    return product_id


@pytest.fixture
def sample_purchase(test_db, sample_product, sample_supplier):
    """Create a sample purchase for tests."""
    with session_scope() as session:
        purchase = Purchase(
            product_id=sample_product,
            supplier_id=sample_supplier,
            purchase_date=date(2025, 12, 15),
            unit_price=Decimal("12.99"),
            quantity_purchased=2,
            notes="Holiday stock up",
        )
        session.add(purchase)
        session.flush()
        purchase_id = purchase.id
    return purchase_id


@pytest.fixture
def sample_inventory_item(test_db, sample_product, sample_purchase):
    """Create a sample inventory item for tests."""
    with session_scope() as session:
        item = InventoryItem(
            product_id=sample_product,
            purchase_id=sample_purchase,
            quantity=10.0,
            unit_cost=12.99,
            purchase_date=date(2025, 12, 15),
            location="Main Storage",
            expiration_date=date(2026, 12, 15),
            notes="Holiday baking stock",
        )
        session.add(item)
        session.flush()
        item_id = item.id
    return item_id


# ============================================================================
# ExportResult Tests
# ============================================================================


class TestExportResult:
    """Tests for the ExportResult dataclass."""

    def test_export_result_creation(self):
        """Test ExportResult can be created with all fields."""
        result = ExportResult(
            view_type="products",
            record_count=10,
            output_path="/tmp/test.json",
            export_date="2025-12-25T10:00:00Z",
        )
        assert result.view_type == "products"
        assert result.record_count == 10
        assert result.output_path == "/tmp/test.json"
        assert result.export_date == "2025-12-25T10:00:00Z"


# ============================================================================
# Products View Export Tests
# ============================================================================


class TestExportProductsView:
    """Tests for export_products_view function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_products_view(temp_path)

            assert result.view_type == "products"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["view_type"] == "products"
            assert data["version"] == "1.0"
            assert "_meta" in data
            assert data["records"] == []
        finally:
            os.unlink(temp_path)

    def test_export_with_product(self, test_db, sample_product, cleanup_test_data):
        """Test export includes product data with context fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_products_view(temp_path)

            assert result.record_count == 1

            with open(temp_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            product = data["records"][0]

            # Verify product fields
            assert product["brand"] == "King Arthur"
            assert product["product_name"] == "All-Purpose Flour"
            assert product["package_unit"] == "lb"
            assert product["upc_code"] == "123456789012"

            # Verify ingredient context fields
            assert product["ingredient_slug"] == "test_flour"
            assert product["ingredient_name"] == "All-Purpose Flour"
            assert product["ingredient_category"] == "Flour"

        finally:
            os.unlink(temp_path)

    def test_export_includes_preferred_supplier(
        self, test_db, sample_product, cleanup_test_data
    ):
        """Test export includes preferred supplier name."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_products_view(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            product = data["records"][0]
            assert product["preferred_supplier_name"] == "Costco"

        finally:
            os.unlink(temp_path)

    def test_export_includes_last_purchase(
        self, test_db, sample_product, sample_purchase, cleanup_test_data
    ):
        """Test export includes last purchase price and date."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_products_view(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            product = data["records"][0]
            assert product["last_purchase_price"] == "12.99"
            assert product["last_purchase_date"] == "2025-12-15"

        finally:
            os.unlink(temp_path)

    def test_export_includes_inventory_quantity(
        self, test_db, sample_inventory_item, cleanup_test_data
    ):
        """Test export includes inventory quantity sum."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_products_view(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            product = data["records"][0]
            assert product["inventory_quantity"] == 10.0

        finally:
            os.unlink(temp_path)

    def test_export_meta_fields_present(self, test_db, cleanup_test_data):
        """Test _meta section includes editable and readonly fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_products_view(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert "editable_fields" in data["_meta"]
            assert "readonly_fields" in data["_meta"]
            assert data["_meta"]["editable_fields"] == PRODUCTS_VIEW_EDITABLE
            assert data["_meta"]["readonly_fields"] == PRODUCTS_VIEW_READONLY

        finally:
            os.unlink(temp_path)

    def test_export_uses_session_parameter(
        self, test_db, sample_product, cleanup_test_data
    ):
        """Test export works with passed session parameter."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            with session_scope() as session:
                result = export_products_view(temp_path, session=session)

            assert result.record_count == 1

        finally:
            os.unlink(temp_path)


# ============================================================================
# Inventory View Export Tests
# ============================================================================


class TestExportInventoryView:
    """Tests for export_inventory_view function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_inventory_view(temp_path)

            assert result.view_type == "inventory"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["view_type"] == "inventory"
            assert data["records"] == []
        finally:
            os.unlink(temp_path)

    def test_export_with_inventory_item(
        self, test_db, sample_inventory_item, cleanup_test_data
    ):
        """Test export includes inventory data with context fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_inventory_view(temp_path)

            assert result.record_count == 1

            with open(temp_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            item = data["records"][0]

            # Verify inventory fields
            assert item["quantity"] == 10.0
            assert item["location"] == "Main Storage"
            assert item["unit_cost"] == 12.99
            assert item["expiration_date"] == "2026-12-15"
            assert item["notes"] == "Holiday baking stock"

            # Verify product context
            assert item["brand"] == "King Arthur"
            assert item["package_unit"] == "lb"

            # Verify ingredient context
            assert item["ingredient_slug"] == "test_flour"
            assert item["ingredient_name"] == "All-Purpose Flour"

        finally:
            os.unlink(temp_path)

    def test_export_includes_product_slug(
        self, test_db, sample_inventory_item, cleanup_test_data
    ):
        """Test export includes composite product slug."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_inventory_view(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            item = data["records"][0]
            assert item["product_slug"] == "test_flour:King Arthur:5.0:lb"

        finally:
            os.unlink(temp_path)

    def test_export_meta_fields_present(self, test_db, cleanup_test_data):
        """Test _meta section includes editable and readonly fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_inventory_view(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert data["_meta"]["editable_fields"] == INVENTORY_VIEW_EDITABLE
            assert data["_meta"]["readonly_fields"] == INVENTORY_VIEW_READONLY

        finally:
            os.unlink(temp_path)


# ============================================================================
# Purchases View Export Tests
# ============================================================================


class TestExportPurchasesView:
    """Tests for export_purchases_view function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_purchases_view(temp_path)

            assert result.view_type == "purchases"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["view_type"] == "purchases"
            assert data["records"] == []
        finally:
            os.unlink(temp_path)

    def test_export_with_purchase(
        self, test_db, sample_purchase, cleanup_test_data
    ):
        """Test export includes purchase data with context fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_purchases_view(temp_path)

            assert result.record_count == 1

            with open(temp_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            purchase = data["records"][0]

            # Verify purchase fields
            assert purchase["purchase_date"] == "2025-12-15"
            assert purchase["unit_price"] == "12.99"
            assert purchase["quantity_purchased"] == 2
            assert purchase["notes"] == "Holiday stock up"

            # Verify product context
            assert purchase["brand"] == "King Arthur"
            assert purchase["product_name"] == "All-Purpose Flour"

            # Verify ingredient context
            assert purchase["ingredient_slug"] == "test_flour"
            assert purchase["ingredient_name"] == "All-Purpose Flour"

            # Verify supplier context
            assert purchase["supplier_name"] == "Costco"
            assert purchase["supplier_city"] == "Boston"
            assert purchase["supplier_state"] == "MA"

        finally:
            os.unlink(temp_path)

    def test_export_includes_total_cost(
        self, test_db, sample_purchase, cleanup_test_data
    ):
        """Test export includes calculated total cost."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_purchases_view(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            purchase = data["records"][0]
            # 12.99 * 2 = 25.98
            assert purchase["total_cost"] == "25.98"

        finally:
            os.unlink(temp_path)

    def test_export_meta_fields_present(self, test_db, cleanup_test_data):
        """Test _meta section includes editable and readonly fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_purchases_view(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert data["_meta"]["editable_fields"] == PURCHASES_VIEW_EDITABLE
            assert data["_meta"]["readonly_fields"] == PURCHASES_VIEW_READONLY

        finally:
            os.unlink(temp_path)


# ============================================================================
# Export All Views Tests
# ============================================================================


class TestExportAllViews:
    """Tests for export_all_views function."""

    def test_export_all_views_creates_files(self, test_db, cleanup_test_data):
        """Test export_all_views creates all three view files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = export_all_views(tmpdir)

            assert "products" in results
            assert "inventory" in results
            assert "purchases" in results

            # Verify files exist
            assert (Path(tmpdir) / "view_products.json").exists()
            assert (Path(tmpdir) / "view_inventory.json").exists()
            assert (Path(tmpdir) / "view_purchases.json").exists()

    def test_export_all_views_with_data(
        self, test_db, sample_inventory_item, cleanup_test_data
    ):
        """Test export_all_views exports all data correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = export_all_views(tmpdir)

            # All views should have records
            assert results["products"].record_count == 1
            assert results["inventory"].record_count == 1
            # Purchase was created as dependency for inventory_item
            assert results["purchases"].record_count == 1

    def test_export_all_views_uses_session(
        self, test_db, sample_product, cleanup_test_data
    ):
        """Test export_all_views works with passed session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with session_scope() as session:
                results = export_all_views(tmpdir, session=session)

            assert results["products"].record_count == 1


# ============================================================================
# Field Definition Tests
# ============================================================================


class TestFieldDefinitions:
    """Tests for editable/readonly field constant definitions."""

    def test_products_editable_fields(self):
        """Verify products editable fields match spec requirements."""
        required_editable = [
            "brand",
            "product_name",
            "package_size",
            "package_unit",
            "upc_code",
            "notes",
        ]
        for field in required_editable:
            assert field in PRODUCTS_VIEW_EDITABLE

    def test_products_readonly_includes_context(self):
        """Verify products readonly includes context fields."""
        context_fields = [
            "ingredient_name",
            "ingredient_category",
            "last_purchase_price",
            "inventory_quantity",
        ]
        for field in context_fields:
            assert field in PRODUCTS_VIEW_READONLY

    def test_inventory_editable_fields(self):
        """Verify inventory editable fields match spec requirements."""
        required_editable = ["quantity", "location", "notes"]
        for field in required_editable:
            assert field in INVENTORY_VIEW_EDITABLE

    def test_purchases_minimal_editable(self):
        """Verify purchases has minimal editable fields (historical data)."""
        # Purchases are historical - only notes should be editable
        assert PURCHASES_VIEW_EDITABLE == ["notes"]

    def test_no_overlap_editable_readonly(self):
        """Verify no fields appear in both editable and readonly."""
        products_overlap = set(PRODUCTS_VIEW_EDITABLE) & set(PRODUCTS_VIEW_READONLY)
        inventory_overlap = set(INVENTORY_VIEW_EDITABLE) & set(INVENTORY_VIEW_READONLY)
        purchases_overlap = set(PURCHASES_VIEW_EDITABLE) & set(PURCHASES_VIEW_READONLY)

        assert len(products_overlap) == 0
        assert len(inventory_overlap) == 0
        assert len(purchases_overlap) == 0
