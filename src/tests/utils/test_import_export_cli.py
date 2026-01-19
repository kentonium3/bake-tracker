"""
Tests for the Import/Export CLI (F030 commands).

Tests cover:
- export-complete command
- export-view command
- validate-export command
- Exit codes
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
from src.utils.import_export_cli import (
    CLIFKResolver,
    export_complete_cmd,
    export_view_cmd,
    import_view_cmd,
    main,
    validate_export_cmd,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cleanup_test_data(test_db):
    """Cleanup test data after each test."""
    yield
    with session_scope() as session:
        session.query(InventoryItem).delete(synchronize_session=False)
        session.query(Purchase).delete(synchronize_session=False)
        session.query(Product).delete(synchronize_session=False)
        session.query(Ingredient).delete(synchronize_session=False)
        session.query(Supplier).delete(synchronize_session=False)


@pytest.fixture
def sample_data(test_db):
    """Create sample data for CLI tests."""
    with session_scope() as session:
        # Supplier
        supplier = Supplier(
            name="Test Supplier",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(supplier)
        session.flush()

        # Ingredient
        ingredient = Ingredient(
            slug="test_flour",
            display_name="Test Flour",
            category="Flour",
        )
        session.add(ingredient)
        session.flush()

        # Product
        product = Product(
            ingredient_id=ingredient.id,
            brand="Test Brand",
            package_unit="lb",
            package_unit_quantity=5.0,
            preferred_supplier_id=supplier.id,
        )
        session.add(product)
        session.flush()

        # Purchase
        purchase = Purchase(
            product_id=product.id,
            supplier_id=supplier.id,
            purchase_date=date(2025, 12, 15),
            unit_price=Decimal("10.99"),
            quantity_purchased=2,
        )
        session.add(purchase)
        session.flush()

        # Inventory
        item = InventoryItem(
            product_id=product.id,
            purchase_id=purchase.id,
            quantity=5.0,
            unit_cost=10.99,
            purchase_date=date(2025, 12, 15),
            location="Main Storage",
        )
        session.add(item)

    return {
        "supplier_id": supplier.id,
        "ingredient_id": ingredient.id,
        "product_id": product.id,
        "purchase_id": purchase.id,
        "inventory_item_id": item.id,
    }


# ============================================================================
# export-complete Command Tests
# ============================================================================


class TestExportCompleteCmd:
    """Tests for export_complete_cmd function."""

    def test_export_complete_creates_directory(self, test_db, cleanup_test_data):
        """Test export-complete creates output directory with manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "export_test"

            result = export_complete_cmd(str(output_dir))

            assert result == 0
            assert output_dir.exists()
            assert (output_dir / "manifest.json").exists()

    def test_export_complete_creates_entity_files(self, test_db, sample_data, cleanup_test_data):
        """Test export-complete creates all entity files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "export_test"

            result = export_complete_cmd(str(output_dir))

            assert result == 0
            assert (output_dir / "suppliers.json").exists()
            assert (output_dir / "ingredients.json").exists()
            assert (output_dir / "products.json").exists()
            assert (output_dir / "recipes.json").exists()
            assert (output_dir / "purchases.json").exists()
            assert (output_dir / "inventory_items.json").exists()

    def test_export_complete_with_zip(self, test_db, cleanup_test_data):
        """Test export-complete with --zip creates ZIP archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "export_test"

            result = export_complete_cmd(str(output_dir), create_zip=True)

            assert result == 0
            zip_path = output_dir.with_suffix(".zip")
            assert zip_path.exists()

    def test_export_complete_default_directory(self, test_db, cleanup_test_data):
        """Test export-complete uses timestamped default directory."""
        import os

        # Save current directory
        original_cwd = os.getcwd()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                result = export_complete_cmd(None)

                assert result == 0
                # Should have created an export_YYYYMMDD_HHMMSS directory
                dirs = [d for d in Path(tmpdir).iterdir() if d.name.startswith("export_")]
                assert len(dirs) == 1
        finally:
            os.chdir(original_cwd)


# ============================================================================
# export-view Command Tests
# ============================================================================


