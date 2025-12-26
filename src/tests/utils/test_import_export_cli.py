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
    export_complete_cmd,
    export_view_cmd,
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

            assert data["view_type"] == "products"
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

            assert data["view_type"] == "inventory"
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

            assert data["view_type"] == "purchases"
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
