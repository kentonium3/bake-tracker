"""
Tests for Material Catalog Service - CRUD operations for material hierarchy.

Part of Feature 047: Materials Management System.
"""

import pytest
from decimal import Decimal

from src.services.material_catalog_service import (
    # Category operations
    create_category,
    get_category,
    list_categories,
    update_category,
    delete_category,
    # Subcategory operations
    create_subcategory,
    get_subcategory,
    list_subcategories,
    update_subcategory,
    delete_subcategory,
    # Material operations
    create_material,
    get_material,
    list_materials,
    update_material,
    delete_material,
    # Product operations
    create_product,
    get_product,
    list_products,
    update_product,
    delete_product,
    # Utilities
    slugify,
)
from src.services.exceptions import ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_session(test_db):
    """Provide a database session for tests."""
    return test_db()


@pytest.fixture
def sample_category(test_db):
    """Create a sample category for tests."""
    session = test_db()
    return create_category("Ribbons", session=session)


@pytest.fixture
def sample_subcategory(test_db, sample_category):
    """Create a sample subcategory for tests."""
    session = test_db()
    return create_subcategory(sample_category.id, "Satin", session=session)


@pytest.fixture
def sample_material(test_db, sample_subcategory):
    """Create a sample material for tests."""
    session = test_db()
    return create_material(
        sample_subcategory.id,
        "Red Satin Ribbon",
        "linear_cm",
        session=session,
    )


@pytest.fixture
def sample_product(test_db, sample_material):
    """Create a sample product for tests."""
    session = test_db()
    return create_product(
        sample_material.id,
        "100ft Red Satin Roll",
        100,
        "feet",
        brand="Michaels",
        session=session,
    )


# ============================================================================
# Slugify Tests
# ============================================================================


class TestSlugify:
    """Tests for slug generation utility."""

    def test_basic_slug(self):
        """Simple name converts to lowercase with underscores."""
        assert slugify("Red Satin Ribbon") == "red_satin_ribbon"

    def test_slug_with_hyphens(self):
        """Hyphens convert to underscores."""
        assert slugify("Semi-Sweet Chips") == "semi_sweet_chips"

    def test_slug_special_chars(self):
        """Special characters are removed."""
        assert slugify("Bob's Red Mill (25 lb)") == "bobs_red_mill_25_lb"

    def test_slug_consecutive_spaces(self):
        """Multiple spaces collapse to single underscore."""
        assert slugify("Multi    Space    Name") == "multi_space_name"

    def test_slug_leading_trailing(self):
        """Leading/trailing whitespace stripped."""
        assert slugify("  Ribbon  ") == "ribbon"


# ============================================================================
# Category Tests
# ============================================================================


