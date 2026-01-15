"""
Tests for the Denormalized Export Service.

Tests cover:
- Products context-rich export with context fields
- Inventory context-rich export with product/purchase context
- Purchases context-rich export with product/supplier context
- Ingredients context-rich export with hierarchy and computed values
- Materials context-rich export with hierarchy
- Recipes context-rich export with embedded ingredients and costs
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
from src.models.material import Material
from src.models.material_category import MaterialCategory
from src.models.material_product import MaterialProduct
from src.models.material_subcategory import MaterialSubcategory
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.recipe import Recipe, RecipeIngredient
from src.models.supplier import Supplier
from src.services.database import session_scope
from src.services.denormalized_export_service import (
    INGREDIENTS_CONTEXT_RICH_EDITABLE,
    INGREDIENTS_CONTEXT_RICH_READONLY,
    INVENTORY_CONTEXT_RICH_EDITABLE,
    INVENTORY_CONTEXT_RICH_READONLY,
    MATERIALS_CONTEXT_RICH_EDITABLE,
    MATERIALS_CONTEXT_RICH_READONLY,
    PRODUCTS_CONTEXT_RICH_EDITABLE,
    PRODUCTS_CONTEXT_RICH_READONLY,
    PURCHASES_CONTEXT_RICH_EDITABLE,
    PURCHASES_CONTEXT_RICH_READONLY,
    RECIPES_CONTEXT_RICH_EDITABLE,
    RECIPES_CONTEXT_RICH_READONLY,
    ExportResult,
    export_all_context_rich,
    export_ingredients_context_rich,
    export_inventory_context_rich,
    export_materials_context_rich,
    export_products_context_rich,
    export_purchases_context_rich,
    export_recipes_context_rich,
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


@pytest.fixture
def sample_ingredient_with_hierarchy(test_db):
    """Create sample ingredients with parent-child hierarchy for tests."""
    with session_scope() as session:
        # Create root ingredient (level 0)
        root = Ingredient(
            slug="chocolate",
            display_name="Chocolate",
            category="Chocolate",
            hierarchy_level=0,
            description="All chocolate products",
        )
        session.add(root)
        session.flush()
        root_id = root.id

        # Create mid-level ingredient (level 1)
        mid = Ingredient(
            slug="dark_chocolate",
            display_name="Dark Chocolate",
            category="Chocolate",
            hierarchy_level=1,
            parent_ingredient_id=root_id,
        )
        session.add(mid)
        session.flush()
        mid_id = mid.id

        # Create leaf ingredient (level 2)
        leaf = Ingredient(
            slug="semi_sweet_chips",
            display_name="Semi-Sweet Chips",
            category="Chocolate",
            hierarchy_level=2,
            parent_ingredient_id=mid_id,
            description="Semi-sweet chocolate chips",
        )
        session.add(leaf)
        session.flush()
        leaf_id = leaf.id

    return {"root": root_id, "mid": mid_id, "leaf": leaf_id}


@pytest.fixture
def sample_material_hierarchy(test_db):
    """Create sample material hierarchy for tests."""
    with session_scope() as session:
        # Create category
        category = MaterialCategory(
            name="Ribbons",
            slug="ribbons",
            description="All ribbons",
        )
        session.add(category)
        session.flush()
        category_id = category.id

        # Create subcategory
        subcategory = MaterialSubcategory(
            category_id=category_id,
            name="Satin",
            slug="satin",
            description="Satin ribbons",
        )
        session.add(subcategory)
        session.flush()
        subcategory_id = subcategory.id

        # Create material
        material = Material(
            subcategory_id=subcategory_id,
            name="Red Satin Ribbon",
            slug="red-satin-ribbon",
            description="1-inch red satin ribbon",
            base_unit_type="linear_inches",
        )
        session.add(material)
        session.flush()
        material_id = material.id

    return {
        "category": category_id,
        "subcategory": subcategory_id,
        "material": material_id,
    }


@pytest.fixture
def sample_material_with_product(test_db, sample_material_hierarchy, sample_supplier):
    """Create sample material with a product for tests."""
    with session_scope() as session:
        product = MaterialProduct(
            material_id=sample_material_hierarchy["material"],
            supplier_id=sample_supplier,
            name="100ft Red Satin Roll",
            slug="red-satin-100ft",
            brand="Michaels",
            package_quantity=100,
            package_unit="feet",
            quantity_in_base_units=1200,  # 100 feet = 1200 inches
            current_inventory=600,  # 50 feet remaining
            weighted_avg_cost=Decimal("0.05"),  # $0.05 per inch
        )
        session.add(product)
        session.flush()
        product_id = product.id
    return product_id


@pytest.fixture
def sample_recipe(test_db, sample_ingredient):
    """Create a sample recipe with ingredients for tests."""
    with session_scope() as session:
        recipe = Recipe(
            name="Chocolate Chip Cookies",
            category="Cookies",
            source="Family Recipe",
            yield_quantity=24,
            yield_unit="cookies",
            yield_description="2-inch cookies",
            estimated_time_minutes=45,
            notes="Classic recipe",
        )
        session.add(recipe)
        session.flush()
        recipe_id = recipe.id

        # Add recipe ingredient
        ri = RecipeIngredient(
            recipe_id=recipe_id,
            ingredient_id=sample_ingredient,
            quantity=2.5,
            unit="cup",
            notes="sifted",
        )
        session.add(ri)

    return recipe_id


@pytest.fixture
def cleanup_extended_test_data(test_db):
    """Cleanup extended test data after each test."""
    yield
    with session_scope() as session:
        # Delete in reverse dependency order
        session.query(RecipeIngredient).delete(synchronize_session=False)
        session.query(Recipe).delete(synchronize_session=False)
        session.query(MaterialProduct).delete(synchronize_session=False)
        session.query(Material).delete(synchronize_session=False)
        session.query(MaterialSubcategory).delete(synchronize_session=False)
        session.query(MaterialCategory).delete(synchronize_session=False)
        session.query(InventoryItem).delete(synchronize_session=False)
        session.query(Purchase).delete(synchronize_session=False)
        session.query(Product).delete(synchronize_session=False)
        session.query(Ingredient).delete(synchronize_session=False)
        session.query(Supplier).delete(synchronize_session=False)


# ============================================================================
# ExportResult Tests
# ============================================================================


class TestExportResult:
    """Tests for the ExportResult dataclass."""

    def test_export_result_creation(self):
        """Test ExportResult can be created with all fields."""
        result = ExportResult(
            export_type="products",
            record_count=10,
            output_path="/tmp/test.json",
            export_date="2025-12-25T10:00:00Z",
        )
        assert result.export_type == "products"
        assert result.record_count == 10
        assert result.output_path == "/tmp/test.json"
        assert result.export_date == "2025-12-25T10:00:00Z"


# ============================================================================
# Products Context-Rich Export Tests
# ============================================================================


class TestExportProductsContextRich:
    """Tests for export_products_context_rich function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_products_context_rich(temp_path)

            assert result.export_type == "products"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "products"
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
            result = export_products_context_rich(temp_path)

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
            result = export_products_context_rich(temp_path)

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
            result = export_products_context_rich(temp_path)

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
            result = export_products_context_rich(temp_path)

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
            export_products_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert "editable_fields" in data["_meta"]
            assert "readonly_fields" in data["_meta"]
            assert data["_meta"]["editable_fields"] == PRODUCTS_CONTEXT_RICH_EDITABLE
            assert data["_meta"]["readonly_fields"] == PRODUCTS_CONTEXT_RICH_READONLY

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
                result = export_products_context_rich(temp_path, session=session)

            assert result.record_count == 1

        finally:
            os.unlink(temp_path)