class TestExportViewCmd:
    """Tests for export_view_cmd function."""

    def test_export_view_products(self, test_db, sample_data, cleanup_test_data):
        """Test export-view with products type."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_view_cmd("products", temp_path)

            assert result == 0
            assert Path(temp_path).exists()

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "products"
            assert "_meta" in data
            assert len(data["records"]) == 1

        finally:
            os.unlink(temp_path)

    def test_export_view_inventory(self, test_db, sample_data, cleanup_test_data):
        """Test export-view with inventory type."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_view_cmd("inventory", temp_path)

            assert result == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "inventory"
            assert len(data["records"]) == 1

        finally:
            os.unlink(temp_path)

    def test_export_view_purchases(self, test_db, sample_data, cleanup_test_data):
        """Test export-view with purchases type."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_view_cmd("purchases", temp_path)

            assert result == 0

            with open(temp_path) as f:
                data = json.load(f)

            assert data["export_type"] == "purchases"
            assert len(data["records"]) == 1

        finally:
            os.unlink(temp_path)

    def test_export_view_default_output(self, test_db, cleanup_test_data):
        """Test export-view uses default output filename."""
        import os

        original_cwd = os.getcwd()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                result = export_view_cmd("products", None)

                assert result == 0
                assert Path("view_products.json").exists()

        finally:
            os.chdir(original_cwd)

    def test_export_view_invalid_type(self, test_db, cleanup_test_data):
        """Test export-view returns error for invalid type."""
        result = export_view_cmd("invalid_type", "/tmp/test.json")
        assert result == 1


# ============================================================================
# validate-export Command Tests
# ============================================================================


class TestValidateExportCmd:
    """Tests for validate_export_cmd function."""

    def test_validate_valid_export(self, test_db, cleanup_test_data):
        """Test validate-export returns 0 for valid export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an export first
            export_complete_cmd(tmpdir)

            # Validate it
            result = validate_export_cmd(tmpdir)

            assert result == 0

    def test_validate_missing_manifest(self, test_db):
        """Test validate-export returns 1 for missing manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_export_cmd(tmpdir)
            assert result == 1

    def test_validate_corrupted_file(self, test_db, cleanup_test_data):
        """Test validate-export returns 1 for corrupted file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an export
            export_complete_cmd(tmpdir)

            # Corrupt a file
            suppliers_path = Path(tmpdir) / "suppliers.json"
            with open(suppliers_path, "a") as f:
                f.write("corrupted data")

            # Validate it
            result = validate_export_cmd(tmpdir)

            assert result == 1


# ============================================================================
# CLI Integration Tests
# ============================================================================


class TestMainCLI:
    """Integration tests for main CLI function."""

    def test_main_no_command_shows_help(self, test_db):
        """Test main with no command returns 1."""
        import sys
        from unittest import mock

        with mock.patch.object(sys, "argv", ["import_export_cli"]):
            result = main()
            assert result == 1

    def test_main_export_complete(self, test_db, cleanup_test_data):
        """Test main with export-complete command."""
        import sys
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = str(Path(tmpdir) / "export_test")
            with mock.patch.object(
                sys, "argv", ["import_export_cli", "export-complete", "-o", output_dir]
            ):
                result = main()

                assert result == 0
                assert (Path(output_dir) / "manifest.json").exists()

    def test_main_export_view(self, test_db, cleanup_test_data):
        """Test main with export-view command."""
        import sys
        from unittest import mock

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            with mock.patch.object(
                sys, "argv", ["import_export_cli", "export-view", "-t", "products", "-o", temp_path]
            ):
                result = main()

                assert result == 0
                assert Path(temp_path).exists()

        finally:
            os.unlink(temp_path)

    def test_main_validate_export(self, test_db, cleanup_test_data):
        """Test main with validate-export command."""
        import sys
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an export first
            export_complete_cmd(tmpdir)

            # Validate via main
            with mock.patch.object(
                sys, "argv", ["import_export_cli", "validate-export", tmpdir]
            ):
                result = main()

                assert result == 0


# ============================================================================
# import-view Command Tests
# ============================================================================