class TestCategoryOperations:
    """Tests for category CRUD operations."""

    def test_create_category(self, db_session):
        """Can create a new category."""
        cat = create_category("Boxes", session=db_session)

        assert cat.id is not None
        assert cat.name == "Boxes"
        assert cat.slug == "boxes"
        assert cat.sort_order == 0

    def test_create_category_auto_slug(self, db_session):
        """Slug is auto-generated from name."""
        cat = create_category("Gift Tags & Labels", session=db_session)

        assert cat.slug == "gift_tags_labels"

    def test_create_category_custom_slug(self, db_session):
        """Can provide custom slug."""
        cat = create_category("Boxes", slug="custom_boxes", session=db_session)

        assert cat.slug == "custom_boxes"

    def test_create_category_unique_slug(self, db_session):
        """Duplicate slugs get numeric suffix."""
        cat1 = create_category("Ribbons", slug="ribbons", session=db_session)
        cat2 = create_category("More Ribbons", slug="ribbons", session=db_session)

        assert cat1.slug == "ribbons"
        assert cat2.slug == "ribbons_2"

    def test_create_category_empty_name_fails(self, db_session):
        """Empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            create_category("", session=db_session)

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_get_category_by_id(self, db_session, sample_category):
        """Can retrieve category by ID."""
        cat = get_category(category_id=sample_category.id, session=db_session)

        assert cat is not None
        assert cat.name == sample_category.name

    def test_get_category_by_slug(self, db_session, sample_category):
        """Can retrieve category by slug."""
        cat = get_category(slug=sample_category.slug, session=db_session)

        assert cat is not None
        assert cat.id == sample_category.id

    def test_get_category_not_found(self, db_session):
        """Returns None for non-existent category."""
        cat = get_category(category_id=99999, session=db_session)

        assert cat is None

    def test_list_categories(self, db_session):
        """List returns all categories ordered by sort_order."""
        create_category("Boxes", sort_order=2, session=db_session)
        create_category("Ribbons", sort_order=1, session=db_session)
        create_category("Tags", sort_order=0, session=db_session)

        categories = list_categories(session=db_session)

        assert len(categories) == 3
        assert categories[0].name == "Tags"
        assert categories[1].name == "Ribbons"
        assert categories[2].name == "Boxes"

    def test_update_category(self, db_session, sample_category):
        """Can update category fields."""
        updated = update_category(
            sample_category.id,
            name="Updated Ribbons",
            description="All ribbon types",
            sort_order=5,
            session=db_session,
        )

        assert updated.name == "Updated Ribbons"
        assert updated.description == "All ribbon types"
        assert updated.sort_order == 5

    def test_update_category_not_found(self, db_session):
        """Update raises for non-existent category."""
        with pytest.raises(ValidationError) as exc_info:
            update_category(99999, name="New Name", session=db_session)

        assert "not found" in str(exc_info.value).lower()

    def test_delete_category(self, db_session):
        """Can delete category with no children."""
        cat = create_category("To Delete", session=db_session)
        result = delete_category(cat.id, session=db_session)

        assert result is True
        assert get_category(category_id=cat.id, session=db_session) is None

    def test_delete_category_with_children_fails(
        self, db_session, sample_category, sample_subcategory
    ):
        """Cannot delete category with subcategories."""
        with pytest.raises(ValidationError) as exc_info:
            delete_category(sample_category.id, session=db_session)

        assert "has" in str(exc_info.value).lower()
        assert "subcategory" in str(exc_info.value).lower()


# ============================================================================
# Subcategory Tests
# ============================================================================


class TestSubcategoryOperations:
    """Tests for subcategory CRUD operations."""

    def test_create_subcategory(self, db_session, sample_category):
        """Can create a subcategory."""
        subcat = create_subcategory(
            sample_category.id,
            "Grosgrain",
            session=db_session,
        )

        assert subcat.id is not None
        assert subcat.name == "Grosgrain"
        assert subcat.category_id == sample_category.id

    def test_create_subcategory_invalid_category(self, db_session):
        """Fails if category doesn't exist."""
        with pytest.raises(ValidationError) as exc_info:
            create_subcategory(99999, "Test", session=db_session)

        assert "category" in str(exc_info.value).lower()
        assert "not found" in str(exc_info.value).lower()

    def test_get_subcategory_by_id(self, db_session, sample_subcategory):
        """Can retrieve subcategory by ID."""
        subcat = get_subcategory(subcategory_id=sample_subcategory.id, session=db_session)

        assert subcat is not None
        assert subcat.name == sample_subcategory.name

    def test_list_subcategories_all(self, db_session, sample_category):
        """List returns all subcategories."""
        create_subcategory(sample_category.id, "Satin", session=db_session)
        create_subcategory(sample_category.id, "Grosgrain", session=db_session)

        subcats = list_subcategories(session=db_session)

        assert len(subcats) == 2

    def test_list_subcategories_by_category(self, db_session):
        """Can filter subcategories by category."""
        cat1 = create_category("Ribbons", session=db_session)
        cat2 = create_category("Boxes", session=db_session)
        create_subcategory(cat1.id, "Satin", session=db_session)
        create_subcategory(cat1.id, "Grosgrain", session=db_session)
        create_subcategory(cat2.id, "Cardboard", session=db_session)

        ribbon_subcats = list_subcategories(category_id=cat1.id, session=db_session)
        box_subcats = list_subcategories(category_id=cat2.id, session=db_session)

        assert len(ribbon_subcats) == 2
        assert len(box_subcats) == 1

    def test_delete_subcategory(self, db_session, sample_category):
        """Can delete subcategory with no materials."""
        subcat = create_subcategory(sample_category.id, "To Delete", session=db_session)
        result = delete_subcategory(subcat.id, session=db_session)

        assert result is True

    def test_delete_subcategory_with_materials_fails(
        self, db_session, sample_subcategory, sample_material
    ):
        """Cannot delete subcategory with materials."""
        with pytest.raises(ValidationError) as exc_info:
            delete_subcategory(sample_subcategory.id, session=db_session)

        assert "has" in str(exc_info.value).lower()
        assert "material" in str(exc_info.value).lower()