# ============================================================================
# Inventory Context-Rich Export Tests
# ============================================================================


class TestExportInventoryContextRich:
    """Tests for export_inventory_context_rich function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_inventory_context_rich(temp_path)

            assert result.export_type == "inventory"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "inventory"
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
            result = export_inventory_context_rich(temp_path)

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
            export_inventory_context_rich(temp_path)

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
            export_inventory_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert data["_meta"]["editable_fields"] == INVENTORY_CONTEXT_RICH_EDITABLE
            assert data["_meta"]["readonly_fields"] == INVENTORY_CONTEXT_RICH_READONLY

        finally:
            os.unlink(temp_path)


# ============================================================================
# Purchases Context-Rich Export Tests
# ============================================================================


class TestExportPurchasesContextRich:
    """Tests for export_purchases_context_rich function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_purchases_context_rich(temp_path)

            assert result.export_type == "purchases"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "purchases"
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
            result = export_purchases_context_rich(temp_path)

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
            export_purchases_context_rich(temp_path)

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
            export_purchases_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert data["_meta"]["editable_fields"] == PURCHASES_CONTEXT_RICH_EDITABLE
            assert data["_meta"]["readonly_fields"] == PURCHASES_CONTEXT_RICH_READONLY

        finally:
            os.unlink(temp_path)


