"""Tests for Material Import/Export (Feature 047 - WP08).

Tests for:
- Exporting material catalog to JSON
- Importing material catalog from JSON
- Round-trip data integrity
- FK resolution via slugs
- Error handling for missing references
"""

import json
import pytest
import tempfile
from pathlib import Path
from src.models.supplier import Supplier
from src.models.material_category import MaterialCategory
from src.models.material_subcategory import MaterialSubcategory
from src.models.material import Material
from src.models.material_product import MaterialProduct
from src.models.material_unit import MaterialUnit
from src.services.catalog_import_service import (
    import_material_categories,
    import_material_subcategories,
    import_materials,
    import_material_products,
    import_material_units,
    CatalogImportResult,
    MATERIAL_PRODUCT_DEPRECATED_FIELDS,
)
from src.services.coordinated_export_service import export_complete


@pytest.fixture
def db_session(test_db):
    """Provide a database session for tests."""
    return test_db()


@pytest.fixture
def sample_supplier(db_session):
    """Create a sample supplier for testing."""
    supplier = Supplier(
        name="Test Craft Store",
        city="Boston",
        state="MA",
        zip_code="02101",
    )
    db_session.add(supplier)
    db_session.flush()
    return supplier


@pytest.fixture
def full_material_catalog(db_session, sample_supplier):
    """Create a complete material catalog for export testing."""
    # Category
    cat = MaterialCategory(
        name="Ribbons",
        slug="ribbons",
        description="Decorative ribbons",
        sort_order=1,
    )
    db_session.add(cat)
    db_session.flush()

    # Subcategory
    subcat = MaterialSubcategory(
        category_id=cat.id,
        name="Satin",
        slug="satin",
        description="Satin ribbons",
        sort_order=1,
    )
    db_session.add(subcat)
    db_session.flush()

    # Material
    mat = Material(
        subcategory_id=subcat.id,
        name="Red Satin",
        slug="red-satin",
        base_unit_type="linear_cm",  # Valid values: 'each', 'linear_cm', 'square_cm'
        description="Red satin ribbon",
    )
    db_session.add(mat)
    db_session.flush()

    # Product
    # Feature 058: Removed current_inventory, weighted_avg_cost fields
    # Inventory and costing now tracked via MaterialInventoryItem (FIFO)
    prod = MaterialProduct(
        material_id=mat.id,
        name="30m Roll Red Satin",
        brand="Michaels",
        package_quantity=3000,  # 30m = 3000 cm
        package_unit="cm",
        quantity_in_base_units=3000,  # Same as package_quantity for cm
        supplier_id=sample_supplier.id,
    )
    db_session.add(prod)
    db_session.flush()

    # Unit
    unit = MaterialUnit(
        material_id=mat.id,
        name="6-inch ribbon",
        slug="6-inch-ribbon",
        quantity_per_unit=6,
        description="Standard 6-inch ribbon segment",
    )
    db_session.add(unit)
    db_session.commit()

    return {
        "category": cat,
        "subcategory": subcat,
        "material": mat,
        "product": prod,
        "unit": unit,
        "supplier": sample_supplier,
    }


# =============================================================================
# Export Tests
# =============================================================================


