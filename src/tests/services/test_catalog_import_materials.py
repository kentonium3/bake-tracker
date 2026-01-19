"""
Tests for catalog_import_service materials and material_products import functions.

Tests cover:
- import_materials() with ADD_ONLY and AUGMENT modes
- import_material_products() with slug resolution
- Result count verification
- Error handling for validation and FK resolution

Feature 049: Import/Export System Phase 1 - WP02 Unit Tests
"""

import pytest

from src.models.material_category import MaterialCategory
from src.models.material_subcategory import MaterialSubcategory
from src.models.material import Material
from src.models.material_product import MaterialProduct
from src.models.supplier import Supplier
from src.services.catalog_import_service import (
    import_materials,
    import_material_products,
    ImportMode,
)
from src.services.database import session_scope


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cleanup_material_data(test_db):
    """Cleanup material test data after each test."""
    yield
    with session_scope() as session:
        # Delete in reverse dependency order
        session.query(MaterialProduct).delete(synchronize_session=False)
        session.query(Material).delete(synchronize_session=False)
        session.query(MaterialSubcategory).delete(synchronize_session=False)
        session.query(MaterialCategory).delete(synchronize_session=False)
        session.query(Supplier).delete(synchronize_session=False)


@pytest.fixture
def sample_material_category(test_db):
    """Create a sample material category and subcategory for tests."""
    with session_scope() as session:
        category = MaterialCategory(
            name="Ribbons",
            slug="ribbons",
            description="Ribbon materials",
        )
        session.add(category)
        session.flush()

        subcategory = MaterialSubcategory(
            category_id=category.id,
            name="Satin",
            slug="satin",
            description="Satin ribbons",
        )
        session.add(subcategory)
        session.flush()

        return {
            "category_id": category.id,
            "category_name": category.name,
            "subcategory_id": subcategory.id,
            "subcategory_name": subcategory.name,
        }


@pytest.fixture
def sample_material(test_db, sample_material_category):
    """Create a sample material for tests."""
    with session_scope() as session:
        material = Material(
            subcategory_id=sample_material_category["subcategory_id"],
            name="Red Satin Ribbon",
            slug="red-satin-ribbon",
            base_unit_type="linear_cm",
            description=None,  # Leave null for augment tests
        )
        session.add(material)
        session.flush()

        return {
            "id": material.id,
            "slug": material.slug,
            "name": material.name,
            "subcategory_id": material.subcategory_id,
        }


@pytest.fixture
def sample_supplier_for_materials(test_db):
    """Create a sample supplier for material product tests."""
    with session_scope() as session:
        supplier = Supplier(
            name="Michaels",
            city="Waltham",
            state="MA",
            zip_code="02451",
        )
        session.add(supplier)
        session.flush()
        return {"id": supplier.id, "name": supplier.name}


@pytest.fixture
def sample_material_product(test_db, sample_material, sample_supplier_for_materials):
    """Create a sample material product for tests."""
    with session_scope() as session:
        product = MaterialProduct(
            material_id=sample_material["id"],
            name="100ft Red Satin Roll",
            slug="100ft-red-satin-roll",
            brand=None,  # Leave null for augment tests
            package_quantity=100,
            package_unit="feet",
            quantity_in_base_units=1200,  # 100ft = 1200 inches
            supplier_id=None,  # Leave null for augment tests
        )
        session.add(product)
        session.flush()

        return {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "material_id": product.material_id,
        }


# ============================================================================
# Test: import_materials ADD_ONLY mode - Create New
# ============================================================================


