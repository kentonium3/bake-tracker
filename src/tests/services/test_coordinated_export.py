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

from src.models.event import Event, EventProductionTarget, EventAssemblyTarget
from src.models.finished_good import FinishedGood
from src.models.finished_unit import FinishedUnit
from src.models.ingredient import Ingredient
from src.models.inventory_depletion import InventoryDepletion
from src.models.inventory_item import InventoryItem
from src.models.product import Product
from src.models.production_run import ProductionRun
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
        # Feature 049: New entities first
        session.query(InventoryDepletion).delete(synchronize_session=False)
        session.query(ProductionRun).delete(synchronize_session=False)
        session.query(EventProductionTarget).delete(synchronize_session=False)
        session.query(EventAssemblyTarget).delete(synchronize_session=False)
        session.query(Event).delete(synchronize_session=False)
        session.query(FinishedGood).delete(synchronize_session=False)
        session.query(FinishedUnit).delete(synchronize_session=False)
        # Original entities
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
    """Create a sample recipe for tests.

    F056: yield_quantity, yield_unit removed from Recipe model.
    """
    with session_scope() as session:
        recipe = Recipe(
            name="Test Cookies",
            category="Cookies",
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


# Feature 049: New entity fixtures
@pytest.fixture
def sample_finished_good(test_db):
    """Create a sample finished good for tests."""
    with session_scope() as session:
        fg = FinishedGood(
            slug="test_cookies_box",
            display_name="Test Cookies Box",
            description="A box of test cookies",
            packaging_instructions="Pack 12 cookies per box",
            notes="Test finished good notes",
        )
        session.add(fg)
        session.flush()
        fg_id = fg.id
    return fg_id


@pytest.fixture
def sample_finished_unit(test_db, sample_recipe):
    """Create a sample finished unit for tests."""
    with session_scope() as session:
        fu = FinishedUnit(
            slug="test_cookie",
            display_name="Test Cookie",
            description="A single test cookie",
            recipe_id=sample_recipe,
            items_per_batch=24,
            item_unit="cookie",
            notes="Test finished unit notes",
        )
        session.add(fu)
        session.flush()
        fu_id = fu.id
    return fu_id


@pytest.fixture
def sample_event(test_db, sample_recipe, sample_finished_good):
    """Create a sample event with production and assembly targets."""
    with session_scope() as session:
        event = Event(
            name="Test Holiday Event",
            event_date=date(2025, 12, 25),
            year=2025,
            notes="Test event notes",
        )
        session.add(event)
        session.flush()

        # Add production target
        prod_target = EventProductionTarget(
            event_id=event.id,
            recipe_id=sample_recipe,
            target_batches=5,
            notes="Production target notes",
        )
        session.add(prod_target)

        # Add assembly target
        assembly_target = EventAssemblyTarget(
            event_id=event.id,
            finished_good_id=sample_finished_good,
            target_quantity=10,
            notes="Assembly target notes",
        )
        session.add(assembly_target)

        event_id = event.id
    return event_id


@pytest.fixture
def sample_production_run(test_db, sample_recipe, sample_event, sample_finished_unit):
    """Create a sample production run for tests."""
    from datetime import datetime

    with session_scope() as session:
        run = ProductionRun(
            recipe_id=sample_recipe,
            finished_unit_id=sample_finished_unit,
            event_id=sample_event,
            num_batches=2,
            expected_yield=48,
            actual_yield=46,
            produced_at=datetime(2025, 12, 20, 10, 0, 0),
            notes="Test production run notes",
        )
        session.add(run)
        session.flush()
        run_id = run.id
    return run_id


@pytest.fixture
def sample_inventory_depletion(test_db, sample_inventory_item):
    """Create a sample inventory depletion for tests."""
    from datetime import datetime
    from decimal import Decimal

    with session_scope() as session:
        depletion = InventoryDepletion(
            inventory_item_id=sample_inventory_item,
            quantity_depleted=Decimal("2.0"),
            depletion_reason="production",
            depletion_date=datetime(2025, 12, 20),
            notes="Used in test batch",
            cost=Decimal("25.98"),  # 2 units * 12.99 cost per unit
        )
        session.add(depletion)
        session.flush()
        depletion_id = depletion.id
    return depletion_id


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

    # Feature 056: FinishedUnits dependency test
    def test_finished_units_depend_on_recipes(self):
        """Verify finished_units depend on recipes."""
        order, deps = DEPENDENCY_ORDER["finished_units"]
        assert "recipes" in deps
        assert order == 5

    def test_purchases_depend_on_products_and_suppliers(self):
        """Verify purchases depend on products and suppliers."""
        order, deps = DEPENDENCY_ORDER["purchases"]
        assert "products" in deps
        assert "suppliers" in deps
        assert order == 6

    def test_inventory_items_depend_on_products(self):
        """Verify inventory items depend on products."""
        order, deps = DEPENDENCY_ORDER["inventory_items"]
        assert "products" in deps
        assert order == 7

    # Feature 049: New entity dependency tests
    def test_finished_goods_no_dependencies(self):
        """Verify finished_goods have no dependencies."""
        order, deps = DEPENDENCY_ORDER["finished_goods"]
        assert deps == []
        assert order == 15  # F058: Shifted by material_inventory_items

    def test_events_no_dependencies(self):
        """Verify events have no dependencies."""
        order, deps = DEPENDENCY_ORDER["events"]
        assert deps == []
        assert order == 16  # F058: Shifted by material_inventory_items

    def test_production_runs_depend_on_recipes_events_and_finished_units(self):
        """Verify production_runs depend on recipes, events, and finished_units."""
        order, deps = DEPENDENCY_ORDER["production_runs"]
        assert "recipes" in deps
        assert "events" in deps
        assert "finished_units" in deps
        assert order == 17  # F058: Shifted by material_inventory_items

    def test_inventory_depletions_depend_on_inventory_items(self):
        """Verify inventory_depletions depend on inventory_items."""
        order, deps = DEPENDENCY_ORDER["inventory_depletions"]
        assert "inventory_items" in deps
        assert order == 18  # F058: Shifted by material_inventory_items


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

            # Verify all entity files created
            assert len(manifest.files) == len(DEPENDENCY_ORDER)

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

            # Verify slug present for FK resolution (IDs not exported for portability)
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

            # Verify FK resolution fields in nested ingredients (slug only, no IDs for portability)
            ing = recipe["ingredients"][0]
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

            # Verify FK resolution fields (slug only, no IDs for portability)
            assert "product_slug" in purchase
            assert "supplier_slug" in purchase

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

    def test_export_uses_session_parameter(self, test_db, sample_ingredient, cleanup_test_data):
        """Test export works with passed session parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with session_scope() as session:
                manifest = export_complete(tmpdir, session=session)

                # Verify export completed with all entity files
                assert len(manifest.files) == len(DEPENDENCY_ORDER)

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
            assert result["files_checked"] == len(DEPENDENCY_ORDER)
            assert result["errors"] == []

    def test_validate_export_missing_manifest(self, test_db):
        """Test validation fails when manifest.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_export(tmpdir)

            assert result["valid"] is False
            assert "manifest.json not found" in result["errors"][0]

    def test_validate_export_checksum_mismatch(self, test_db, sample_supplier, cleanup_test_data):
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

    def test_validate_export_missing_file(self, test_db, sample_supplier, cleanup_test_data):
        """Test validation detects missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir)

            # Delete a file
            (Path(tmpdir) / "suppliers.json").unlink()

            result = validate_export(tmpdir)

            assert result["valid"] is False
            assert any("File not found" in e for e in result["errors"])

    def test_validate_export_from_zip(self, test_db, sample_supplier, cleanup_test_data):
        """Test validation works with ZIP file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export_dir"
            export_complete(str(output_path), create_zip=True)

            zip_path = output_path.with_suffix(".zip")
            result = validate_export(str(zip_path))

            assert result["valid"] is True
            assert result["files_checked"] == len(DEPENDENCY_ORDER)


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

            # Check order matches coordinated export dependency order
            entity_order = [f.entity_type for f in manifest.files]
            expected_order = [
                entity_type
                for entity_type, (order, _deps) in sorted(
                    DEPENDENCY_ORDER.items(), key=lambda item: item[1][0]
                )
            ]
            assert entity_order == expected_order


# ============================================================================
# Feature 049: New Entity Export Tests
# ============================================================================


class TestExportFinishedGoods:
    """Tests for finished_goods export functionality."""

    def test_export_finished_goods_empty(self, test_db, cleanup_test_data):
        """Test finished_goods export with no records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            fg_entry = next((f for f in manifest.files if f.entity_type == "finished_goods"), None)
            assert fg_entry is not None
            assert fg_entry.record_count == 0
            assert fg_entry.import_order == 15  # F058: Shifted by material_inventory_items

    def test_export_finished_goods_with_data(
        self, test_db, sample_finished_good, cleanup_test_data
    ):
        """Test finished_goods export includes correct fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            fg_entry = next((f for f in manifest.files if f.entity_type == "finished_goods"), None)
            assert fg_entry.record_count == 1

            # Verify file content
            fg_path = Path(tmpdir) / "finished_goods.json"
            with open(fg_path) as f:
                data = json.load(f)

            assert data["entity_type"] == "finished_goods"
            assert len(data["records"]) == 1

            fg = data["records"][0]
            assert fg["slug"] == "test_cookies_box"
            assert fg["display_name"] == "Test Cookies Box"
            assert fg["description"] == "A box of test cookies"
            assert fg["packaging_instructions"] == "Pack 12 cookies per box"


# ============================================================================
# Feature 056: FinishedUnits Export Tests
# ============================================================================


class TestExportFinishedUnits:
    """Tests for finished_units export functionality (Feature 056)."""

    def test_export_finished_units_empty(self, test_db, cleanup_test_data):
        """Test finished_units export with no records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            fu_entry = next((f for f in manifest.files if f.entity_type == "finished_units"), None)
            assert fu_entry is not None
            assert fu_entry.record_count == 0
            assert fu_entry.import_order == 5  # After recipes

    def test_export_finished_units_with_data(
        self, test_db, sample_finished_unit, cleanup_test_data
    ):
        """Test finished_units export includes correct fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            fu_entry = next((f for f in manifest.files if f.entity_type == "finished_units"), None)
            assert fu_entry.record_count == 1

            # Verify file content
            fu_path = Path(tmpdir) / "finished_units.json"
            with open(fu_path) as f:
                data = json.load(f)

            assert data["entity_type"] == "finished_units"
            assert len(data["records"]) == 1

            fu = data["records"][0]
            assert fu["slug"] == "test_cookie"
            assert fu["display_name"] == "Test Cookie"
            assert fu["items_per_batch"] == 24
            assert fu["item_unit"] == "cookie"

    def test_export_finished_units_contains_required_fields(
        self, test_db, sample_finished_unit, cleanup_test_data
    ):
        """Verify all required fields are exported for FinishedUnit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            fu_path = Path(tmpdir) / "finished_units.json"
            with open(fu_path) as f:
                data = json.load(f)

            record = data["records"][0]

            # Verify required fields per spec
            required_fields = [
                "uuid",
                "slug",
                "display_name",
                "recipe_name",
                "category",
                "yield_mode",
                "items_per_batch",
                "item_unit",
                "batch_percentage",
                "portion_description",
                "inventory_count",
                "description",
                "notes",
            ]
            for field in required_fields:
                assert field in record, f"Missing required field: {field}"

    def test_export_finished_units_uses_recipe_name(
        self, test_db, sample_finished_unit, cleanup_test_data
    ):
        """Verify export uses recipe.name for recipe_name field (not recipe_id)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            fu_path = Path(tmpdir) / "finished_units.json"
            with open(fu_path) as f:
                data = json.load(f)

            record = data["records"][0]

            # Should use recipe name, not recipe_id
            assert "recipe_name" in record
            assert record["recipe_name"] == "Test Cookies"
            assert "recipe_id" not in record  # Should NOT have raw ID

    def test_export_finished_units_handles_null_fields(
        self, test_db, sample_recipe, cleanup_test_data
    ):
        """Test export handles null optional fields gracefully."""
        # Create a minimal finished unit with many null fields
        with session_scope() as session:
            fu = FinishedUnit(
                slug="minimal_fu",
                display_name="Minimal FU",
                recipe_id=sample_recipe,
                # Leave optional fields as None
            )
            session.add(fu)

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            fu_path = Path(tmpdir) / "finished_units.json"
            with open(fu_path) as f:
                data = json.load(f)

            # Find the minimal_fu record
            minimal = next((r for r in data["records"] if r["slug"] == "minimal_fu"), None)
            assert minimal is not None

            # Null fields should be exported as null
            assert minimal["batch_percentage"] is None
            assert minimal["portion_description"] is None


class TestExportEvents:
    """Tests for events export functionality."""

    def test_export_events_empty(self, test_db, cleanup_test_data):
        """Test events export with no records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            event_entry = next((f for f in manifest.files if f.entity_type == "events"), None)
            assert event_entry is not None
            assert event_entry.record_count == 0
            assert event_entry.import_order == 16  # F058: Shifted by material_inventory_items

    def test_export_events_with_data(
        self,
        test_db,
        sample_event,
        sample_recipe,
        sample_finished_good,
        cleanup_test_data,
    ):
        """Test events export includes targets with FK resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            event_entry = next((f for f in manifest.files if f.entity_type == "events"), None)
            assert event_entry.record_count == 1

            # Verify file content
            events_path = Path(tmpdir) / "events.json"
            with open(events_path) as f:
                data = json.load(f)

            assert data["entity_type"] == "events"
            assert len(data["records"]) == 1

            event = data["records"][0]
            assert event["name"] == "Test Holiday Event"
            assert event["year"] == 2025

            # Verify production targets with FK fields (slug/name only, no IDs for portability)
            assert "production_targets" in event
            assert len(event["production_targets"]) == 1
            pt = event["production_targets"][0]
            assert "recipe_name" in pt
            assert pt["recipe_name"] == "Test Cookies"

            # Verify assembly targets with FK fields (slug only, no IDs for portability)
            assert "assembly_targets" in event
            assert len(event["assembly_targets"]) == 1
            at = event["assembly_targets"][0]
            assert "finished_good_slug" in at
            assert at["finished_good_slug"] == "test_cookies_box"


class TestExportProductionRuns:
    """Tests for production_runs export functionality."""

    def test_export_production_runs_empty(self, test_db, cleanup_test_data):
        """Test production_runs export with no records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            pr_entry = next((f for f in manifest.files if f.entity_type == "production_runs"), None)
            assert pr_entry is not None
            assert pr_entry.record_count == 0
            assert pr_entry.import_order == 17  # F058: Shifted by material_inventory_items

    def test_export_production_runs_with_data(
        self, test_db, sample_production_run, cleanup_test_data
    ):
        """Test production_runs export includes FK resolution fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            pr_entry = next((f for f in manifest.files if f.entity_type == "production_runs"), None)
            assert pr_entry.record_count == 1

            # Verify file content
            pr_path = Path(tmpdir) / "production_runs.json"
            with open(pr_path) as f:
                data = json.load(f)

            assert data["entity_type"] == "production_runs"
            assert len(data["records"]) == 1

            run = data["records"][0]
            assert run["num_batches"] == 2
            assert run["expected_yield"] == 48
            assert run["actual_yield"] == 46

            # Verify FK resolution fields (slug/name only, no IDs for portability)
            assert "recipe_name" in run
            assert run["recipe_name"] == "Test Cookies"

            assert "event_name" in run
            assert run["event_name"] == "Test Holiday Event"


class TestExportInventoryDepletions:
    """Tests for inventory_depletions export functionality."""

    def test_export_inventory_depletions_empty(self, test_db, cleanup_test_data):
        """Test inventory_depletions export with no records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            dep_entry = next(
                (f for f in manifest.files if f.entity_type == "inventory_depletions"),
                None,
            )
            assert dep_entry is not None
            assert dep_entry.record_count == 0
            assert dep_entry.import_order == 18  # F058: Shifted by material_inventory_items

    def test_export_inventory_depletions_with_data(
        self, test_db, sample_inventory_depletion, cleanup_test_data
    ):
        """Test inventory_depletions export includes FK resolution fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            dep_entry = next(
                (f for f in manifest.files if f.entity_type == "inventory_depletions"),
                None,
            )
            assert dep_entry.record_count == 1

            # Verify file content
            dep_path = Path(tmpdir) / "inventory_depletions.json"
            with open(dep_path) as f:
                data = json.load(f)

            assert data["entity_type"] == "inventory_depletions"
            assert len(data["records"]) == 1

            depletion = data["records"][0]
            # Decimals may include additional precision, check numeric value
            assert float(depletion["quantity_depleted"]) == 2.0
            assert depletion["depletion_reason"] == "production"
            assert depletion["notes"] == "Used in test batch"

            # Verify FK resolution field present (ref only, no ID for portability)
            assert "inventory_item_ref" in depletion


class TestNewEntitiesEmptyArrays:
    """Tests verifying empty entities export as empty arrays (T008)."""

    def test_all_entities_export_with_empty_database(self, test_db, cleanup_test_data):
        """Verify all entity types export as empty arrays when DB is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir)

            # Verify all files exist
            assert len(manifest.files) == len(DEPENDENCY_ORDER)

            # Verify each file has records: []
            for file_entry in manifest.files:
                file_path = Path(tmpdir) / file_entry.filename
                assert file_path.exists(), f"File {file_entry.filename} does not exist"

                with open(file_path) as f:
                    data = json.load(f)

                assert "records" in data, f"File {file_entry.filename} missing 'records' key"
                assert (
                    data["records"] == []
                ), f"File {file_entry.filename} should have empty records array"
                assert (
                    file_entry.record_count == 0
                ), f"Manifest entry {file_entry.entity_type} should have 0 records"