class TestImportViewCmd:
    """Tests for import_view_cmd function."""

    def test_import_view_valid_file_merge_mode(self, test_db, sample_data, cleanup_test_data):
        """Test import-view with valid file in merge mode (default)."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            # Create a simple view file with existing ingredient
            view_data = {
                "export_type": "products",
                "export_date": "2025-12-25T12:00:00Z",
                "_meta": {
                    "editable_fields": ["product_name"],
                },
                "records": [
                    {
                        "ingredient_slug": "test_flour",
                        "brand": "New Brand",
                        "package_unit": "oz",
                        "package_unit_quantity": 16.0,
                        "product_name": "New Product",
                    }
                ],
            }
            json.dump(view_data, f)
            temp_path = f.name

        try:
            result = import_view_cmd(temp_path, mode="merge")

            assert result == 0

            # Verify the product was created
            with session_scope() as session:
                products = session.query(Product).filter(Product.brand == "New Brand").all()
                assert len(products) == 1
                assert products[0].product_name == "New Product"

        finally:
            os.unlink(temp_path)

    def test_import_view_skip_existing_mode(self, test_db, sample_data, cleanup_test_data):
        """Test import-view with skip_existing mode doesn't update existing."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            # Create view with duplicate of existing product
            view_data = {
                "export_type": "products",
                "export_date": "2025-12-25T12:00:00Z",
                "_meta": {
                    "editable_fields": ["product_name"],
                },
                "records": [
                    {
                        # This matches the existing product
                        "ingredient_slug": "test_flour",
                        "brand": "Test Brand",
                        "package_unit": "lb",
                        "package_unit_quantity": 5.0,
                        "product_name": "Updated Name",
                    }
                ],
            }
            json.dump(view_data, f)
            temp_path = f.name

        try:
            result = import_view_cmd(temp_path, mode="skip_existing")

            assert result == 0

            # Verify the product was NOT updated (skip_existing)
            with session_scope() as session:
                products = session.query(Product).filter(Product.brand == "Test Brand").all()
                assert len(products) == 1
                # Original product should have no product_name
                assert products[0].product_name is None

        finally:
            os.unlink(temp_path)

    def test_import_view_dry_run_no_changes(self, test_db, sample_data, cleanup_test_data):
        """Test import-view with dry-run makes no database changes."""
        # Count products before
        with session_scope() as session:
            product_count_before = session.query(Product).count()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            view_data = {
                "export_type": "products",
                "export_date": "2025-12-25T12:00:00Z",
                "_meta": {
                    "editable_fields": ["product_name"],
                },
                "records": [
                    {
                        "ingredient_slug": "test_flour",
                        "brand": "DryRun Brand",
                        "package_unit": "oz",
                        "package_unit_quantity": 8.0,
                    }
                ],
            }
            json.dump(view_data, f)
            temp_path = f.name

        try:
            result = import_view_cmd(temp_path, dry_run=True)

            # Should return 0 (success)
            assert result == 0

            # Verify no new product was created
            with session_scope() as session:
                product_count_after = session.query(Product).count()
                assert product_count_after == product_count_before

                # Double-check no "DryRun Brand" product exists
                products = session.query(Product).filter(Product.brand == "DryRun Brand").all()
                assert len(products) == 0

        finally:
            os.unlink(temp_path)

    def test_import_view_skip_on_error_logs_failures(self, test_db, cleanup_test_data):
        """Test import-view with skip-on-error logs skipped records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create view file with missing FK
            view_path = Path(tmpdir) / "view.json"
            view_data = {
                "export_type": "products",
                "export_date": "2025-12-25T12:00:00Z",
                "_meta": {
                    "editable_fields": [],
                },
                "records": [
                    {
                        "ingredient_slug": "nonexistent_ingredient",
                        "brand": "Test Brand",
                        "package_unit": "lb",
                        "package_unit_quantity": 5.0,
                    }
                ],
            }
            with open(view_path, "w") as f:
                json.dump(view_data, f)

            result = import_view_cmd(str(view_path), skip_on_error=True)

            # Should return 0 (no actual failures since they were skipped)
            assert result == 0

            # Verify a skipped records log was created
            log_files = list(Path(tmpdir).glob("import_skipped_*.json"))
            assert len(log_files) == 1

            # Verify log contents
            with open(log_files[0]) as f:
                log_data = json.load(f)
            assert len(log_data["skipped_records"]) > 0

    def test_import_view_missing_fk_without_interactive_fails(self, test_db, cleanup_test_data):
        """Test import-view fails on missing FK without --interactive (fail-fast default)."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            view_data = {
                "export_type": "products",
                "export_date": "2025-12-25T12:00:00Z",
                "_meta": {
                    "editable_fields": [],
                },
                "records": [
                    {
                        "ingredient_slug": "nonexistent_ingredient",
                        "brand": "Test Brand",
                        "package_unit": "lb",
                        "package_unit_quantity": 5.0,
                    }
                ],
            }
            json.dump(view_data, f)
            temp_path = f.name

        try:
            # No --interactive and no --skip-on-error should fail
            result = import_view_cmd(temp_path)

            # Should return 1 (failure)
            assert result == 1

        finally:
            os.unlink(temp_path)

    def test_import_view_file_not_found(self, test_db, cleanup_test_data):
        """Test import-view returns error for missing file."""
        result = import_view_cmd("/nonexistent/path/file.json")
        assert result == 1

    def test_import_view_invalid_json(self, test_db, cleanup_test_data):
        """Test import-view returns error for invalid JSON."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("this is not valid json {{{")
            temp_path = f.name

        try:
            result = import_view_cmd(temp_path)
            assert result == 1

        finally:
            os.unlink(temp_path)


# ============================================================================
# CLIFKResolver Tests
# ============================================================================


class TestCLIFKResolver:
    """Tests for CLIFKResolver class."""

    def test_resolve_skip_choice(self, test_db):
        """Test CLIFKResolver handles SKIP choice."""
        from unittest import mock
        from src.services.fk_resolver_service import MissingFK, ResolutionChoice

        resolver = CLIFKResolver()

        missing = MissingFK(
            entity_type="supplier",
            missing_value="Unknown Supplier",
            field_name="supplier_name",
            affected_record_count=3,
            sample_records=[],
        )

        # Mock input to return "S"
        with mock.patch("builtins.input", return_value="S"):
            resolution = resolver.resolve(missing)

        assert resolution.choice == ResolutionChoice.SKIP
        assert resolution.entity_type == "supplier"
        assert resolution.missing_value == "Unknown Supplier"

    def test_resolve_create_supplier(self, test_db):
        """Test CLIFKResolver handles CREATE for supplier."""
        from unittest import mock
        from src.services.fk_resolver_service import MissingFK, ResolutionChoice

        resolver = CLIFKResolver()

        missing = MissingFK(
            entity_type="supplier",
            missing_value="New Supplier",
            field_name="supplier_name",
            affected_record_count=2,
            sample_records=[],
        )

        # Mock input sequence: C -> enter (default name) -> Boston -> MA -> 02101 -> (empty street)
        inputs = iter(["C", "", "Boston", "MA", "02101", ""])
        with mock.patch("builtins.input", lambda _: next(inputs)):
            resolution = resolver.resolve(missing)

        assert resolution.choice == ResolutionChoice.CREATE
        assert resolution.entity_type == "supplier"
        assert resolution.created_entity["name"] == "New Supplier"
        assert resolution.created_entity["city"] == "Boston"
        assert resolution.created_entity["state"] == "MA"
        assert resolution.created_entity["zip_code"] == "02101"

    def test_resolve_create_ingredient(self, test_db):
        """Test CLIFKResolver handles CREATE for ingredient."""
        from unittest import mock
        from src.services.fk_resolver_service import MissingFK, ResolutionChoice

        resolver = CLIFKResolver()

        missing = MissingFK(
            entity_type="ingredient",
            missing_value="new_sugar",
            field_name="ingredient_slug",
            affected_record_count=1,
            sample_records=[],
        )

        # Mock input sequence: C -> enter (default slug) -> Sugar -> Sweeteners -> (empty desc)
        inputs = iter(["C", "", "Sugar", "Sweeteners", ""])
        with mock.patch("builtins.input", lambda _: next(inputs)):
            resolution = resolver.resolve(missing)

        assert resolution.choice == ResolutionChoice.CREATE
        assert resolution.entity_type == "ingredient"
        assert resolution.created_entity["slug"] == "new_sugar"
        assert resolution.created_entity["display_name"] == "Sugar"
        assert resolution.created_entity["category"] == "Sweeteners"

    def test_resolve_invalid_input_retries(self, test_db):
        """Test CLIFKResolver retries on invalid input."""
        from unittest import mock
        from src.services.fk_resolver_service import MissingFK, ResolutionChoice

        resolver = CLIFKResolver()

        missing = MissingFK(
            entity_type="supplier",
            missing_value="Test",
            field_name="supplier_name",
            affected_record_count=1,
            sample_records=[],
        )

        # Mock input sequence: X (invalid) -> Y (invalid) -> S (valid)
        inputs = iter(["X", "Y", "S"])
        with mock.patch("builtins.input", lambda _: next(inputs)):
            resolution = resolver.resolve(missing)

        assert resolution.choice == ResolutionChoice.SKIP


# ============================================================================
# import-view CLI Integration Tests
# ============================================================================


class TestImportViewCLIIntegration:
    """Integration tests for import-view via main()."""

    def test_main_import_view(self, test_db, sample_data, cleanup_test_data):
        """Test main with import-view command."""
        import sys
        from unittest import mock

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            view_data = {
                "export_type": "products",
                "export_date": "2025-12-25T12:00:00Z",
                "_meta": {
                    "editable_fields": [],
                },
                "records": [
                    {
                        "ingredient_slug": "test_flour",
                        "brand": "CLI Test Brand",
                        "package_unit": "oz",
                        "package_unit_quantity": 12.0,
                    }
                ],
            }
            json.dump(view_data, f)
            temp_path = f.name

        try:
            with mock.patch.object(
                sys, "argv", ["import_export_cli", "import-view", temp_path]
            ):
                result = main()

            assert result == 0

        finally:
            os.unlink(temp_path)

    def test_main_import_view_with_dry_run(self, test_db, sample_data, cleanup_test_data):
        """Test main with import-view --dry-run command."""
        import sys
        from unittest import mock

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            view_data = {
                "export_type": "products",
                "export_date": "2025-12-25T12:00:00Z",
                "_meta": {
                    "editable_fields": [],
                },
                "records": [
                    {
                        "ingredient_slug": "test_flour",
                        "brand": "DryRun CLI Brand",
                        "package_unit": "oz",
                        "package_unit_quantity": 12.0,
                    }
                ],
            }
            json.dump(view_data, f)
            temp_path = f.name

        try:
            with mock.patch.object(
                sys, "argv", ["import_export_cli", "import-view", temp_path, "--dry-run"]
            ):
                result = main()

            assert result == 0

            # Verify no product created
            with session_scope() as session:
                products = session.query(Product).filter(Product.brand == "DryRun CLI Brand").all()
                assert len(products) == 0

        finally:
            os.unlink(temp_path)

    def test_main_import_view_with_mode(self, test_db, sample_data, cleanup_test_data):
        """Test main with import-view --mode skip_existing command."""
        import sys
        from unittest import mock

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            view_data = {
                "export_type": "products",
                "export_date": "2025-12-25T12:00:00Z",
                "_meta": {
                    "editable_fields": [],
                },
                "records": [
                    {
                        "ingredient_slug": "test_flour",
                        "brand": "Mode Test Brand",
                        "package_unit": "oz",
                        "package_unit_quantity": 8.0,
                    }
                ],
            }
            json.dump(view_data, f)
            temp_path = f.name

        try:
            with mock.patch.object(
                sys, "argv", ["import_export_cli", "import-view", temp_path, "-m", "skip_existing"]
            ):
                result = main()

            assert result == 0

        finally:
            os.unlink(temp_path)


# ============================================================================
# F059 Material Purchase CLI Tests
# ============================================================================


class TestMaterialPurchaseCLI:
    """Tests for the purchase-material CLI command (F059)."""

    @pytest.fixture
    def material_test_data(self, test_db):
        """Create material test data for purchase-material tests."""
        from src.models.material import Material
        from src.models.material_category import MaterialCategory
        from src.models.material_subcategory import MaterialSubcategory
        from src.models.material_product import MaterialProduct
        from src.models.supplier import Supplier

        with session_scope() as session:
            # Supplier
            supplier = Supplier(
                name="CLI Test Supplier",
                slug="cli-test-supplier",
                city="Boston",
                state="MA",
                zip_code="02101",
                is_active=True,
            )
            session.add(supplier)
            session.flush()

            # Category
            category = MaterialCategory(
                name="Test Category",
                slug="test_category",
            )
            session.add(category)
            session.flush()

            # Subcategory
            subcategory = MaterialSubcategory(
                category_id=category.id,
                name="Test Subcategory",
                slug="test_subcategory",
            )
            session.add(subcategory)
            session.flush()

            # Material
            material = Material(
                subcategory_id=subcategory.id,
                name="Test Material",
                slug="test_material",
                base_unit_type="each",
            )
            session.add(material)
            session.flush()

            # Product
            product = MaterialProduct(
                material_id=material.id,
                name="Test Product",
                slug="test-product",
                package_quantity=10.0,
                package_unit="each",
                quantity_in_base_units=10.0,
            )
            session.add(product)
            session.flush()

            return {
                "supplier_id": supplier.id,
                "category_id": category.id,
                "subcategory_id": subcategory.id,
                "material_id": material.id,
                "product_id": product.id,
            }

    def test_purchase_material_help(self, test_db, capsys):
        """Test that --help shows correct options."""
        import sys
        from unittest import mock

        with mock.patch.object(sys, "argv", ["import_export_cli", "purchase-material", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        # argparse exits with 0 for --help
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "--product" in captured.out
        assert "--name" in captured.out
        assert "--qty" in captured.out
        assert "--cost" in captured.out

    def test_purchase_existing_product_by_slug(self, test_db, material_test_data, capsys):
        """Test purchasing an existing product by slug."""
        import sys
        from unittest import mock

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--product", "test-product",
                "--qty", "2",
                "--cost", "25.00",
            ],
        ):
            result = main()

        captured = capsys.readouterr()
        # Should succeed
        assert result == 0
        assert "PURCHASE RECORDED" in captured.out

    def test_purchase_missing_product_fails(self, test_db, material_test_data, capsys):
        """Test that purchasing a non-existent product fails gracefully."""
        import sys
        from unittest import mock

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--product", "non-existent-product",
                "--qty", "1",
                "--cost", "10.00",
            ],
        ):
            result = main()

        captured = capsys.readouterr()
        assert result == 1
        assert "ERROR" in captured.out
        assert "not found" in captured.out.lower()

    def test_purchase_no_product_or_name_fails(self, test_db, capsys):
        """Test that --product or --name is required."""
        import sys
        from unittest import mock

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--qty", "1",
                "--cost", "10.00",
            ],
        ):
            result = main()

        captured = capsys.readouterr()
        assert result == 1
        assert "ERROR" in captured.out
        assert "--product or --name" in captured.out.lower()

    def test_purchase_both_product_and_name_fails(self, test_db, material_test_data, capsys):
        """Test that --product and --name are mutually exclusive."""
        import sys
        from unittest import mock

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--product", "test-product",
                "--name", "New Product",
                "--qty", "1",
                "--cost", "10.00",
            ],
        ):
            result = main()

        captured = capsys.readouterr()
        assert result == 1
        assert "ERROR" in captured.out
        assert "cannot specify both" in captured.out.lower()

    def test_create_provisional_product(self, test_db, material_test_data, capsys):
        """Test creating a provisional product and recording purchase."""
        import sys
        from unittest import mock

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--name", "New Test Product",
                "--material-id", str(material_test_data["material_id"]),
                "--package-size", "50",
                "--package-unit", "each",
                "--qty", "1",
                "--cost", "15.00",
            ],
        ):
            result = main()

        captured = capsys.readouterr()
        assert result == 0
        assert "PROVISIONAL PRODUCT CREATED" in captured.out
        assert "PURCHASE RECORDED" in captured.out

    def test_create_provisional_missing_material_id_fails(self, test_db, capsys):
        """Test that --material-id is required for new products."""
        import sys
        from unittest import mock

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--name", "New Product",
                "--package-size", "10",
                "--package-unit", "each",
                "--qty", "1",
                "--cost", "10.00",
            ],
        ):
            result = main()

        captured = capsys.readouterr()
        assert result == 1
        assert "ERROR" in captured.out
        assert "material" in captured.out.lower()

    def test_purchase_with_date(self, test_db, material_test_data, capsys):
        """Test purchase with custom date."""
        import sys
        from unittest import mock

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--product", "test-product",
                "--qty", "1",
                "--cost", "10.00",
                "--date", "2026-01-15",
            ],
        ):
            result = main()

        captured = capsys.readouterr()
        assert result == 0
        assert "2026-01-15" in captured.out

    def test_purchase_invalid_date_fails(self, test_db, material_test_data, capsys):
        """Test that invalid date format fails."""
        import sys
        from unittest import mock

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--product", "test-product",
                "--qty", "1",
                "--cost", "10.00",
                "--date", "01/15/2026",  # Wrong format
            ],
        ):
            result = main()

        captured = capsys.readouterr()
        assert result == 1
        assert "Invalid date" in captured.out

    def test_provisional_product_has_is_provisional_flag(self, test_db, material_test_data, capsys):
        """Test that provisional products are created with is_provisional=True."""
        import sys
        from unittest import mock
        from src.models.material_product import MaterialProduct

        with mock.patch.object(
            sys,
            "argv",
            [
                "import_export_cli",
                "purchase-material",
                "--name", "Provisional Flag Test Product",
                "--material-id", str(material_test_data["material_id"]),
                "--package-size", "25",
                "--package-unit", "each",
                "--qty", "1",
                "--cost", "10.00",
            ],
        ):
            result = main()

        assert result == 0

        # Verify the product was created with is_provisional=True
        with session_scope() as session:
            product = session.query(MaterialProduct).filter(
                MaterialProduct.name == "Provisional Flag Test Product"
            ).first()
            assert product is not None
            assert product.is_provisional is True
