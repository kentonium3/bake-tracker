"""
Tests for the Coordinated Export Service.

Tests cover:
- Export manifest generation with checksums
- Entity export with FK resolution fields
- Dependency ordering
- ZIP archive creation
- Export validation
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
from src.models.recipe import Recipe, RecipeComponent, RecipeIngredient
from src.models.supplier import Supplier
from src.services.coordinated_export_service import (
    DEPENDENCY_ORDER,
    ExportManifest,
    FileEntry,
    export_complete,
    validate_export,
    _calculate_checksum,
)
from src.services.database import session_scope


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
        session.query(RecipeIngredient).delete(synchronize_session=False)
        session.query(RecipeComponent).delete(synchronize_session=False)
        session.query(Recipe).delete(synchronize_session=False)
        session.query(Product).delete(synchronize_session=False)
        session.query(Ingredient).delete(synchronize_session=False)
        session.query(Supplier).delete(synchronize_session=False)


@pytest.fixture
def sample_supplier(test_db):
    """Create a sample supplier for tests."""
    with session_scope() as session:
        supplier = Supplier(
            name="Test Supplier",
            city="Boston",
            state="MA",
            zip_code="02101",
            notes="Test supplier notes",
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
            display_name="Test Flour",
            category="Flour",
            description="Test flour description",
        )
        session.add(ingredient)
        session.flush()
        ingredient_id = ingredient.id
    return ingredient_id


@pytest.fixture
def sample_product(test_db, sample_ingredient):
    """Create a sample product for tests."""
    with session_scope() as session:
        product = Product(
            ingredient_id=sample_ingredient,
            brand="Test Brand",
            product_name="Premium Flour",
            package_unit="lb",
            package_unit_quantity=5.0,
            package_size="5 lb bag",
        )
        session.add(product)
        session.flush()
        product_id = product.id
    return product_id


@pytest.fixture
def sample_recipe(test_db, sample_ingredient):
    """Create a sample recipe for tests."""
    with session_scope() as session:
        recipe = Recipe(
            name="Test Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        session.add(recipe)
        session.flush()

        # Add recipe ingredient
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=sample_ingredient,
            quantity=2.0,
            unit="cup",
        )
        session.add(ri)
        recipe_id = recipe.id
    return recipe_id


@pytest.fixture
def sample_purchase(test_db, sample_product, sample_supplier):
    """Create a sample purchase for tests."""
    with session_scope() as session:
        purchase = Purchase(
            product_id=sample_product,
            supplier_id=sample_supplier,
            purchase_date=date(2025, 12, 1),
            unit_price=Decimal("12.99"),
            quantity_purchased=2,
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
            quantity=5.0,
            unit_cost=12.99,
            purchase_date=date(2025, 12, 1),
            location="Main Storage",
        )
        session.add(item)
        session.flush()
        item_id = item.id
    return item_id


# ============================================================================
# DataClass Tests
# ============================================================================


class TestFileEntry:
    """Tests for the FileEntry dataclass."""

    def test_file_entry_creation(self):
        """Test FileEntry can be created with all fields."""
        entry = FileEntry(
            filename="suppliers.json",
            entity_type="suppliers",
            record_count=5,
            sha256="abc123",
            dependencies=[],
            import_order=1,
        )
        assert entry.filename == "suppliers.json"
        assert entry.entity_type == "suppliers"
        assert entry.record_count == 5
        assert entry.sha256 == "abc123"
        assert entry.dependencies == []
        assert entry.import_order == 1


class TestExportManifest:
    """Tests for the ExportManifest dataclass."""

    def test_manifest_creation_with_defaults(self):
        """Test ExportManifest default values."""
        manifest = ExportManifest()
        assert manifest.version == "1.0"
        assert manifest.export_date == ""
        assert manifest.source == ""
        assert manifest.files == []

    def test_manifest_to_dict(self):
        """Test manifest to_dict conversion."""
        manifest = ExportManifest(
            version="1.0",
            export_date="2025-12-25T10:00:00Z",
            source="Test App v1.0",
            files=[
                FileEntry(
                    filename="suppliers.json",
                    entity_type="suppliers",
                    record_count=2,
                    sha256="abc123",
                    dependencies=[],
                    import_order=1,
                )
            ],
        )
        result = manifest.to_dict()

        assert result["version"] == "1.0"
        assert result["export_date"] == "2025-12-25T10:00:00Z"
        assert result["source"] == "Test App v1.0"
        assert len(result["files"]) == 1
        assert result["files"][0]["filename"] == "suppliers.json"


# ============================================================================
# Checksum Tests
# ============================================================================


class TestChecksum:
    """Tests for checksum calculation."""

    def test_calculate_checksum(self):
        """Test SHA256 checksum calculation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"test": "data"}')
            temp_path = Path(f.name)

        try:
            checksum = _calculate_checksum(temp_path)
            # SHA256 hash is 64 hex characters
            assert len(checksum) == 64
            assert all(c in "0123456789abcdef" for c in checksum)
        finally:
            os.unlink(temp_path)

    def test_checksum_consistent(self):
        """Test that same content produces same checksum."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"test": "consistent"}')
            temp_path = Path(f.name)

        try:
            checksum1 = _calculate_checksum(temp_path)
            checksum2 = _calculate_checksum(temp_path)
            assert checksum1 == checksum2
        finally:
            os.unlink(temp_path)


# ============================================================================
# Dependency Order Tests
# ============================================================================


class TestDependencyOrder:
    """Tests for dependency ordering constants."""

    def test_dependency_order_defined(self):
        """Verify all entity types have dependency order."""
        expected_entities = [
            "suppliers",
            "ingredients",
            "products",
            "recipes",
            "purchases",
            "inventory_items",
        ]
        for entity in expected_entities:
            assert entity in DEPENDENCY_ORDER

    def test_suppliers_no_dependencies(self):
        """Verify suppliers have no dependencies."""
        order, deps = DEPENDENCY_ORDER["suppliers"]
        assert deps == []
        assert order == 1

    def test_ingredients_no_dependencies(self):
        """Verify ingredients have no dependencies."""
        order, deps = DEPENDENCY_ORDER["ingredients"]
        assert deps == []
        assert order == 2

    def test_products_depend_on_ingredients(self):
        """Verify products depend on ingredients."""
        order, deps = DEPENDENCY_ORDER["products"]
        assert "ingredients" in deps
        assert order == 3

    def test_purchases_depend_on_products_and_suppliers(self):
        """Verify purchases depend on products and suppliers."""
        order, deps = DEPENDENCY_ORDER["purchases"]
        assert "products" in deps
        assert "suppliers" in deps
        assert order == 5

    def test_inventory_items_depend_on_products(self):
        """Verify inventory items depend on products."""
        order, deps = DEPENDENCY_ORDER["inventory_items"]
        assert "products" in deps
        assert order == 6


# ============================================================================
# Export Function Tests
# ============================================================================


class TestExportComplete:
    """Tests for export_complete function."""

    def test_export_empty_database(self, test_db, cleanup_test_data):
        """Test export of empty database creates files with 0 records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            # Verify manifest created
            assert manifest.version == "1.0"
            assert manifest.export_date != ""
            assert "Seasonal Baking Tracker" in manifest.source

            # Verify all entity files created (6 original + 6 material entities)
            assert len(manifest.files) == 12

            # Verify files sorted by import_order
            orders = [f.import_order for f in manifest.files]
            assert orders == sorted(orders)

            # Verify record counts are 0
            for file_entry in manifest.files:
                assert file_entry.record_count == 0

            # Verify manifest.json exists
            manifest_path = Path(tmpdir) / "manifest.json"
            assert manifest_path.exists()

    def test_export_with_supplier(self, test_db, sample_supplier, cleanup_test_data):
        """Test export includes supplier data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            # Find suppliers file entry
            suppliers_entry = next(
                (f for f in manifest.files if f.entity_type == "suppliers"), None
            )
            assert suppliers_entry is not None
            assert suppliers_entry.record_count == 1

            # Verify file content
            suppliers_path = Path(tmpdir) / "suppliers.json"
            with open(suppliers_path) as f:
                data = json.load(f)

            assert data["entity_type"] == "suppliers"
            assert len(data["records"]) == 1
            assert data["records"][0]["name"] == "Test Supplier"
            assert data["records"][0]["city"] == "Boston"

    def test_export_with_product_includes_fk_fields(
        self, test_db, sample_product, cleanup_test_data
    ):
        """Test product export includes ingredient FK resolution fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            products_path = Path(tmpdir) / "products.json"
            with open(products_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            product = data["records"][0]

            # Verify both ID and slug present for FK
            assert "ingredient_id" in product
            assert "ingredient_slug" in product
            assert product["ingredient_slug"] == "test_flour"
            assert product["brand"] == "Test Brand"

    def test_export_with_recipe_includes_ingredients(
        self, test_db, sample_recipe, cleanup_test_data
    ):
        """Test recipe export includes nested ingredients with FK fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            recipes_path = Path(tmpdir) / "recipes.json"
            with open(recipes_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            recipe = data["records"][0]

            assert recipe["name"] == "Test Cookies"
            assert "ingredients" in recipe
            assert len(recipe["ingredients"]) == 1

            # Verify FK resolution fields in nested ingredients
            ing = recipe["ingredients"][0]
            assert "ingredient_id" in ing
            assert "ingredient_slug" in ing
            assert ing["ingredient_slug"] == "test_flour"

    def test_export_with_purchase_includes_fk_fields(
        self, test_db, sample_purchase, cleanup_test_data
    ):
        """Test purchase export includes product and supplier FK resolution fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            purchases_path = Path(tmpdir) / "purchases.json"
            with open(purchases_path) as f:
                data = json.load(f)

            assert len(data["records"]) == 1
            purchase = data["records"][0]

            # Verify product FK fields
            assert "product_id" in purchase
            assert "product_slug" in purchase

            # Verify supplier FK fields
            assert "supplier_id" in purchase
            assert "supplier_name" in purchase

    def test_export_checksums_match(self, test_db, sample_supplier, cleanup_test_data):
        """Test export checksums match actual file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            for file_entry in manifest.files:
                file_path = Path(tmpdir) / file_entry.filename
                actual_checksum = _calculate_checksum(file_path)
                assert file_entry.sha256 == actual_checksum

    def test_export_manifest_json_written(self, test_db, cleanup_test_data):
        """Test manifest.json is written with correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir)

            manifest_path = Path(tmpdir) / "manifest.json"
            assert manifest_path.exists()

            with open(manifest_path) as f:
                data = json.load(f)

            assert "version" in data
            assert "export_date" in data
            assert "source" in data
            assert "files" in data

    def test_export_with_zip(self, test_db, sample_supplier, cleanup_test_data):
        """Test export creates ZIP archive when requested."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export_dir"
            manifest = export_complete(str(output_path), create_zip=True)

            # Verify ZIP file created
            zip_path = output_path.with_suffix(".zip")
            assert zip_path.exists()

            # Verify manifest returned
            assert manifest.version == "1.0"

    def test_export_uses_session_parameter(
        self, test_db, sample_ingredient, cleanup_test_data
    ):
        """Test export works with passed session parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with session_scope() as session:
                manifest = export_complete(tmpdir, session=session)

                # Verify export completed (6 original + 6 material entities)
                assert len(manifest.files) == 12

                # Verify ingredients exported
                ing_entry = next(
                    (f for f in manifest.files if f.entity_type == "ingredients"), None
                )
                assert ing_entry.record_count == 1