# ============================================================================
# Export All Context-Rich Tests
# ============================================================================


class TestExportAllContextRich:
    """Tests for export_all_context_rich function."""

    def test_export_all_context_rich_creates_files(self, test_db, cleanup_test_data):
        """Test export_all_context_rich creates all three context-rich files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = export_all_context_rich(tmpdir)

            assert "products" in results
            assert "inventory" in results
            assert "purchases" in results

            # Verify files exist
            assert (Path(tmpdir) / "aug_products.json").exists()
            assert (Path(tmpdir) / "aug_inventory.json").exists()
            assert (Path(tmpdir) / "aug_purchases.json").exists()

    def test_export_all_context_rich_with_data(
        self, test_db, sample_inventory_item, cleanup_test_data
    ):
        """Test export_all_context_rich exports all data correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = export_all_context_rich(tmpdir)

            # All exports should have records
            assert results["products"].record_count == 1
            assert results["inventory"].record_count == 1
            # Purchase was created as dependency for inventory_item
            assert results["purchases"].record_count == 1

    def test_export_all_context_rich_uses_session(
        self, test_db, sample_product, cleanup_test_data
    ):
        """Test export_all_context_rich works with passed session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with session_scope() as session:
                results = export_all_context_rich(tmpdir, session=session)

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
            assert field in PRODUCTS_CONTEXT_RICH_EDITABLE

    def test_products_readonly_includes_context(self):
        """Verify products readonly includes context fields."""
        context_fields = [
            "ingredient_name",
            "ingredient_category",
            "last_purchase_price",
            "inventory_quantity",
        ]
        for field in context_fields:
            assert field in PRODUCTS_CONTEXT_RICH_READONLY

    def test_inventory_editable_fields(self):
        """Verify inventory editable fields match spec requirements."""
        required_editable = ["quantity", "location", "notes"]
        for field in required_editable:
            assert field in INVENTORY_CONTEXT_RICH_EDITABLE

    def test_purchases_minimal_editable(self):
        """Verify purchases has minimal editable fields (historical data)."""
        # Purchases are historical - only notes should be editable
        assert PURCHASES_CONTEXT_RICH_EDITABLE == ["notes"]

    def test_no_overlap_editable_readonly(self):
        """Verify no fields appear in both editable and readonly."""
        products_overlap = set(PRODUCTS_CONTEXT_RICH_EDITABLE) & set(PRODUCTS_CONTEXT_RICH_READONLY)
        inventory_overlap = set(INVENTORY_CONTEXT_RICH_EDITABLE) & set(INVENTORY_CONTEXT_RICH_READONLY)
        purchases_overlap = set(PURCHASES_CONTEXT_RICH_EDITABLE) & set(PURCHASES_CONTEXT_RICH_READONLY)
        ingredients_overlap = set(INGREDIENTS_CONTEXT_RICH_EDITABLE) & set(INGREDIENTS_CONTEXT_RICH_READONLY)
        materials_overlap = set(MATERIALS_CONTEXT_RICH_EDITABLE) & set(MATERIALS_CONTEXT_RICH_READONLY)
        recipes_overlap = set(RECIPES_CONTEXT_RICH_EDITABLE) & set(RECIPES_CONTEXT_RICH_READONLY)

        assert len(products_overlap) == 0
        assert len(inventory_overlap) == 0
        assert len(purchases_overlap) == 0
        assert len(ingredients_overlap) == 0
        assert len(materials_overlap) == 0
        assert len(recipes_overlap) == 0


# ============================================================================
# Ingredients Context-Rich Export Tests
# ============================================================================


class TestExportIngredientsContextRich:
    """Tests for export_ingredients_context_rich function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_ingredients_context_rich(temp_path)

            assert result.export_type == "ingredients"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "ingredients"
            assert data["version"] == "1.0"
            assert "_meta" in data
            assert data["records"] == []
        finally:
            os.unlink(temp_path)

    def test_export_with_ingredient(self, test_db, sample_ingredient, cleanup_test_data):
        """Test export includes ingredient data."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_ingredients_context_rich(temp_path)

            assert result.record_count == 1

            with open(temp_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            ingredient = data["records"][0]

            # Verify ingredient fields
            assert ingredient["slug"] == "test_flour"
            assert ingredient["display_name"] == "All-Purpose Flour"
            assert ingredient["category"] == "Flour"
            assert ingredient["description"] == "Standard baking flour"

        finally:
            os.unlink(temp_path)

    def test_export_includes_hierarchy_path(
        self, test_db, sample_ingredient_with_hierarchy, cleanup_extended_test_data
    ):
        """Test export includes full category hierarchy path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_ingredients_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            # Find the leaf ingredient
            leaf_record = None
            for record in data["records"]:
                if record["slug"] == "semi_sweet_chips":
                    leaf_record = record
                    break

            assert leaf_record is not None
            # Should have full hierarchy path
            assert "Chocolate" in leaf_record["category_hierarchy"]
            assert "Dark Chocolate" in leaf_record["category_hierarchy"]
            assert "Semi-Sweet Chips" in leaf_record["category_hierarchy"]
            assert " > " in leaf_record["category_hierarchy"]

        finally:
            os.unlink(temp_path)

    def test_export_includes_products_array(
        self, test_db, sample_product, cleanup_test_data
    ):
        """Test export includes nested products array."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_ingredients_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            ingredient = data["records"][0]

            assert "products" in ingredient
            assert len(ingredient["products"]) == 1

            product = ingredient["products"][0]
            assert product["brand"] == "King Arthur"
            assert product["product_name"] == "All-Purpose Flour"

        finally:
            os.unlink(temp_path)

    def test_export_includes_inventory_total(
        self, test_db, sample_inventory_item, cleanup_test_data
    ):
        """Test export includes computed inventory total."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_ingredients_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            ingredient = data["records"][0]

            assert "inventory_total" in ingredient
            assert ingredient["inventory_total"] == 10.0

        finally:
            os.unlink(temp_path)

    def test_export_includes_average_cost(
        self, test_db, sample_inventory_item, cleanup_test_data
    ):
        """Test export includes computed average cost."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_ingredients_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            ingredient = data["records"][0]

            assert "average_cost" in ingredient
            # Should be the unit cost from inventory item
            assert ingredient["average_cost"] == 12.99

        finally:
            os.unlink(temp_path)

    def test_export_meta_fields_present(self, test_db, cleanup_test_data):
        """Test _meta section includes editable and readonly fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_ingredients_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert "editable_fields" in data["_meta"]
            assert "readonly_fields" in data["_meta"]
            assert data["_meta"]["editable_fields"] == INGREDIENTS_CONTEXT_RICH_EDITABLE
            assert data["_meta"]["readonly_fields"] == INGREDIENTS_CONTEXT_RICH_READONLY

        finally:
            os.unlink(temp_path)