class TestImportMaterialsAddOnlyCreatesNew:
    """Test import_materials creates new materials in ADD_ONLY mode."""

    def test_import_materials_add_only_creates_new(self, test_db, cleanup_material_data):
        """Verify new materials are created with auto-created category/subcategory."""
        data = [
            {
                "name": "Blue Grosgrain Ribbon",
                "category": "Ribbons: Grosgrain",
                "base_unit_type": "linear_cm",
                "description": "A beautiful blue grosgrain ribbon",
            }
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value)

        # Verify success count
        assert result.entity_counts["materials"].added == 1
        assert result.entity_counts["materials"].skipped == 0
        assert result.entity_counts["materials"].failed == 0

        # Verify material was created in database
        with session_scope() as session:
            material = session.query(Material).filter_by(name="Blue Grosgrain Ribbon").first()
            assert material is not None
            assert material.base_unit_type == "linear_cm"
            assert material.description == "A beautiful blue grosgrain ribbon"
            # Verify slug was auto-generated
            assert material.slug == "blue-grosgrain-ribbon"

            # Verify category and subcategory were auto-created
            category = session.query(MaterialCategory).filter_by(name="Ribbons").first()
            assert category is not None

            subcategory = session.query(MaterialSubcategory).filter_by(name="Grosgrain").first()
            assert subcategory is not None
            assert subcategory.category_id == category.id

    def test_import_materials_add_only_with_explicit_slug(self, test_db, cleanup_material_data):
        """Verify explicit slug is used when provided."""
        data = [
            {
                "name": "White Box",
                "slug": "custom-white-box-slug",
                "category": "Boxes: Window Boxes",
                "base_unit_type": "each",
            }
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["materials"].added == 1

        with session_scope() as session:
            material = session.query(Material).filter_by(slug="custom-white-box-slug").first()
            assert material is not None
            assert material.name == "White Box"

    def test_import_materials_add_only_defaults_base_unit_to_each(
        self, test_db, cleanup_material_data
    ):
        """Verify base_unit_type defaults to 'each' when not provided."""
        data = [
            {
                "name": "Gift Tag",
                "category": "Tags: Paper Tags",
                # No base_unit_type provided
            }
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["materials"].added == 1

        with session_scope() as session:
            material = session.query(Material).filter_by(name="Gift Tag").first()
            assert material.base_unit_type == "each"


# ============================================================================
# Test: import_materials ADD_ONLY mode - Skip Existing
# ============================================================================


class TestImportMaterialsAddOnlySkipsExisting:
    """Test import_materials skips existing materials in ADD_ONLY mode."""

    def test_import_materials_add_only_skips_existing(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify existing materials are skipped in ADD_ONLY mode."""
        data = [
            {
                "name": "Red Satin Ribbon",
                "slug": sample_material["slug"],  # Same slug as existing
                "category": "Ribbons: Satin",
                "base_unit_type": "linear_cm",
                "description": "This description should NOT be saved",
            }
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value)

        # Verify skip count
        assert result.entity_counts["materials"].added == 0
        assert result.entity_counts["materials"].skipped == 1
        assert result.entity_counts["materials"].failed == 0

        # Verify original material is unchanged
        with session_scope() as session:
            material = session.query(Material).filter_by(slug=sample_material["slug"]).first()
            # Description should still be None (original value)
            assert material.description is None

    def test_import_materials_add_only_skips_multiple_existing(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify multiple existing materials are skipped."""
        data = [
            {
                "name": "Red Satin Ribbon",
                "slug": sample_material["slug"],
                "category": "Ribbons: Satin",
                "base_unit_type": "linear_cm",
            },
            {
                "name": "New Material",
                "category": "Boxes: Gift Boxes",
                "base_unit_type": "each",
            },
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["materials"].added == 1
        assert result.entity_counts["materials"].skipped == 1


# ============================================================================
# Test: import_materials AUGMENT mode - Updates NULL fields
# ============================================================================


class TestImportMaterialsAugmentUpdatesNullFields:
    """Test import_materials AUGMENT mode fills NULL fields only."""

    def test_import_materials_augment_updates_null_fields(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify AUGMENT mode fills NULL description field."""
        data = [
            {
                "name": "Red Satin Ribbon",
                "slug": sample_material["slug"],
                "category": "Ribbons: Satin",
                "base_unit_type": "linear_cm",
                "description": "Newly added description",
            }
        ]

        result = import_materials(data, mode=ImportMode.AUGMENT.value)

        # Verify augment count
        assert result.entity_counts["materials"].added == 0
        assert result.entity_counts["materials"].augmented == 1
        assert result.entity_counts["materials"].skipped == 0

        # Verify description was updated
        with session_scope() as session:
            material = session.query(Material).filter_by(slug=sample_material["slug"]).first()
            assert material.description == "Newly added description"

    def test_import_materials_augment_skips_no_null_fields(self, test_db, cleanup_material_data):
        """Verify AUGMENT mode skips when no NULL fields to update."""
        # First create a material with description already set
        with session_scope() as session:
            category = MaterialCategory(name="Bags", slug="bags")
            session.add(category)
            session.flush()

            subcategory = MaterialSubcategory(category_id=category.id, name="Paper", slug="paper")
            session.add(subcategory)
            session.flush()

            material = Material(
                subcategory_id=subcategory.id,
                name="Brown Paper Bag",
                slug="brown-paper-bag",
                base_unit_type="each",
                description="Already has a description",  # Not null
            )
            session.add(material)

        # Try to augment with new description
        data = [
            {
                "name": "Brown Paper Bag",
                "slug": "brown-paper-bag",
                "category": "Bags: Paper",
                "base_unit_type": "each",
                "description": "This should NOT overwrite",
            }
        ]

        result = import_materials(data, mode=ImportMode.AUGMENT.value)

        # Should be skipped since no null fields to update
        assert result.entity_counts["materials"].augmented == 0
        assert result.entity_counts["materials"].skipped == 1

        # Verify original description is preserved
        with session_scope() as session:
            material = session.query(Material).filter_by(slug="brown-paper-bag").first()
            assert material.description == "Already has a description"


# ============================================================================
# Test: import_materials AUGMENT mode - Preserves Protected Fields
# ============================================================================


class TestImportMaterialsAugmentPreservesProtectedFields:
    """Test import_materials AUGMENT mode preserves protected fields."""

    def test_import_materials_augment_preserves_protected_fields(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify name, slug, base_unit_type are NOT modified in AUGMENT mode."""
        original_name = sample_material["name"]
        original_slug = sample_material["slug"]

        data = [
            {
                "name": "MODIFIED NAME",  # Try to change name
                "slug": sample_material["slug"],  # Must match for lookup
                "category": "Ribbons: Satin",
                "base_unit_type": "square_cm",  # Try to change base_unit_type
                "description": "Add description",
            }
        ]

        result = import_materials(data, mode=ImportMode.AUGMENT.value)

        # Should augment description only
        assert result.entity_counts["materials"].augmented == 1

        with session_scope() as session:
            material = session.query(Material).filter_by(slug=sample_material["slug"]).first()
            # Protected fields should be unchanged
            assert material.name == original_name
            assert material.slug == original_slug
            assert material.base_unit_type == "linear_cm"  # Original value
            # Only null field should be updated
            assert material.description == "Add description"


# ============================================================================
# Test: import_material_products - Slug Resolution
# ============================================================================


class TestImportMaterialProductsResolvesSlug:
    """Test import_material_products resolves material_slug correctly."""

    def test_import_material_products_resolves_slug(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify material_slug is resolved to material_id."""
        data = [
            {
                "name": "50ft Red Satin Spool",
                "material_slug": sample_material["slug"],
                "package_quantity": 50,
                "package_unit": "feet",
                "quantity_in_base_units": 600,
            }
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].added == 1
        assert result.entity_counts["material_products"].failed == 0

        with session_scope() as session:
            product = session.query(MaterialProduct).filter_by(name="50ft Red Satin Spool").first()
            assert product is not None
            assert product.material_id == sample_material["id"]

    def test_import_material_products_resolves_material_by_name(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify material can be resolved by display name."""
        data = [
            {
                "name": "25ft Red Satin Mini Roll",
                "material": sample_material["name"],  # Use display name
                "package_quantity": 25,
                "package_unit": "feet",
                "quantity_in_base_units": 300,
            }
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].added == 1

        with session_scope() as session:
            product = (
                session.query(MaterialProduct).filter_by(name="25ft Red Satin Mini Roll").first()
            )
            assert product.material_id == sample_material["id"]

    def test_import_material_products_prefers_slug_over_name(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify material_slug takes precedence over material name."""
        # Create another material with similar name
        with session_scope() as session:
            category = session.query(MaterialCategory).filter_by(name="Ribbons").first()
            if not category:
                category = MaterialCategory(name="Ribbons", slug="ribbons")
                session.add(category)
                session.flush()

            subcat = session.query(MaterialSubcategory).filter_by(name="Satin").first()
            if not subcat:
                subcat = MaterialSubcategory(category_id=category.id, name="Satin", slug="satin")
                session.add(subcat)
                session.flush()

            other_material = Material(
                subcategory_id=subcat.id,
                name="Red Satin Ribbon",  # Same display name
                slug="red-satin-ribbon-wide",  # Different slug
                base_unit_type="linear_cm",
            )
            session.add(other_material)
            session.flush()
            other_id = other_material.id

        data = [
            {
                "name": "Test Product",
                "material_slug": "red-satin-ribbon-wide",  # Specific slug
                "material": "Red Satin Ribbon",  # Ambiguous name
                "package_quantity": 10,
                "package_unit": "feet",
                "quantity_in_base_units": 120,
            }
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].added == 1

        with session_scope() as session:
            product = session.query(MaterialProduct).filter_by(name="Test Product").first()
            # Should use slug match, not name match
            assert product.material_id == other_id


# ============================================================================
# Test: import_material_products - Error on Invalid Slug
# ============================================================================


class TestImportMaterialProductsErrorInvalidSlug:
    """Test import_material_products errors on invalid material_slug."""

    def test_import_material_products_error_invalid_slug(self, test_db, cleanup_material_data):
        """Verify error when material_slug does not exist."""
        data = [
            {
                "name": "Orphan Product",
                "material_slug": "nonexistent-material-slug",
                "package_quantity": 10,
                "package_unit": "each",
                "quantity_in_base_units": 10,
            }
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].added == 0
        assert result.entity_counts["material_products"].failed == 1
        assert len(result.errors) == 1

        error = result.errors[0]
        assert error.entity_type == "material_products"
        assert error.error_type == "fk_missing"
        assert "nonexistent-material-slug" in error.message

    def test_import_material_products_error_no_material_reference(
        self, test_db, cleanup_material_data
    ):
        """Verify error when neither material_slug nor material name provided."""
        data = [
            {
                "name": "No Material Reference",
                "package_quantity": 10,
                "package_unit": "each",
                "quantity_in_base_units": 10,
            }
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].added == 0
        assert result.entity_counts["material_products"].failed == 1
        assert result.errors[0].error_type == "fk_missing"


# ============================================================================
# Test: import_materials Result Counts
# ============================================================================


class TestImportMaterialsResultCounts:
    """Test ImportResult has correct successful/skipped/failed counts."""

    def test_import_materials_result_counts(self, test_db, sample_material, cleanup_material_data):
        """Verify ImportResult has accurate counts for mixed operations."""
        data = [
            # Should be added (new material)
            {
                "name": "New Blue Ribbon",
                "category": "Ribbons: Satin",
                "base_unit_type": "linear_cm",
            },
            # Should be skipped (existing slug)
            {
                "name": "Red Satin Ribbon",
                "slug": sample_material["slug"],
                "category": "Ribbons: Satin",
                "base_unit_type": "linear_cm",
            },
            # Should fail (missing category)
            {
                "name": "Missing Category Material",
                "base_unit_type": "each",
            },
            # Should fail (invalid category format)
            {
                "name": "Bad Category Format",
                "category": "NoColonSeparator",
                "base_unit_type": "each",
            },
            # Should fail (invalid base_unit_type)
            {
                "name": "Invalid Unit Type",
                "category": "Boxes: Gift Boxes",
                "base_unit_type": "invalid_unit",
            },
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value)

        # Verify counts
        assert result.entity_counts["materials"].added == 1
        assert result.entity_counts["materials"].skipped == 1
        assert result.entity_counts["materials"].failed == 3

        # Verify total counts via properties
        assert result.total_added == 1
        assert result.total_skipped == 1
        assert result.total_failed == 3

        # Verify error details
        assert len(result.errors) == 3
        error_types = [e.error_type for e in result.errors]
        assert error_types.count("validation") == 3  # All validation errors

    def test_import_materials_result_counts_augment_mode(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify counts are correct in AUGMENT mode."""
        data = [
            # Should be augmented (existing with null description)
            {
                "name": "Red Satin Ribbon",
                "slug": sample_material["slug"],
                "category": "Ribbons: Satin",
                "base_unit_type": "linear_cm",
                "description": "Added description",
            },
            # Should be added (new)
            {
                "name": "Brand New Material",
                "category": "Bags: Paper",
                "base_unit_type": "each",
            },
        ]

        result = import_materials(data, mode=ImportMode.AUGMENT.value)

        assert result.entity_counts["materials"].added == 1
        assert result.entity_counts["materials"].augmented == 1
        assert result.entity_counts["materials"].skipped == 0
        assert result.entity_counts["materials"].failed == 0
        assert result.total_augmented == 1

    def test_import_material_products_result_counts(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify result counts for material_products import."""
        data = [
            # Should succeed
            {
                "name": "Success Product",
                "material_slug": sample_material["slug"],
                "package_quantity": 10,
                "package_unit": "feet",
                "quantity_in_base_units": 120,
            },
            # Should fail (missing material)
            {
                "name": "Failed Product",
                "material_slug": "nonexistent",
                "package_quantity": 5,
                "package_unit": "each",
                "quantity_in_base_units": 5,
            },
            # Should fail (missing package_unit)
            {
                "name": "Missing Unit Product",
                "material_slug": sample_material["slug"],
                "package_quantity": 5,
            },
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].added == 1
        assert result.entity_counts["material_products"].failed == 2

    def test_import_materials_dry_run_no_changes(self, test_db, cleanup_material_data):
        """Verify dry_run=True does not persist changes."""
        data = [
            {
                "name": "Dry Run Material",
                "category": "Ribbons: Test",
                "base_unit_type": "each",
            }
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value, dry_run=True)

        # Should report success but not persist
        assert result.entity_counts["materials"].added == 1
        assert result.dry_run is True

        # Verify nothing was actually saved
        with session_scope() as session:
            material = session.query(Material).filter_by(name="Dry Run Material").first()
            assert material is None


# ============================================================================
# Test: import_material_products AUGMENT mode
# ============================================================================


class TestImportMaterialProductsAugmentMode:
    """Test import_material_products AUGMENT mode behavior."""

    def test_import_material_products_augment_fills_brand(
        self, test_db, sample_material_product, cleanup_material_data
    ):
        """Verify AUGMENT mode fills NULL brand field."""
        data = [
            {
                "name": sample_material_product["name"],
                "slug": sample_material_product["slug"],
                "material_slug": "red-satin-ribbon",
                "brand": "Premium Brand",
                "package_quantity": 100,
                "package_unit": "feet",
                "quantity_in_base_units": 1200,
            }
        ]

        result = import_material_products(data, mode=ImportMode.AUGMENT.value)

        assert result.entity_counts["material_products"].augmented == 1

        with session_scope() as session:
            product = (
                session.query(MaterialProduct)
                .filter_by(slug=sample_material_product["slug"])
                .first()
            )
            assert product.brand == "Premium Brand"

    def test_import_material_products_augment_fills_supplier(
        self, test_db, sample_material_product, sample_supplier_for_materials, cleanup_material_data
    ):
        """Verify AUGMENT mode fills NULL supplier_id field."""
        data = [
            {
                "name": sample_material_product["name"],
                "slug": sample_material_product["slug"],
                "material_slug": "red-satin-ribbon",
                "supplier": sample_supplier_for_materials["name"],
                "package_quantity": 100,
                "package_unit": "feet",
                "quantity_in_base_units": 1200,
            }
        ]

        result = import_material_products(data, mode=ImportMode.AUGMENT.value)

        assert result.entity_counts["material_products"].augmented == 1

        with session_scope() as session:
            product = (
                session.query(MaterialProduct)
                .filter_by(slug=sample_material_product["slug"])
                .first()
            )
            assert product.supplier_id == sample_supplier_for_materials["id"]

    def test_import_material_products_skips_existing_add_mode(
        self, test_db, sample_material_product, cleanup_material_data
    ):
        """Verify ADD_ONLY mode skips existing products."""
        data = [
            {
                "name": sample_material_product["name"],
                "slug": sample_material_product["slug"],
                "material_slug": "red-satin-ribbon",
                "brand": "Should Not Be Set",
                "package_quantity": 100,
                "package_unit": "feet",
                "quantity_in_base_units": 1200,
            }
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].added == 0
        assert result.entity_counts["material_products"].skipped == 1

        # Verify brand is still null
        with session_scope() as session:
            product = (
                session.query(MaterialProduct)
                .filter_by(slug=sample_material_product["slug"])
                .first()
            )
            assert product.brand is None


# ============================================================================
# Test: Validation Errors
# ============================================================================


class TestImportMaterialsValidationErrors:
    """Test validation error handling."""

    def test_import_materials_missing_name(self, test_db, cleanup_material_data):
        """Verify error when name is missing."""
        data = [
            {
                "category": "Ribbons: Satin",
                "base_unit_type": "each",
                # Missing name
            }
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["materials"].failed == 1
        assert result.errors[0].error_type == "validation"
        assert "name" in result.errors[0].message.lower()

    def test_import_materials_accepts_display_name(self, test_db, cleanup_material_data):
        """Verify display_name is accepted as fallback for name."""
        data = [
            {
                "display_name": "Display Name Material",
                "category": "Ribbons: Satin",
                "base_unit_type": "each",
            }
        ]

        result = import_materials(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["materials"].added == 1

        with session_scope() as session:
            material = session.query(Material).filter_by(name="Display Name Material").first()
            assert material is not None

    def test_import_material_products_missing_name(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify error when product name is missing."""
        data = [
            {
                "material_slug": sample_material["slug"],
                "package_quantity": 10,
                "package_unit": "each",
                "quantity_in_base_units": 10,
                # Missing name
            }
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].failed == 1
        assert result.errors[0].error_type == "validation"

    def test_import_material_products_missing_package_unit(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify error when package_unit is missing."""
        data = [
            {
                "name": "Product Without Unit",
                "material_slug": sample_material["slug"],
                "package_quantity": 10,
                "quantity_in_base_units": 10,
                # Missing package_unit
            }
        ]

        result = import_material_products(data, mode=ImportMode.ADD_ONLY.value)

        assert result.entity_counts["material_products"].failed == 1
        assert result.errors[0].error_type == "validation"
        assert "package_unit" in result.errors[0].message.lower()


# ============================================================================
# Test: Session Parameter
# ============================================================================


class TestImportMaterialsSessionParameter:
    """Test that functions accept session parameter correctly."""

    def test_import_materials_with_session(self, test_db, cleanup_material_data):
        """Verify import_materials works with passed session."""
        data = [
            {
                "name": "Session Test Material",
                "category": "Bags: Paper",
                "base_unit_type": "each",
            }
        ]

        with session_scope() as session:
            result = import_materials(data, mode=ImportMode.ADD_ONLY.value, session=session)

            assert result.entity_counts["materials"].added == 1

            # Verify within same session
            material = session.query(Material).filter_by(name="Session Test Material").first()
            assert material is not None

    def test_import_material_products_with_session(
        self, test_db, sample_material, cleanup_material_data
    ):
        """Verify import_material_products works with passed session."""
        data = [
            {
                "name": "Session Test Product",
                "material_slug": sample_material["slug"],
                "package_quantity": 5,
                "package_unit": "each",
                "quantity_in_base_units": 5,
            }
        ]

        with session_scope() as session:
            result = import_material_products(data, mode=ImportMode.ADD_ONLY.value, session=session)

            assert result.entity_counts["material_products"].added == 1

            product = session.query(MaterialProduct).filter_by(name="Session Test Product").first()
            assert product is not None
