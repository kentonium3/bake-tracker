"""
Integration tests for import/export round-trip workflows.

These tests verify complete workflows across multiple services:
- Full backup -> restore -> verify
- Context-rich export -> modify -> import
- Format auto-detection accuracy
- Transaction imports -> verify inventory changes (when WP04/WP05 complete)

WP08 - Integration Testing
"""

import json
import tempfile
import uuid
from pathlib import Path

import pytest

from src.models.ingredient import Ingredient
from src.models.material import Material
from src.models.product import Product
from src.models.recipe import Recipe
from src.models.supplier import Supplier
from src.services.database import session_scope
from src.services.denormalized_export_service import (
    export_ingredients_view,
    export_materials_view,
    export_recipes_view,
)
from src.services.enhanced_import_service import (
    FormatDetectionResult,
    detect_format,
    import_context_rich_view,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_export_dir():
    """Create temporary directory for exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def unique_id():
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]


@pytest.fixture
def sample_ingredient(test_db, unique_id):
    """Create a sample ingredient for testing."""
    with session_scope() as session:
        ingredient = Ingredient(
            slug=f"test_flour_{unique_id}",
            display_name=f"Test Flour {unique_id}",
            category="Flour",
            description="Original description",
            notes="Original notes",
        )
        session.add(ingredient)
        session.commit()
        return {
            "id": ingredient.id,
            "slug": ingredient.slug,
            "display_name": ingredient.display_name,
            "category": ingredient.category,
            "description": ingredient.description,
            "notes": ingredient.notes,
        }


@pytest.fixture
def sample_material(test_db, unique_id):
    """
    Create a sample material for testing.

    Materials require a subcategory, which requires a category.
    This fixture creates the full hierarchy.
    """
    from src.models.material_category import MaterialCategory
    from src.models.material_subcategory import MaterialSubcategory

    with session_scope() as session:
        # Create category first
        category = MaterialCategory(
            name=f"Test Category {unique_id}",
            slug=f"test_category_{unique_id}",
        )
        session.add(category)
        session.flush()

        # Create subcategory
        subcategory = MaterialSubcategory(
            category_id=category.id,
            name=f"Test Subcategory {unique_id}",
            slug=f"test_subcategory_{unique_id}",
        )
        session.add(subcategory)
        session.flush()

        # Create material
        material = Material(
            subcategory_id=subcategory.id,
            name=f"Test Boxes {unique_id}",
            slug=f"test_boxes_{unique_id}",
            base_unit_type="each",
            description="Original material description",
        )
        session.add(material)
        session.commit()
        return {
            "id": material.id,
            "slug": material.slug,
            "name": material.name,
            "description": material.description,
        }


@pytest.fixture
def sample_recipe(test_db, unique_id):
    """Create a sample recipe for testing."""
    with session_scope() as session:
        recipe = Recipe(
            name=f"Test Recipe {unique_id}",
            category="Cookies",
            yield_quantity=24.0,
            yield_unit="cookies",
            notes="Original recipe notes",
        )
        session.add(recipe)
        session.commit()
        return {
            "id": recipe.id,
            "name": recipe.name,
            "notes": recipe.notes,
        }


# ============================================================================
# Format Auto-Detection Tests (T073)
# ============================================================================


class TestFormatAutoDetection:
    """
    Test format auto-detection accuracy.

    SC-009: Format auto-detection correctly identifies format 100% of time.
    """

    def test_detect_context_rich_format(self, temp_export_dir):
        """Test detection of context-rich format."""
        data = {
            "view_type": "ingredients",
            "_meta": {
                "editable_fields": ["description", "notes"],
                "readonly_fields": ["id", "slug", "display_name"],
            },
            "records": [
                {"slug": "test", "description": "Test description"},
            ],
        }
        file_path = temp_export_dir / "context_rich.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = detect_format(str(file_path))

        assert result.format_type == "context_rich"
        assert result.view_type == "ingredients"
        assert "description" in result.editable_fields

    def test_detect_normalized_format(self, temp_export_dir):
        """Test detection of normalized backup format."""
        data = {
            "version": "4.0",
            "application": "bake-tracker",
            "exported_at": "2026-01-12T10:00:00Z",
            "ingredients": [{"slug": "flour"}],
            "products": [],
        }
        file_path = temp_export_dir / "normalized.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = detect_format(str(file_path))

        assert result.format_type == "normalized"
        assert result.version == "4.0"

    def test_detect_purchases_format(self, temp_export_dir):
        """Test detection of purchases import format."""
        data = {
            "schema_version": "4.0",
            "import_type": "purchases",
            "source": "bt_mobile",
            "purchases": [
                {"product_slug": "test", "unit_price": 5.99, "quantity_purchased": 2},
            ],
        }
        file_path = temp_export_dir / "purchases.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = detect_format(str(file_path))

        assert result.format_type == "purchases"
        assert result.entity_count == 1

    def test_detect_adjustments_format(self, temp_export_dir):
        """Test detection of adjustments import format."""
        data = {
            "schema_version": "4.0",
            "import_type": "adjustments",
            "source": "bt_mobile",
            "adjustments": [
                {"product_slug": "test", "quantity": -2.5, "reason_code": "spoilage"},
            ],
        }
        file_path = temp_export_dir / "adjustments.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = detect_format(str(file_path))

        assert result.format_type == "adjustments"

    def test_detect_inventory_updates_alias(self, temp_export_dir):
        """Test detection of inventory_updates (alias for adjustments)."""
        data = {
            "schema_version": "4.0",
            "import_type": "inventory_updates",
            "inventory_updates": [
                {"product_slug": "test", "quantity": -1.0},
            ],
        }
        file_path = temp_export_dir / "inventory_updates.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = detect_format(str(file_path))

        assert result.format_type == "adjustments"

    def test_detect_unknown_format(self, temp_export_dir):
        """Test detection of unknown format."""
        data = {
            "random_field": "value",
            "data": [1, 2, 3],
        }
        file_path = temp_export_dir / "unknown.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = detect_format(str(file_path))

        assert result.format_type == "unknown"

    @pytest.mark.parametrize(
        "file_content,expected_format",
        [
            (
                {"_meta": {"editable_fields": []}, "records": []},
                "context_rich",
            ),
            (
                {"version": "4.0", "application": "bake-tracker"},
                "normalized",
            ),
            (
                {"import_type": "purchases", "purchases": []},
                "purchases",
            ),
            (
                {"import_type": "adjustments", "adjustments": []},
                "adjustments",
            ),
        ],
    )
    def test_format_detection_100_percent_accuracy(
        self, temp_export_dir, file_content, expected_format
    ):
        """
        Parametrized test for 100% format detection accuracy.

        SC-009: Format auto-detection correctly identifies format 100% of time.
        """
        file_path = temp_export_dir / f"test_{expected_format}.json"
        with open(file_path, "w") as f:
            json.dump(file_content, f)

        result = detect_format(str(file_path))

        assert result.format_type == expected_format


# ============================================================================
# Context-Rich Roundtrip Tests (T069)
# ============================================================================


class TestContextRichRoundtrip:
    """
    Test context-rich export -> modify editable -> import workflow.

    Verifies editable fields updated, computed fields ignored.
    """

    def test_ingredients_context_rich_roundtrip(
        self, test_db, sample_ingredient, temp_export_dir, unique_id
    ):
        """
        Test ingredients context-rich export -> modify -> import workflow.

        1. Export ingredients with context-rich format
        2. Modify editable fields (description, notes)
        3. Modify readonly fields (should be ignored)
        4. Import modified file
        5. Verify editable fields updated
        6. Verify readonly fields unchanged
        """
        # 1. Export context-rich ingredients
        export_path = str(temp_export_dir / "ingredients_view.json")
        export_ingredients_view(export_path)

        # 2. Load and verify export structure
        with open(export_path) as f:
            data = json.load(f)

        assert data.get("view_type") == "ingredients"
        assert "_meta" in data
        assert "editable_fields" in data["_meta"]

        # Find our test ingredient in the records
        test_record = None
        for record in data["records"]:
            if record.get("slug") == sample_ingredient["slug"]:
                test_record = record
                break

        assert test_record is not None, "Test ingredient not found in export"

        # 3. Modify editable field
        test_record["description"] = f"AI-augmented description {unique_id}"
        test_record["notes"] = f"AI-added notes {unique_id}"

        # Try to modify readonly fields (should be ignored on import)
        test_record["display_name"] = "Should Not Change"
        if "product_count" in test_record:
            test_record["product_count"] = 99999  # Computed field

        # 4. Save modified data
        with open(export_path, "w") as f:
            json.dump(data, f)

        # 5. Import modified file
        result = import_context_rich_view(export_path)

        assert result.merged >= 1, f"Expected merge, got: {result.get_summary()}"

        # 6. Verify editable fields updated
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter_by(slug=sample_ingredient["slug"])
                .first()
            )
            assert ingredient is not None

            # Editable fields should be updated
            assert ingredient.description == f"AI-augmented description {unique_id}"
            assert ingredient.notes == f"AI-added notes {unique_id}"

            # Readonly fields should be unchanged
            assert ingredient.display_name == sample_ingredient["display_name"]

    def test_materials_context_rich_roundtrip(
        self, test_db, sample_material, temp_export_dir, unique_id
    ):
        """Test materials context-rich export -> modify -> import workflow."""
        # 1. Export context-rich materials
        export_path = str(temp_export_dir / "materials_view.json")
        export_materials_view(export_path)

        # 2. Load and modify
        with open(export_path) as f:
            data = json.load(f)

        assert data.get("view_type") == "materials"

        # Find test material
        test_record = None
        for record in data["records"]:
            if record.get("slug") == sample_material["slug"]:
                test_record = record
                break

        if test_record is None:
            pytest.skip("Test material not in export")

        # Modify editable field
        test_record["description"] = f"AI-augmented material description {unique_id}"

        with open(export_path, "w") as f:
            json.dump(data, f)

        # 3. Import
        result = import_context_rich_view(export_path)

        # 4. Verify
        with session_scope() as session:
            material = (
                session.query(Material).filter_by(slug=sample_material["slug"]).first()
            )
            if material:
                assert (
                    material.description
                    == f"AI-augmented material description {unique_id}"
                )

    @pytest.mark.skip(
        reason="Recipe model doesn't have slug field - context-rich import uses slug for lookup"
    )
    def test_recipes_context_rich_roundtrip(
        self, test_db, sample_recipe, temp_export_dir, unique_id
    ):
        """
        Test recipes context-rich export -> modify -> import workflow.

        Note: This test is skipped because the Recipe model doesn't have a slug field.
        The context-rich import system uses slug-based lookups for entity identification.
        Once Recipe model is updated to include slug, this test can be enabled.
        """
        # 1. Export context-rich recipes
        export_path = str(temp_export_dir / "recipes_view.json")
        export_recipes_view(export_path)

        # 2. Load and modify
        with open(export_path) as f:
            data = json.load(f)

        assert data.get("view_type") == "recipes"

        # Find test recipe by name (recipes don't have slug)
        test_record = None
        for record in data["records"]:
            if record.get("name") == sample_recipe["name"]:
                test_record = record
                break

        if test_record is None:
            pytest.skip("Test recipe not in export")

        # Modify editable field (notes is typically editable for recipes)
        test_record["notes"] = f"AI-added recipe notes {unique_id}"

        with open(export_path, "w") as f:
            json.dump(data, f)

        # 3. Import - would fail because recipes don't have slug
        result = import_context_rich_view(export_path)

        # 4. Verify
        with session_scope() as session:
            recipe = (
                session.query(Recipe).filter_by(name=sample_recipe["name"]).first()
            )
            if recipe:
                assert recipe.notes == f"AI-added recipe notes {unique_id}"

    def test_context_rich_import_ignores_computed_fields(
        self, test_db, sample_ingredient, temp_export_dir, unique_id
    ):
        """
        Test that computed/readonly fields are ignored during context-rich import.

        Even if the import file contains modified computed fields like
        inventory_total or average_cost, they should NOT be written to DB.
        """
        # Create a context-rich file with modified computed fields
        data = {
            "view_type": "ingredients",
            "_meta": {
                "editable_fields": ["description", "notes"],
                "readonly_fields": [
                    "id",
                    "slug",
                    "display_name",
                    "category",
                    "product_count",
                    "inventory_total",
                    "average_cost",
                ],
            },
            "records": [
                {
                    "id": 999999,  # Should be ignored
                    "slug": sample_ingredient["slug"],
                    "display_name": "Should Not Change",  # Readonly
                    "category": "Should Not Change",  # Readonly
                    "description": f"Valid update {unique_id}",  # Editable
                    "notes": f"Valid notes {unique_id}",  # Editable
                    "product_count": 999,  # Computed - should be ignored
                    "inventory_total": 999.99,  # Computed - should be ignored
                    "average_cost": 999.99,  # Computed - should be ignored
                }
            ],
        }

        file_path = temp_export_dir / "context_rich_with_computed.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        # Import
        result = import_context_rich_view(str(file_path))

        assert result.merged == 1

        # Verify only editable fields changed
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter_by(slug=sample_ingredient["slug"])
                .first()
            )

            # Editable fields updated
            assert ingredient.description == f"Valid update {unique_id}"
            assert ingredient.notes == f"Valid notes {unique_id}"

            # Readonly fields unchanged
            assert ingredient.display_name == sample_ingredient["display_name"]
            assert ingredient.category == sample_ingredient["category"]

    def test_context_rich_dry_run_makes_no_changes(
        self, test_db, sample_ingredient, temp_export_dir, unique_id
    ):
        """Test that dry_run mode previews changes without modifying database."""
        data = {
            "view_type": "ingredients",
            "_meta": {
                "editable_fields": ["description"],
                "readonly_fields": ["slug"],
            },
            "records": [
                {
                    "slug": sample_ingredient["slug"],
                    "description": f"Dry run description {unique_id}",
                }
            ],
        }

        file_path = temp_export_dir / "dry_run_test.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        # Import with dry_run=True
        result = import_context_rich_view(str(file_path), dry_run=True)

        assert result.dry_run is True
        assert result.merged >= 1  # Would have merged

        # Verify NO changes made to database
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter_by(slug=sample_ingredient["slug"])
                .first()
            )
            # Description should still be original
            assert ingredient.description == sample_ingredient["description"]
            assert ingredient.description != f"Dry run description {unique_id}"


# ============================================================================
# Full Backup Roundtrip Tests (T068)
# ============================================================================


class TestFullBackupRoundtrip:
    """
    Test complete backup -> restore workflow.

    SC-002: Complete system state can be restored from backup.

    Note: Full roundtrip requires coordinated import which may depend on WP04/WP05.
    These tests verify export and manifest structure.
    """

    def test_full_backup_export_structure(self, test_db, temp_export_dir):
        """Test that full backup exports with correct manifest structure."""
        # Import the coordinated export service
        from src.services.coordinated_export_service import export_complete

        # Export full backup
        manifest = export_complete(str(temp_export_dir))

        # Verify manifest structure
        assert manifest is not None
        assert hasattr(manifest, "files") or hasattr(manifest, "export_date")

        # Check for manifest.json file
        manifest_path = temp_export_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest_data = json.load(f)

            # Should have 16 entity files
            assert "files" in manifest_data
            assert len(manifest_data["files"]) == 16

            # Verify each file entry has required fields
            for file_entry in manifest_data["files"]:
                assert "filename" in file_entry
                assert "entity_type" in file_entry
                assert "record_count" in file_entry
                assert "import_order" in file_entry


# ============================================================================
# Transaction Import Integration Tests (T070, T071)
# ============================================================================


@pytest.fixture
def sample_product_with_inventory(test_db, unique_id):
    """Create a product with inventory for transaction testing.

    Note: Products don't have a slug field. Transaction imports use a
    composite slug format: ingredient_slug:brand:package_unit_quantity:package_unit
    """
    from datetime import date
    from src.models.inventory_item import InventoryItem

    with session_scope() as session:
        # Create ingredient first (products need ingredient)
        ingredient = Ingredient(
            slug=f"test_flour_{unique_id}",
            display_name=f"Test Flour {unique_id}",
            category="Flour",
        )
        session.add(ingredient)
        session.flush()

        # Create product - no slug field, use composite key
        product = Product(
            ingredient_id=ingredient.id,
            brand=f"TestBrand{unique_id}",  # No spaces - simpler for slug
            product_name=f"Test Flour 5lb",
            package_size="5 lb",  # package_size is String, not Float
            package_unit="lb",
            package_unit_quantity=5.0,  # This is the Float for quantity
        )
        session.add(product)
        session.flush()

        # Create inventory item with purchase_date for FIFO
        inventory_item = InventoryItem(
            product_id=product.id,
            quantity=10.0,
            unit_cost=5.99,
            purchase_date=date(2026, 1, 1),  # Required for FIFO ordering
        )
        session.add(inventory_item)
        session.commit()

        # Build composite slug for transaction imports:
        # Format: ingredient_slug:brand:package_unit_quantity:package_unit
        composite_slug = f"{ingredient.slug}:{product.brand}:{product.package_unit_quantity}:{product.package_unit}"

        return {
            "id": product.id,
            "ingredient_id": ingredient.id,
            "composite_slug": composite_slug,
            "initial_inventory": 10.0,
        }


class TestPurchaseImportIntegration:
    """
    Integration tests for purchase import.

    T070: Test purchase import -> verify inventory increased
    """

    def test_purchase_import_increases_inventory(
        self, test_db, sample_product_with_inventory, temp_export_dir, unique_id
    ):
        """Test that purchase import creates inventory records and increases quantity."""
        try:
            from src.services.transaction_import_service import import_purchases
        except ImportError:
            pytest.skip("WP04 not yet complete - transaction_import_service.py")

        from src.models.inventory_item import InventoryItem

        # Use composite slug format for transaction imports
        product_slug = sample_product_with_inventory["composite_slug"]
        product_id = sample_product_with_inventory["id"]
        initial_qty = sample_product_with_inventory["initial_inventory"]

        # Get initial total inventory using product ID
        with session_scope() as session:
            initial_total = sum(
                i.quantity
                for i in session.query(InventoryItem)
                .filter_by(product_id=product_id)
                .all()
            )

        # Create purchase JSON (includes supplier since Purchase.supplier_id is NOT NULL)
        purchase_data = {
            "schema_version": "4.0",
            "import_type": "purchases",
            "source": "integration_test",
            "supplier": "Test Store",  # Default supplier for all purchases
            "purchases": [
                {
                    "product_slug": product_slug,
                    "purchased_at": "2026-01-12T10:00:00Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 5,
                    "notes": f"Integration test purchase {unique_id}",
                }
            ],
        }

        purchase_path = temp_export_dir / "purchases.json"
        with open(purchase_path, "w") as f:
            json.dump(purchase_data, f)

        # Import purchases
        result = import_purchases(str(purchase_path))

        # Should succeed
        assert result.successful >= 1 or result.created >= 1

        # Verify inventory increased using product ID
        with session_scope() as session:
            new_total = sum(
                i.quantity
                for i in session.query(InventoryItem)
                .filter_by(product_id=product_id)
                .all()
            )
            # New inventory should be initial + purchased amount
            assert new_total == initial_total + 5


class TestAdjustmentImportIntegration:
    """
    Integration tests for adjustment import.

    T071: Test adjustment import -> verify inventory decreased
    """

    def test_adjustment_import_decreases_inventory(
        self, test_db, sample_product_with_inventory, temp_export_dir, unique_id
    ):
        """Test that adjustment import decreases inventory correctly."""
        try:
            from src.services.transaction_import_service import import_adjustments
        except ImportError:
            pytest.skip("WP05 not yet complete - transaction_import_service.py")

        from src.models.inventory_item import InventoryItem

        # Use composite slug format for transaction imports
        product_slug = sample_product_with_inventory["composite_slug"]
        product_id = sample_product_with_inventory["id"]

        # Get initial total inventory using product ID
        with session_scope() as session:
            initial_total = sum(
                i.quantity
                for i in session.query(InventoryItem)
                .filter_by(product_id=product_id)
                .all()
            )

        # Create adjustment JSON
        adjustment_data = {
            "schema_version": "4.0",
            "import_type": "adjustments",
            "source": "integration_test",
            "adjustments": [
                {
                    "product_slug": product_slug,
                    "adjusted_at": "2026-01-12T10:00:00Z",
                    "quantity": -3,  # Must be negative
                    "reason_code": "spoilage",
                    "notes": f"Integration test adjustment {unique_id}",
                }
            ],
        }

        adj_path = temp_export_dir / "adjustments.json"
        with open(adj_path, "w") as f:
            json.dump(adjustment_data, f)

        # Import adjustments
        result = import_adjustments(str(adj_path))

        # Should succeed
        assert result.successful >= 1 or result.created >= 1

        # Verify inventory decreased using product ID
        with session_scope() as session:
            new_total = sum(
                i.quantity
                for i in session.query(InventoryItem)
                .filter_by(product_id=product_id)
                .all()
            )
            # New inventory should be initial - adjusted amount
            assert new_total == initial_total - 3


class TestErrorHandlingAndRollback:
    """
    Tests for atomic transactions and rollback on failure.

    T072: Test error handling and rollback
    """

    def test_context_rich_import_handles_not_found(self, test_db, temp_export_dir):
        """Test that records not found in DB are handled gracefully."""
        data = {
            "view_type": "ingredients",
            "_meta": {
                "editable_fields": ["description"],
                "readonly_fields": ["slug"],
            },
            "records": [
                {
                    "slug": "nonexistent_ingredient_xyz",
                    "description": "This ingredient does not exist",
                }
            ],
        }

        file_path = temp_export_dir / "not_found_test.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = import_context_rich_view(str(file_path))

        # Should report not found, not crash
        assert result.not_found == 1
        assert result.merged == 0

    def test_context_rich_import_handles_mixed_records(
        self, test_db, sample_ingredient, temp_export_dir, unique_id
    ):
        """Test that valid records are processed even when some fail."""
        data = {
            "view_type": "ingredients",
            "_meta": {
                "editable_fields": ["description"],
                "readonly_fields": ["slug"],
            },
            "records": [
                # Valid record
                {
                    "slug": sample_ingredient["slug"],
                    "description": f"Valid update {unique_id}",
                },
                # Invalid - doesn't exist
                {
                    "slug": "nonexistent_ingredient",
                    "description": "Should be skipped",
                },
            ],
        }

        file_path = temp_export_dir / "mixed_records.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = import_context_rich_view(str(file_path))

        # Valid record should be merged
        assert result.merged == 1
        # Invalid record should be tracked as not found
        assert result.not_found == 1

        # Verify valid record was updated
        with session_scope() as session:
            ingredient = (
                session.query(Ingredient)
                .filter_by(slug=sample_ingredient["slug"])
                .first()
            )
            assert ingredient.description == f"Valid update {unique_id}"