class TestMaterialExport:
    """Tests for material export functionality."""

    def test_export_includes_material_categories(self, db_session, full_material_catalog):
        """Export includes material_categories.json file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir, session=db_session)

            # Check manifest includes material_categories
            filenames = [f.filename for f in manifest.files]
            assert "material_categories.json" in filenames

            # Check file content
            with open(Path(tmpdir) / "material_categories.json") as f:
                data = json.load(f)

            assert len(data["records"]) >= 1
            assert any(r["slug"] == "ribbons" for r in data["records"])

    def test_export_includes_all_material_entities(self, db_session, full_material_catalog):
        """Export includes all material entity types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_complete(tmpdir, session=db_session)

            filenames = [f.filename for f in manifest.files]
            assert "material_categories.json" in filenames
            assert "material_subcategories.json" in filenames
            assert "materials.json" in filenames
            assert "material_products.json" in filenames
            assert "material_units.json" in filenames

    def test_export_includes_fk_resolution_fields(self, db_session, full_material_catalog):
        """Export includes slug fields for FK resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir, session=db_session)

            # Check subcategory has category_slug
            with open(Path(tmpdir) / "material_subcategories.json") as f:
                data = json.load(f)
            record = data["records"][0]
            assert "category_slug" in record
            assert record["category_slug"] == "ribbons"

            # Check material has subcategory_slug
            with open(Path(tmpdir) / "materials.json") as f:
                data = json.load(f)
            record = data["records"][0]
            assert "subcategory_slug" in record
            assert record["subcategory_slug"] == "satin"


# =============================================================================
# Import Tests
# =============================================================================


class TestMaterialCategoryImport:
    """Tests for material category import."""

    def test_import_new_category(self, db_session):
        """Import creates new category."""
        data = [{"name": "Boxes", "slug": "boxes", "description": "Gift boxes"}]

        result = import_material_categories(data, session=db_session)

        assert result.entity_counts["material_categories"].added == 1
        assert result.entity_counts["material_categories"].failed == 0

        # Verify in database
        cat = db_session.query(MaterialCategory).filter_by(slug="boxes").first()
        assert cat is not None
        assert cat.name == "Boxes"

    def test_import_skips_existing(self, db_session, full_material_catalog):
        """Import skips existing category in ADD mode."""
        data = [{"name": "Ribbons", "slug": "ribbons"}]

        result = import_material_categories(data, mode="add", session=db_session)

        assert result.entity_counts["material_categories"].skipped == 1
        assert result.entity_counts["material_categories"].added == 0

    def test_import_validates_required_fields(self, db_session):
        """Import fails for missing required fields."""
        data = [{"slug": "no-name"}]  # Missing name

        result = import_material_categories(data, session=db_session)

        assert result.entity_counts["material_categories"].failed == 1
        assert any("name" in e.message.lower() for e in result.errors)


class TestMaterialImportFKResolution:
    """Tests for FK resolution during import."""

    def test_subcategory_resolves_category_slug(self, db_session, full_material_catalog):
        """Subcategory import resolves category_slug to category_id."""
        data = [
            {
                "name": "Grosgrain",
                "slug": "grosgrain",
                "category_slug": "ribbons",  # FK resolution field
            }
        ]

        result = import_material_subcategories(data, session=db_session)

        assert result.entity_counts["material_subcategories"].added == 1

        subcat = db_session.query(MaterialSubcategory).filter_by(slug="grosgrain").first()
        assert subcat.category_id == full_material_catalog["category"].id

    def test_subcategory_fails_invalid_category(self, db_session):
        """Subcategory import fails when category not found."""
        data = [
            {
                "name": "Orphan",
                "slug": "orphan",
                "category_slug": "nonexistent",
            }
        ]

        result = import_material_subcategories(data, session=db_session)

        assert result.entity_counts["material_subcategories"].failed == 1
        assert any("nonexistent" in e.message for e in result.errors)

    def test_product_resolves_material_and_supplier(self, db_session, full_material_catalog):
        """Product import resolves material_slug and supplier_name."""
        data = [
            {
                "name": "200ft Roll",
                "material_slug": "red-satin",
                "supplier_name": "Test Craft Store",
                "package_quantity": 2400,
                "package_unit": "cm",
            }
        ]

        result = import_material_products(data, session=db_session)

        assert result.entity_counts["material_products"].added == 1

        prod = db_session.query(MaterialProduct).filter_by(name="200ft Roll").first()
        assert prod.material_id == full_material_catalog["material"].id
        assert prod.supplier_id == full_material_catalog["supplier"].id


# =============================================================================
# Round-Trip Tests
# =============================================================================


class TestImportExportRoundtrip:
    """Tests for import/export round-trip integrity."""

    def test_roundtrip_preserves_categories(self, db_session, full_material_catalog):
        """Export and re-import preserves category data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Export
            export_complete(tmpdir, session=db_session)

            # Read exported data
            with open(Path(tmpdir) / "material_categories.json") as f:
                export_data = json.load(f)

            original_count = len(export_data["records"])
            assert original_count >= 1

            # Clear and re-import
            db_session.query(MaterialUnit).delete()
            db_session.query(MaterialProduct).delete()
            db_session.query(Material).delete()
            db_session.query(MaterialSubcategory).delete()
            db_session.query(MaterialCategory).delete()
            db_session.commit()

            result = import_material_categories(export_data["records"], session=db_session)

            assert result.entity_counts["material_categories"].added == original_count

    def test_roundtrip_preserves_hierarchy(self, db_session, full_material_catalog):
        """Export and re-import preserves full hierarchy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Export
            export_complete(tmpdir, session=db_session)

            # Read all exported data
            with open(Path(tmpdir) / "material_categories.json") as f:
                cat_data = json.load(f)
            with open(Path(tmpdir) / "material_subcategories.json") as f:
                subcat_data = json.load(f)
            with open(Path(tmpdir) / "materials.json") as f:
                mat_data = json.load(f)
            with open(Path(tmpdir) / "material_units.json") as f:
                unit_data = json.load(f)

            # Clear database
            db_session.query(MaterialUnit).delete()
            db_session.query(MaterialProduct).delete()
            db_session.query(Material).delete()
            db_session.query(MaterialSubcategory).delete()
            db_session.query(MaterialCategory).delete()
            db_session.commit()

            # Re-import in dependency order
            import_material_categories(cat_data["records"], session=db_session)
            import_material_subcategories(subcat_data["records"], session=db_session)
            import_materials(mat_data["records"], session=db_session)
            import_material_units(unit_data["records"], session=db_session)

            # Verify relationships
            mat = db_session.query(Material).filter_by(slug="red-satin").first()
            assert mat is not None
            assert mat.subcategory.slug == "satin"
            assert mat.subcategory.category.slug == "ribbons"

            unit = db_session.query(MaterialUnit).filter_by(slug="6-inch-ribbon").first()
            assert unit is not None
            assert unit.material.slug == "red-satin"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestImportErrorHandling:
    """Tests for import error handling."""

    def test_invalid_base_unit_type_rejected(self, db_session, full_material_catalog):
        """Material with invalid base_unit_type is rejected."""
        data = [
            {
                "name": "Bad Material",
                "subcategory_slug": "satin",
                "base_unit_type": "invalid_type",
            }
        ]

        result = import_materials(data, session=db_session)

        assert result.entity_counts["materials"].failed == 1
        assert any("base_unit_type" in e.message for e in result.errors)

    def test_missing_package_fields_rejected(self, db_session, full_material_catalog):
        """Product without package fields is rejected."""
        data = [
            {
                "name": "Bad Product",
                "material_slug": "red-satin",
                # Missing package_quantity and package_unit
            }
        ]

        result = import_material_products(data, session=db_session)

        assert result.entity_counts["material_products"].failed == 1

    def test_invalid_quantity_per_unit_rejected(self, db_session, full_material_catalog):
        """Unit with invalid quantity_per_unit is rejected."""
        data = [
            {
                "name": "Bad Unit",
                "material_slug": "red-satin",
                "quantity_per_unit": 0,  # Invalid
            }
        ]

        result = import_material_units(data, session=db_session)

        assert result.entity_counts["material_units"].failed == 1
        assert any("quantity_per_unit" in e.message for e in result.errors)


# =============================================================================
# Feature 058: Deprecated Field Handling Tests
# =============================================================================


class TestMaterialProductDeprecatedFields:
    """Tests for Feature 058 - deprecated field handling in import/export.

    These tests verify that:
    1. Export excludes current_inventory, weighted_avg_cost, inventory_value
    2. Import ignores these fields if present in old files (backward compatibility)
    3. Round-trip preserves data without these deprecated fields
    """

    def test_export_excludes_deprecated_fields(self, db_session, full_material_catalog):
        """Export should not include current_inventory, weighted_avg_cost, or inventory_value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_complete(tmpdir, session=db_session)

            with open(Path(tmpdir) / "material_products.json") as f:
                data = json.load(f)

            assert len(data["records"]) >= 1
            product = data["records"][0]

            # Verify deprecated fields are NOT present
            for deprecated_field in MATERIAL_PRODUCT_DEPRECATED_FIELDS:
                assert (
                    deprecated_field not in product
                ), f"Deprecated field '{deprecated_field}' should not be in export"

            # Verify expected fields ARE present
            assert "name" in product
            assert "material_slug" in product
            assert "package_quantity" in product
            assert "package_unit" in product

    def test_import_ignores_deprecated_fields(self, db_session, full_material_catalog):
        """Import should succeed when old files contain deprecated fields."""
        # Simulate data from an old export that has deprecated fields
        data = [
            {
                "name": "New Ribbon Roll",
                "material_slug": "red-satin",
                "package_quantity": 500,
                "package_unit": "cm",
                # Deprecated fields from old exports:
                "current_inventory": 250,
                "weighted_avg_cost": "0.10",
                "inventory_value": "25.00",
            }
        ]

        result = import_material_products(data, session=db_session)

        # Import should succeed
        assert result.entity_counts["material_products"].added == 1
        assert result.entity_counts["material_products"].failed == 0

        # Verify the product was created
        product = db_session.query(MaterialProduct).filter_by(name="New Ribbon Roll").first()
        assert product is not None
        assert product.package_quantity == 500
        assert product.package_unit == "cm"

        # Verify deprecated fields are NOT set (model no longer has them)
        assert (
            not hasattr(product, "current_inventory")
            or getattr(product, "current_inventory", None) is None
        )
        assert (
            not hasattr(product, "weighted_avg_cost")
            or getattr(product, "weighted_avg_cost", None) is None
        )
        assert (
            not hasattr(product, "inventory_value")
            or getattr(product, "inventory_value", None) is None
        )

    def test_import_works_without_deprecated_fields(self, db_session, full_material_catalog):
        """Import should work normally when deprecated fields are absent."""
        # Data without deprecated fields (new export format)
        data = [
            {
                "name": "Another Ribbon Roll",
                "material_slug": "red-satin",
                "package_quantity": 300,
                "package_unit": "cm",
            }
        ]

        result = import_material_products(data, session=db_session)

        assert result.entity_counts["material_products"].added == 1
        assert result.entity_counts["material_products"].failed == 0

    def test_roundtrip_preserves_data_without_deprecated_fields(
        self, db_session, full_material_catalog
    ):
        """Export then import should preserve all non-deprecated fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Export
            export_complete(tmpdir, session=db_session)

            # Read exported data
            with open(Path(tmpdir) / "material_products.json") as f:
                export_data = json.load(f)

            original = export_data["records"][0]
            original_name = original["name"]
            original_package_qty = original["package_quantity"]
            original_package_unit = original["package_unit"]

            # Delete existing products
            db_session.query(MaterialProduct).delete()
            db_session.commit()

            # Re-import
            result = import_material_products(export_data["records"], session=db_session)

            assert result.entity_counts["material_products"].added >= 1

            # Verify data integrity
            reimported = db_session.query(MaterialProduct).filter_by(name=original_name).first()
            assert reimported is not None
            assert reimported.package_quantity == original_package_qty
            assert reimported.package_unit == original_package_unit

    def test_import_logs_deprecated_fields(self, db_session, full_material_catalog, caplog):
        """Import should log when deprecated fields are encountered."""
        import logging

        with caplog.at_level(logging.INFO, logger="src.services.catalog_import_service"):
            data = [
                {
                    "name": "Logged Ribbon Roll",
                    "material_slug": "red-satin",
                    "package_quantity": 100,
                    "package_unit": "cm",
                    "current_inventory": 50,  # Deprecated
                }
            ]

            import_material_products(data, session=db_session)

            # Verify log message was generated
            assert any(
                "ignoring deprecated fields" in record.message.lower()
                or "current_inventory" in record.message
                for record in caplog.records
            )