# ============================================================================
# Export Validation Tests
# ============================================================================


class TestValidateExport:
    """Tests for validate_export function."""

    def test_validate_export_valid(self, test_db, sample_supplier, cleanup_test_data):
        """Test validation passes for valid export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir)
            result = validate_export(tmpdir)

            assert result["valid"] is True
            assert result["files_checked"] == 12  # 6 original + 6 material entities
            assert result["errors"] == []

    def test_validate_export_missing_manifest(self, test_db):
        """Test validation fails when manifest.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_export(tmpdir)

            assert result["valid"] is False
            assert "manifest.json not found" in result["errors"][0]

    def test_validate_export_checksum_mismatch(
        self, test_db, sample_supplier, cleanup_test_data
    ):
        """Test validation detects checksum mismatch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir)

            # Corrupt a file
            suppliers_path = Path(tmpdir) / "suppliers.json"
            with open(suppliers_path, "a") as f:
                f.write("corrupted data")

            result = validate_export(tmpdir)

            assert result["valid"] is False
            assert any("Checksum mismatch" in e for e in result["errors"])

    def test_validate_export_missing_file(
        self, test_db, sample_supplier, cleanup_test_data
    ):
        """Test validation detects missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir)

            # Delete a file
            (Path(tmpdir) / "suppliers.json").unlink()

            result = validate_export(tmpdir)

            assert result["valid"] is False
            assert any("File not found" in e for e in result["errors"])

    def test_validate_export_from_zip(
        self, test_db, sample_supplier, cleanup_test_data
    ):
        """Test validation works with ZIP file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export_dir"
            export_complete(str(output_path), create_zip=True)

            zip_path = output_path.with_suffix(".zip")
            result = validate_export(str(zip_path))

            assert result["valid"] is True
            assert result["files_checked"] == 12  # 6 original + 6 material entities


# ============================================================================
# Full Round-Trip Tests
# ============================================================================


class TestExportRoundTrip:
    """Integration tests for export functionality."""

    def test_full_data_export(
        self,
        test_db,
        sample_supplier,
        sample_ingredient,
        sample_product,
        sample_recipe,
        sample_purchase,
        sample_inventory_item,
        cleanup_test_data,
    ):
        """Test export with all entity types populated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            # Verify all entity types have records
            entities = {f.entity_type: f.record_count for f in manifest.files}

            assert entities["suppliers"] == 1
            assert entities["ingredients"] == 1
            assert entities["products"] == 1
            assert entities["recipes"] == 1
            assert entities["purchases"] == 1
            assert entities["inventory_items"] == 1

            # Verify validation passes
            result = validate_export(tmpdir)
            assert result["valid"] is True

    def test_export_import_order_correct(self, test_db, cleanup_test_data):
        """Test manifest files are ordered by import_order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            # Check order - original entities followed by material entities
            entity_order = [f.entity_type for f in manifest.files]
            expected_order = [
                "suppliers",
                "ingredients",
                "products",
                "recipes",
                "purchases",
                "inventory_items",
                # Feature 047: Material entities
                "material_categories",
                "material_subcategories",
                "materials",
                "material_products",
                "material_units",
                "material_purchases",
            ]
            assert entity_order == expected_order