# ============================================================================
# Materials Context-Rich Export Tests
# ============================================================================


class TestExportMaterialsContextRich:
    """Tests for export_materials_context_rich function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_materials_context_rich(temp_path)

            assert result.export_type == "materials"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "materials"
            assert data["version"] == "1.0"
            assert "_meta" in data
            assert data["records"] == []
        finally:
            os.unlink(temp_path)

    def test_export_with_material(
        self, test_db, sample_material_hierarchy, cleanup_extended_test_data
    ):
        """Test export includes material data."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_materials_context_rich(temp_path)

            assert result.record_count == 1

            with open(temp_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            material = data["records"][0]

            # Verify material fields
            assert material["slug"] == "red-satin-ribbon"
            assert material["name"] == "Red Satin Ribbon"
            assert material["base_unit_type"] == "linear_inches"

        finally:
            os.unlink(temp_path)

    def test_export_includes_hierarchy_path(
        self, test_db, sample_material_hierarchy, cleanup_extended_test_data
    ):
        """Test export includes full category hierarchy path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_materials_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            material = data["records"][0]

            # Should have full hierarchy: Category > Subcategory > Material
            assert material["category_hierarchy"] == "Ribbons > Satin > Red Satin Ribbon"

        finally:
            os.unlink(temp_path)

    def test_export_includes_products_array(
        self, test_db, sample_material_with_product, cleanup_extended_test_data
    ):
        """Test export includes nested products array."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_materials_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            material = data["records"][0]

            assert "products" in material
            assert len(material["products"]) == 1

            product = material["products"][0]
            assert product["name"] == "100ft Red Satin Roll"
            assert product["brand"] == "Michaels"
            assert product["current_inventory"] == 600

        finally:
            os.unlink(temp_path)

    def test_export_includes_inventory_totals(
        self, test_db, sample_material_with_product, cleanup_extended_test_data
    ):
        """Test export includes computed inventory totals."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_materials_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            material = data["records"][0]

            assert "total_inventory" in material
            assert material["total_inventory"] == 600.0

            assert "total_inventory_value" in material
            # 600 inches * $0.05/inch = $30.00
            assert material["total_inventory_value"] == 30.0

        finally:
            os.unlink(temp_path)

    def test_export_meta_fields_present(self, test_db, cleanup_test_data):
        """Test _meta section includes editable and readonly fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_materials_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert data["_meta"]["editable_fields"] == MATERIALS_CONTEXT_RICH_EDITABLE
            assert data["_meta"]["readonly_fields"] == MATERIALS_CONTEXT_RICH_READONLY

        finally:
            os.unlink(temp_path)


# ============================================================================
# Recipes Context-Rich Export Tests
# ============================================================================


class TestExportRecipesContextRich:
    """Tests for export_recipes_context_rich function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates file with 0 records."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_recipes_context_rich(temp_path)

            assert result.export_type == "recipes"
            assert result.record_count == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "recipes"
            assert data["version"] == "1.0"
            assert "_meta" in data
            assert data["records"] == []
        finally:
            os.unlink(temp_path)

    def test_export_with_recipe(
        self, test_db, sample_recipe, cleanup_extended_test_data
    ):
        """Test export includes recipe data."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_recipes_context_rich(temp_path)

            assert result.record_count == 1

            with open(temp_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            recipe = data["records"][0]

            # Verify recipe fields
            assert recipe["name"] == "Chocolate Chip Cookies"
            assert recipe["category"] == "Cookies"
            assert recipe["source"] == "Family Recipe"
            assert recipe["yield_quantity"] == 24
            assert recipe["yield_unit"] == "cookies"
            assert recipe["estimated_time_minutes"] == 45

        finally:
            os.unlink(temp_path)

    def test_export_includes_embedded_ingredients(
        self, test_db, sample_recipe, cleanup_extended_test_data
    ):
        """Test export includes nested ingredients array."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_recipes_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            recipe = data["records"][0]

            assert "ingredients" in recipe
            assert len(recipe["ingredients"]) == 1

            ingredient = recipe["ingredients"][0]
            assert ingredient["ingredient_slug"] == "test_flour"
            assert ingredient["ingredient_name"] == "All-Purpose Flour"
            assert ingredient["quantity"] == 2.5
            assert ingredient["unit"] == "cup"
            assert ingredient["notes"] == "sifted"

        finally:
            os.unlink(temp_path)

    def test_export_includes_computed_costs(
        self, test_db, sample_recipe, cleanup_extended_test_data
    ):
        """Test export includes computed cost fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_recipes_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            recipe = data["records"][0]

            # Cost fields should be present (may be None if no pricing data)
            assert "total_cost" in recipe
            assert "cost_per_unit" in recipe

        finally:
            os.unlink(temp_path)

    def test_export_meta_fields_present(self, test_db, cleanup_test_data):
        """Test _meta section includes editable and readonly fields."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_recipes_context_rich(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert "_meta" in data
            assert data["_meta"]["editable_fields"] == RECIPES_CONTEXT_RICH_EDITABLE
            assert data["_meta"]["readonly_fields"] == RECIPES_CONTEXT_RICH_READONLY

        finally:
            os.unlink(temp_path)

    def test_export_uses_session_parameter(
        self, test_db, sample_recipe, cleanup_extended_test_data
    ):
        """Test export works with passed session parameter."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            with session_scope() as session:
                result = export_recipes_context_rich(temp_path, session=session)

            assert result.record_count == 1

        finally:
            os.unlink(temp_path)


# ============================================================================
# Export All Context-Rich Tests (Extended)
# ============================================================================


class TestExportAllContextRichExtended:
    """Extended tests for export_all_context_rich including new exports."""

    def test_export_all_context_rich_creates_all_files(
        self, test_db, cleanup_extended_test_data
    ):
        """Test export_all_context_rich creates all nine context-rich files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = export_all_context_rich(tmpdir)

            # Verify all exports are included (9 total)
            assert "products" in results
            assert "inventory" in results
            assert "purchases" in results
            assert "ingredients" in results
            assert "materials" in results
            assert "recipes" in results
            assert "material_products" in results
            assert "finished_units" in results
            assert "finished_goods" in results

            # Verify files exist
            assert (Path(tmpdir) / "aug_products.json").exists()
            assert (Path(tmpdir) / "aug_inventory.json").exists()
            assert (Path(tmpdir) / "aug_purchases.json").exists()
            assert (Path(tmpdir) / "aug_ingredients.json").exists()
            assert (Path(tmpdir) / "aug_materials.json").exists()
            assert (Path(tmpdir) / "aug_recipes.json").exists()
            assert (Path(tmpdir) / "aug_material_products.json").exists()
            assert (Path(tmpdir) / "aug_finished_units.json").exists()
            assert (Path(tmpdir) / "aug_finished_goods.json").exists()


# ============================================================================
# New Field Definition Tests
# ============================================================================


class TestNewFieldDefinitions:
    """Tests for new editable/readonly field constant definitions."""

    def test_ingredients_editable_fields(self):
        """Verify ingredients editable fields match spec requirements."""
        required_editable = [
            "description",
            "notes",
            "density_volume_value",
            "density_volume_unit",
        ]
        for field in required_editable:
            assert field in INGREDIENTS_CONTEXT_RICH_EDITABLE

    def test_ingredients_readonly_includes_computed(self):
        """Verify ingredients readonly includes computed fields."""
        computed_fields = [
            "category_hierarchy",
            "product_count",
            "inventory_total",
            "average_cost",
        ]
        for field in computed_fields:
            assert field in INGREDIENTS_CONTEXT_RICH_READONLY

    def test_materials_editable_fields(self):
        """Verify materials editable fields match spec requirements."""
        required_editable = ["description", "notes"]
        for field in required_editable:
            assert field in MATERIALS_CONTEXT_RICH_EDITABLE

    def test_materials_readonly_includes_hierarchy(self):
        """Verify materials readonly includes hierarchy and computed fields."""
        context_fields = [
            "category_hierarchy",
            "product_count",
            "total_inventory",
            "total_inventory_value",
        ]
        for field in context_fields:
            assert field in MATERIALS_CONTEXT_RICH_READONLY

    def test_recipes_editable_fields(self):
        """Verify recipes editable fields match spec requirements."""
        required_editable = ["notes", "source", "estimated_time_minutes"]
        for field in required_editable:
            assert field in RECIPES_CONTEXT_RICH_EDITABLE

    def test_recipes_readonly_includes_computed(self):
        """Verify recipes readonly includes computed and nested fields."""
        context_fields = [
            "ingredients",
            "recipe_components",
            "total_cost",
            "cost_per_unit",
        ]
        for field in context_fields:
            assert field in RECIPES_CONTEXT_RICH_READONLY