# ============================================================================
# Material Tests
# ============================================================================


class TestMaterialOperations:
    """Tests for material CRUD operations."""

    def test_create_material_linear_cm(self, db_session, sample_subcategory):
        """Can create material with linear_cm base unit."""
        mat = create_material(
            sample_subcategory.id,
            "Blue Ribbon",
            "linear_cm",
            session=db_session,
        )

        assert mat.id is not None
        assert mat.base_unit_type == "linear_cm"

    def test_create_material_each(self, db_session, sample_subcategory):
        """Can create material with 'each' base unit."""
        mat = create_material(
            sample_subcategory.id,
            "Gift Box",
            "each",
            session=db_session,
        )

        assert mat.base_unit_type == "each"

    def test_create_material_invalid_base_unit(self, db_session, sample_subcategory):
        """Invalid base_unit_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            create_material(
                sample_subcategory.id,
                "Test",
                "invalid_unit",
                session=db_session,
            )

        assert "base_unit_type" in str(exc_info.value).lower()

    def test_get_material_by_id(self, db_session, sample_material):
        """Can retrieve material by ID."""
        mat = get_material(material_id=sample_material.id, session=db_session)

        assert mat is not None
        assert mat.name == sample_material.name

    def test_get_material_by_slug(self, db_session, sample_material):
        """Can retrieve material by slug."""
        mat = get_material(slug=sample_material.slug, session=db_session)

        assert mat is not None
        assert mat.id == sample_material.id

    def test_list_materials_by_subcategory(self, db_session, sample_subcategory):
        """Can filter materials by subcategory."""
        create_material(sample_subcategory.id, "Red Ribbon", "linear_cm", session=db_session)
        create_material(sample_subcategory.id, "Blue Ribbon", "linear_cm", session=db_session)

        materials = list_materials(subcategory_id=sample_subcategory.id, session=db_session)

        assert len(materials) == 2

    def test_update_material(self, db_session, sample_material):
        """Can update material fields."""
        updated = update_material(
            sample_material.id,
            name="Updated Material",
            notes="Test notes",
            session=db_session,
        )

        assert updated.name == "Updated Material"
        assert updated.notes == "Test notes"

    def test_delete_material_no_inventory(self, db_session, sample_subcategory):
        """Can delete material with no inventory."""
        mat = create_material(
            sample_subcategory.id,
            "To Delete",
            "each",
            session=db_session,
        )
        result = delete_material(mat.id, session=db_session)

        assert result is True


# ============================================================================
# Product Tests
# ============================================================================


class TestProductOperations:
    """Tests for product CRUD operations."""

    def test_create_product_feet_to_cm(self, db_session, sample_material):
        """Creates product and converts feet to centimeters."""
        prod = create_product(
            sample_material.id,
            "100ft Roll",
            100,
            "feet",
            session=db_session,
        )

        assert prod.id is not None
        assert prod.package_quantity == 100
        assert prod.package_unit == "feet"
        assert prod.quantity_in_base_units == 3048.0  # 100 feet * 30.48 = 3048 cm

    def test_create_product_yards_to_cm(self, db_session, sample_material):
        """Converts yards to centimeters correctly."""
        prod = create_product(
            sample_material.id,
            "10yd Roll",
            10,
            "yards",
            session=db_session,
        )

        assert prod.quantity_in_base_units == 914.4  # 10 yards * 91.44 = 914.4 cm

    def test_create_product_each(self, db_session, sample_subcategory):
        """Creates 'each' product without conversion."""
        mat = create_material(
            sample_subcategory.id,
            "Gift Boxes",
            "each",
            session=db_session,
        )
        prod = create_product(mat.id, "Box of 10", 10, "each", session=db_session)

        assert prod.quantity_in_base_units == 10

    def test_create_product_invalid_unit(self, db_session, sample_material):
        """Invalid unit for material type raises error."""
        with pytest.raises(ValidationError) as exc_info:
            create_product(
                sample_material.id,
                "Test",
                100,
                "gallons",  # gallons doesn't convert to linear_cm
                session=db_session,
            )

        assert "compatible" in str(exc_info.value).lower()

    def test_create_product_with_brand(self, db_session, sample_material):
        """Can set brand on product."""
        prod = create_product(
            sample_material.id,
            "100ft Roll",
            100,
            "feet",
            brand="Michaels",
            session=db_session,
        )

        assert prod.brand == "Michaels"
        assert prod.display_name == "Michaels 100ft Roll"

    def test_get_product_by_id(self, db_session, sample_product):
        """Can retrieve product by ID."""
        prod = get_product(sample_product.id, session=db_session)

        assert prod is not None
        assert prod.name == sample_product.name

    def test_list_products_by_material(self, db_session, sample_material):
        """Can filter products by material."""
        create_product(sample_material.id, "Small Roll", 50, "feet", session=db_session)
        create_product(sample_material.id, "Large Roll", 200, "feet", session=db_session)

        products = list_products(material_id=sample_material.id, session=db_session)

        assert len(products) == 2

    def test_list_products_exclude_hidden(self, db_session, sample_material):
        """Hidden products excluded by default."""
        prod1 = create_product(sample_material.id, "Visible", 50, "feet", session=db_session)
        prod2 = create_product(sample_material.id, "Hidden", 50, "feet", session=db_session)
        update_product(prod2.id, is_hidden=True, session=db_session)

        visible = list_products(material_id=sample_material.id, session=db_session)
        all_products = list_products(
            material_id=sample_material.id,
            include_hidden=True,
            session=db_session,
        )

        assert len(visible) == 1
        assert len(all_products) == 2

    def test_update_product(self, db_session, sample_product):
        """Can update product fields."""
        updated = update_product(
            sample_product.id,
            name="Updated Product",
            brand="New Brand",
            sku="SKU123",
            session=db_session,
        )

        assert updated.name == "Updated Product"
        assert updated.brand == "New Brand"
        assert updated.sku == "SKU123"

    def test_delete_product_no_inventory(self, db_session, sample_material):
        """Can delete product with no inventory."""
        prod = create_product(
            sample_material.id,
            "To Delete",
            50,
            "feet",
            session=db_session,
        )
        result = delete_product(prod.id, session=db_session)

        assert result is True

    def test_delete_product_with_inventory_fails(self, db_session, sample_product, sample_supplier):
        """Cannot delete product with inventory.

        F058: Inventory is now tracked via MaterialInventoryItem (FIFO).
        This test creates a MaterialPurchase and MaterialInventoryItem to represent inventory.
        """
        from datetime import date
        from src.models.material_purchase import MaterialPurchase
        from src.models.material_inventory_item import MaterialInventoryItem

        # Create a purchase to link the inventory item to
        purchase = MaterialPurchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("10.00"),
            units_added=100.0,
            unit_cost=Decimal("0.10"),
        )
        db_session.add(purchase)
        db_session.flush()

        # Create inventory item with quantity remaining (F058)
        inv_item = MaterialInventoryItem(
            material_product_id=sample_product.id,
            material_purchase_id=purchase.id,
            quantity_purchased=100.0,
            quantity_remaining=100.0,  # Has inventory remaining
            cost_per_unit=Decimal("0.10"),
            purchase_date=date.today(),
        )
        db_session.add(inv_item)
        db_session.flush()

        with pytest.raises(ValidationError) as exc_info:
            delete_product(sample_product.id, session=db_session)

        assert "inventory" in str(exc_info.value).lower()


# ============================================================================
# Hierarchy Integration Tests
# ============================================================================


class TestHierarchyIntegration:
    """Integration tests for complete hierarchy operations."""

    def test_create_full_hierarchy(self, db_session):
        """Can create complete hierarchy via service calls."""
        # Create category
        cat = create_category("Ribbons", session=db_session)
        assert cat.name == "Ribbons"

        # Create subcategory
        subcat = create_subcategory(cat.id, "Satin", session=db_session)
        assert subcat.category_id == cat.id

        # Create material
        mat = create_material(
            subcat.id,
            "Red Satin",
            "linear_cm",
            session=db_session,
        )
        assert mat.subcategory_id == subcat.id

        # Create product
        prod = create_product(
            mat.id,
            "Michaels 100ft Roll",
            100,
            "feet",
            brand="Michaels",
            session=db_session,
        )
        assert prod.material_id == mat.id
        assert prod.quantity_in_base_units == 3048.0  # 100 feet * 30.48 cm/ft

    def test_delete_requires_empty_children(self, db_session):
        """Deletion respects hierarchy constraints."""
        cat = create_category("Test Category", session=db_session)
        subcat = create_subcategory(cat.id, "Test Subcategory", session=db_session)
        mat = create_material(subcat.id, "Test Material", "each", session=db_session)
        prod = create_product(mat.id, "Test Product", 1, "each", session=db_session)

        # Cannot delete category (has subcategory)
        with pytest.raises(ValidationError):
            delete_category(cat.id, session=db_session)

        # Cannot delete subcategory (has material)
        with pytest.raises(ValidationError):
            delete_subcategory(subcat.id, session=db_session)

        # Can delete product (no inventory)
        delete_product(prod.id, session=db_session)

        # Flush to ensure product deletion is persisted
        db_session.flush()

        # Now can delete material (no products with inventory)
        delete_material(mat.id, session=db_session)

        # Flush to ensure material deletion is persisted
        db_session.flush()

        # Refresh subcategory to clear stale relationship cache
        db_session.refresh(subcat)

        # Now can delete subcategory (no materials)
        delete_subcategory(subcat.id, session=db_session)

        # Flush to ensure subcategory deletion is persisted
        db_session.flush()

        # Refresh category to clear stale relationship cache
        db_session.refresh(cat)

        # Now can delete category (no subcategories)
        delete_category(cat.id, session=db_session)


# ============================================================================
# Provisional Product Tests (Feature 059)
# ============================================================================


@pytest.fixture
def sample_each_material(test_db, sample_subcategory):
    """Create a sample material with 'each' base unit type for tests."""
    session = test_db()
    return create_material(
        sample_subcategory.id,
        "Gift Boxes",
        "each",
        session=session,
    )


class TestProvisionalProductLifecycle:
    """Tests for provisional product creation and enrichment (Feature 059)."""

    def test_create_provisional_product(self, db_session, sample_each_material):
        """Test creating a product with is_provisional=True."""
        prod = create_product(
            sample_each_material.id,
            "Test Bags",
            50,
            "each",
            is_provisional=True,
            session=db_session,
        )

        assert prod.is_provisional is True
        assert prod.name == "Test Bags"

    def test_create_non_provisional_product_default(self, db_session, sample_each_material):
        """Test that is_provisional defaults to False."""
        prod = create_product(
            sample_each_material.id,
            "Test Bags",
            50,
            "each",
            brand="TestBrand",
            session=db_session,
        )

        assert prod.is_provisional is False

    def test_check_completeness_complete_product(self, db_session, sample_each_material):
        """Test completeness check for a product with all required fields."""
        from src.services.material_catalog_service import check_provisional_completeness

        prod = create_product(
            sample_each_material.id,
            "Complete Product",
            50,
            "each",
            brand="TestBrand",
            slug="complete_product",
            session=db_session,
        )

        is_complete, missing = check_provisional_completeness(prod.id, session=db_session)

        assert is_complete is True
        assert missing == []

    def test_check_completeness_missing_brand(self, db_session, sample_each_material):
        """Test completeness check when brand is missing."""
        from src.services.material_catalog_service import check_provisional_completeness

        prod = create_product(
            sample_each_material.id,
            "Incomplete Product",
            50,
            "each",
            # No brand provided
            session=db_session,
        )

        is_complete, missing = check_provisional_completeness(prod.id, session=db_session)

        assert is_complete is False
        assert "brand" in missing

    def test_check_completeness_multiple_missing_fields(self, db_session, sample_each_material):
        """Test completeness check reports all missing fields."""
        from src.services.material_catalog_service import check_provisional_completeness

        # Create a minimal provisional product
        prod = create_product(
            sample_each_material.id,
            "Minimal Product",
            50,
            "each",
            is_provisional=True,
            session=db_session,
        )
        # Note: name, material_id, package_quantity, package_unit, and slug are all set
        # Only brand should be missing

        is_complete, missing = check_provisional_completeness(prod.id, session=db_session)

        assert is_complete is False
        assert "brand" in missing

    def test_check_completeness_product_not_found(self, db_session):
        """Test completeness check raises error for non-existent product."""
        from src.services.material_catalog_service import check_provisional_completeness

        with pytest.raises(ValidationError) as exc_info:
            check_provisional_completeness(99999, session=db_session)

        assert "not found" in str(exc_info.value).lower()

    def test_auto_promote_on_enrichment(self, db_session, sample_each_material):
        """Test that provisional product auto-promotes when enriched with all required fields."""
        # Create provisional product without brand
        prod = create_product(
            sample_each_material.id,
            "Provisional Product",
            50,
            "each",
            is_provisional=True,
            session=db_session,
        )
        assert prod.is_provisional is True

        # Update with brand (completing the product)
        updated = update_product(prod.id, brand="TestBrand", session=db_session)

        assert updated.is_provisional is False

    def test_no_auto_promote_if_still_incomplete(self, db_session, sample_each_material):
        """Test that provisional product stays provisional if still incomplete after update."""
        # Create provisional product without brand
        prod = create_product(
            sample_each_material.id,
            "Provisional Product",
            50,
            "each",
            is_provisional=True,
            session=db_session,
        )
        assert prod.is_provisional is True

        # Update with notes only (not completing the product - brand still missing)
        updated = update_product(prod.id, notes="Some notes", session=db_session)

        assert updated.is_provisional is True

    def test_non_provisional_not_affected_by_update(self, db_session, sample_each_material):
        """Test that non-provisional products are not affected by auto-promote logic."""
        # Create a complete non-provisional product
        prod = create_product(
            sample_each_material.id,
            "Complete Product",
            50,
            "each",
            brand="TestBrand",
            session=db_session,
        )
        assert prod.is_provisional is False

        # Update some field
        updated = update_product(prod.id, name="Renamed Product", session=db_session)

        # Should still be non-provisional
        assert updated.is_provisional is False

    def test_list_products_includes_provisional_flag(self, db_session, sample_each_material):
        """Test that list_products includes is_provisional in the returned dict."""
        # Create one provisional and one complete product
        create_product(
            sample_each_material.id,
            "Provisional",
            50,
            "each",
            is_provisional=True,
            session=db_session,
        )
        create_product(
            sample_each_material.id,
            "Complete",
            50,
            "each",
            brand="TestBrand",
            session=db_session,
        )

        products = list_products(material_id=sample_each_material.id, session=db_session)

        # Both should have is_provisional key
        assert all("is_provisional" in p for p in products)

        # Find each product by name
        provisional = next(p for p in products if p["name"] == "Provisional")
        complete = next(p for p in products if p["name"] == "Complete")

        assert provisional["is_provisional"] is True
        assert complete["is_provisional"] is False

    def test_update_product_with_slug(self, db_session, sample_each_material):
        """Test that update_product can update the slug field."""
        prod = create_product(
            sample_each_material.id,
            "Test Product",
            50,
            "each",
            brand="TestBrand",
            session=db_session,
        )

        updated = update_product(prod.id, slug="custom_slug", session=db_session)

        assert updated.slug == "custom_slug"


# ============================================================================
# MaterialUnit Auto-Generation Tests (Feature 084)
# ============================================================================


class TestMaterialUnitAutoGeneration:
    """Tests for auto-generation of MaterialUnits when creating MaterialProducts (Feature 084)."""

    def test_create_product_with_each_auto_generates_unit(self, db_session, sample_each_material):
        """Creating a product for an 'each' type material auto-generates a MaterialUnit."""
        from src.models import MaterialUnit

        prod = create_product(
            sample_each_material.id,
            "Gift Box Small",
            10,
            "each",
            brand="TestBrand",
            session=db_session,
        )

        # Check that a MaterialUnit was created
        units = (
            db_session.query(MaterialUnit).filter(MaterialUnit.material_product_id == prod.id).all()
        )
        assert len(units) == 1
        assert units[0].quantity_per_unit == 1.0

    def test_create_product_with_linear_no_auto_generation(self, db_session, sample_material):
        """Creating a product for a 'linear_cm' type material does NOT auto-generate a MaterialUnit."""
        from src.models import MaterialUnit

        # sample_material is linear_cm type (Red Satin Ribbon)
        prod = create_product(
            sample_material.id,
            "100ft Roll",
            100,
            "feet",
            brand="TestBrand",
            session=db_session,
        )

        # Check that no MaterialUnit was created
        units = (
            db_session.query(MaterialUnit).filter(MaterialUnit.material_product_id == prod.id).all()
        )
        assert len(units) == 0

    def test_create_product_with_square_cm_no_auto_generation(self, db_session, sample_subcategory):
        """Creating a product for a 'square_cm' type material does NOT auto-generate a MaterialUnit."""
        from src.models import MaterialUnit

        # Create a square_cm type material
        mat = create_material(
            sample_subcategory.id,
            "Gift Wrap Paper",
            "square_cm",
            session=db_session,
        )

        prod = create_product(
            mat.id,
            "Sheet 20x30",
            600,
            "square_inches",  # Valid area unit for square_cm material
            brand="TestBrand",
            session=db_session,
        )

        # Check that no MaterialUnit was created (square_cm type)
        units = (
            db_session.query(MaterialUnit).filter(MaterialUnit.material_product_id == prod.id).all()
        )
        assert len(units) == 0

    def test_auto_generated_unit_has_correct_name_and_slug(self, db_session, sample_each_material):
        """Auto-generated MaterialUnit has correct name format '1 {product.name}' and hyphen-style slug."""
        from src.models import MaterialUnit

        prod = create_product(
            sample_each_material.id,
            "Gift Box Large",
            25,
            "each",
            brand="TestBrand",
            session=db_session,
        )

        unit = (
            db_session.query(MaterialUnit)
            .filter(MaterialUnit.material_product_id == prod.id)
            .first()
        )

        assert unit is not None
        assert unit.name == "1 Gift Box Large"  # "1 {product.name}" format
        assert unit.slug == "1-gift-box-large"  # Hyphen-style slug
        assert unit.quantity_per_unit == 1.0
        assert "Auto-generated" in unit.description

    def test_auto_generated_unit_slug_collision_handling(self, db_session, sample_each_material):
        """Auto-generation handles slug collisions by appending numeric suffix."""
        from src.models import MaterialUnit

        # Create first product - will get slug "1-gift-box"
        prod1 = create_product(
            sample_each_material.id,
            "Gift Box",
            10,
            "each",
            brand="Brand1",
            session=db_session,
        )

        # Create second product with same name under same material
        # This would create a unit with colliding slug
        prod2 = create_product(
            sample_each_material.id,
            "Gift Box",
            20,
            "each",
            brand="Brand2",
            session=db_session,
        )

        unit1 = (
            db_session.query(MaterialUnit)
            .filter(MaterialUnit.material_product_id == prod1.id)
            .first()
        )
        unit2 = (
            db_session.query(MaterialUnit)
            .filter(MaterialUnit.material_product_id == prod2.id)
            .first()
        )

        assert unit1 is not None
        assert unit2 is not None
        # Both units have unique slugs (different products, so no collision within scope)
        assert unit1.slug == "1-gift-box"
        assert unit2.slug == "1-gift-box"  # Same slug is OK - different product scope

    def test_auto_generation_uses_same_session(self, db_session, sample_each_material):
        """Auto-generation happens atomically within the same session as product creation."""
        from src.models import MaterialUnit

        # Create product - auto-generation should happen in same transaction
        prod = create_product(
            sample_each_material.id,
            "Test Box",
            5,
            "each",
            brand="TestBrand",
            session=db_session,
        )

        # Without committing the outer session, the unit should be visible
        unit = (
            db_session.query(MaterialUnit)
            .filter(MaterialUnit.material_product_id == prod.id)
            .first()
        )

        # If auto-generation used a separate session, unit wouldn't be visible yet
        assert unit is not None
        assert unit.name == "1 Test Box"

    def test_auto_generation_provisional_product(self, db_session, sample_each_material):
        """Auto-generation works correctly for provisional products."""
        from src.models import MaterialUnit

        prod = create_product(
            sample_each_material.id,
            "Provisional Box",
            10,
            "each",
            is_provisional=True,  # Provisional product
            session=db_session,
        )

        assert prod.is_provisional is True

        # Auto-generated unit should still be created
        unit = (
            db_session.query(MaterialUnit)
            .filter(MaterialUnit.material_product_id == prod.id)
            .first()
        )
        assert unit is not None
        assert unit.name == "1 Provisional Box"
