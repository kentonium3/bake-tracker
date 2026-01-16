"""
Tests for Composition Service - Packaging Extensions (Feature 011).

Tests cover:
- add_packaging_to_assembly() functionality
- add_packaging_to_package() functionality
- get_assembly_packaging() filtering
- get_package_packaging() filtering
- update_packaging_quantity() with decimals
- remove_packaging() functionality
- Packaging product validation
- Duplicate prevention
"""

import pytest

from src.services.composition_service import (
    CompositionService,
    add_packaging_to_assembly,
    add_packaging_to_package,
    get_assembly_packaging,
    get_package_packaging,
    update_packaging_quantity,
    remove_packaging,
    get_packaging_product_usage_count,
    DuplicateCompositionError,
)
from src.services.exceptions import ValidationError
from src.services.ingredient_service import create_ingredient
from src.services.product_service import create_product
from src.models import FinishedGood, Package, Composition, Ingredient
from src.models.assembly_type import AssemblyType

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def packaging_ingredient(test_db):
    """Create a packaging ingredient for tests."""
    return create_ingredient({
        "display_name": "Test Cellophane Bags",
        "category": "Bags",
    })

@pytest.fixture
def food_ingredient(test_db):
    """Create a food ingredient for tests."""
    return create_ingredient({
        "display_name": "Test All-Purpose Flour",
        "category": "Flour",
    })

@pytest.fixture
def packaging_product(test_db, packaging_ingredient):
    """Create a packaging product for tests."""
    return create_product(
        packaging_ingredient.slug,
        {
            "brand": "Amazon Basics",
            "package_size": "100ct",
            "package_unit": "box",
            "package_unit_quantity": 100,
        }
    )

@pytest.fixture
def food_product(test_db, food_ingredient):
    """Create a food product for tests."""
    return create_product(
        food_ingredient.slug,
        {
            "brand": "King Arthur",
            "package_size": "5 lb",
            "package_unit": "lb",
            "package_unit_quantity": 5,
        }
    )

@pytest.fixture
def finished_good(test_db):
    """Create a finished good assembly for tests."""
    fg = FinishedGood(
        slug="test-cookie-dozen",
        display_name="Test Cookie Dozen",
        description="A dozen test cookies",
        assembly_type=AssemblyType.CUSTOM_ORDER,
        inventory_count=0,
    )
    test_db.add(fg)
    test_db.flush()
    return fg

@pytest.fixture
def package(test_db):
    """Create a package for tests."""
    pkg = Package(
        name="Test Gift Box",
        description="A test gift box",
    )
    test_db.add(pkg)
    test_db.flush()
    return pkg

# =============================================================================
# Test: add_packaging_to_assembly
# =============================================================================

class TestAddPackagingToAssembly:
    """Tests for add_packaging_to_assembly() functionality."""

    def test_add_packaging_to_assembly_success(self, test_db, finished_good, packaging_product):
        """Successfully add packaging product to assembly."""
        composition = add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=2.5,
        )

        assert composition.assembly_id == finished_good.id
        assert composition.packaging_product_id == packaging_product.id
        assert composition.component_quantity == 2.5
        assert composition.package_id is None
        assert composition.finished_unit_id is None
        assert composition.finished_good_id is None

    def test_add_packaging_to_assembly_with_notes(self, test_db, finished_good, packaging_product):
        """Add packaging with notes and sort_order."""
        composition = add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
            notes="Use clear bags only",
            sort_order=5,
        )

        assert composition.component_notes == "Use clear bags only"
        assert composition.sort_order == 5

    def test_add_packaging_to_assembly_rejects_invalid_assembly(self, test_db, packaging_product):
        """Reject adding to non-existent assembly."""
        with pytest.raises(ValidationError) as excinfo:
            add_packaging_to_assembly(
                assembly_id=999999,
                packaging_product_id=packaging_product.id,
                quantity=1.0,
            )
        assert "not found" in str(excinfo.value)

    def test_add_packaging_to_assembly_rejects_zero_quantity(
        self, test_db, finished_good, packaging_product
    ):
        """Reject zero quantity."""
        with pytest.raises(ValidationError) as excinfo:
            add_packaging_to_assembly(
                assembly_id=finished_good.id,
                packaging_product_id=packaging_product.id,
                quantity=0,
            )
        assert "greater than 0" in str(excinfo.value)

    def test_add_packaging_to_assembly_rejects_negative_quantity(
        self, test_db, finished_good, packaging_product
    ):
        """Reject negative quantity."""
        with pytest.raises(ValidationError) as excinfo:
            add_packaging_to_assembly(
                assembly_id=finished_good.id,
                packaging_product_id=packaging_product.id,
                quantity=-1.0,
            )
        assert "greater than 0" in str(excinfo.value)

    def test_add_packaging_to_assembly_rejects_duplicate(
        self, test_db, finished_good, packaging_product
    ):
        """Reject adding same packaging product twice."""
        # Add first time
        add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        # Try to add again
        with pytest.raises(DuplicateCompositionError) as excinfo:
            add_packaging_to_assembly(
                assembly_id=finished_good.id,
                packaging_product_id=packaging_product.id,
                quantity=2.0,
            )
        assert "already exists" in str(excinfo.value)

# =============================================================================
# Test: add_packaging_to_package
# =============================================================================

class TestAddPackagingToPackage:
    """Tests for add_packaging_to_package() functionality."""

    def test_add_packaging_to_package_success(self, test_db, package, packaging_product):
        """Successfully add packaging product to package."""
        composition = add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=3.5,
        )

        assert composition.package_id == package.id
        assert composition.packaging_product_id == packaging_product.id
        assert composition.component_quantity == 3.5
        assert composition.assembly_id is None

    def test_add_packaging_to_package_rejects_invalid_package(self, test_db, packaging_product):
        """Reject adding to non-existent package."""
        with pytest.raises(ValidationError) as excinfo:
            add_packaging_to_package(
                package_id=999999,
                packaging_product_id=packaging_product.id,
                quantity=1.0,
            )
        assert "not found" in str(excinfo.value)

    def test_add_packaging_to_package_rejects_duplicate(self, test_db, package, packaging_product):
        """Reject adding same packaging product twice."""
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        with pytest.raises(DuplicateCompositionError):
            add_packaging_to_package(
                package_id=package.id,
                packaging_product_id=packaging_product.id,
                quantity=2.0,
            )

# =============================================================================
# Test: get_assembly_packaging / get_package_packaging
# =============================================================================

class TestGetPackaging:
    """Tests for packaging retrieval methods."""

    def test_get_assembly_packaging_returns_only_packaging(
        self, test_db, finished_good, packaging_product
    ):
        """get_assembly_packaging returns only packaging compositions."""
        # Add packaging
        add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        results = get_assembly_packaging(finished_good.id)

        assert len(results) == 1
        assert results[0].packaging_product_id == packaging_product.id

    def test_get_assembly_packaging_empty_when_none(self, test_db, finished_good):
        """get_assembly_packaging returns empty list when no packaging."""
        results = get_assembly_packaging(finished_good.id)
        assert len(results) == 0

    def test_get_package_packaging_returns_only_packaging(
        self, test_db, package, packaging_product
    ):
        """get_package_packaging returns only packaging compositions."""
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        results = get_package_packaging(package.id)

        assert len(results) == 1
        assert results[0].packaging_product_id == packaging_product.id

    def test_get_packaging_sorted_by_sort_order(self, test_db, finished_good):
        """Packaging compositions are sorted by sort_order."""
        # Create multiple packaging ingredients
        ing1 = create_ingredient({
            "display_name": "Test Ribbon",
            "category": "Ribbon",
        })
        ing2 = create_ingredient({
            "display_name": "Test Labels",
            "category": "Labels",
        })

        prod1 = create_product(
            ing1.slug,
            {
                "brand": "Test Brand",
                "package_size": "1 roll",
                "package_unit": "each",
                "package_unit_quantity": 1,
            }
        )
        prod2 = create_product(
            ing2.slug,
            {
                "brand": "Test Brand",
                "package_size": "50 ct",
                "package_unit": "box",
                "package_unit_quantity": 50,
            }
        )

        # Add in reverse order
        add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=prod2.id,
            quantity=1.0,
            sort_order=10,
        )
        add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=prod1.id,
            quantity=1.0,
            sort_order=5,
        )

        results = get_assembly_packaging(finished_good.id)

        assert len(results) == 2
        assert results[0].sort_order == 5
        assert results[1].sort_order == 10

# =============================================================================
# Test: update_packaging_quantity
# =============================================================================

class TestUpdatePackagingQuantity:
    """Tests for update_packaging_quantity() functionality."""

    def test_update_packaging_quantity_success(
        self, test_db, finished_good, packaging_product
    ):
        """Successfully update packaging quantity."""
        composition = add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        updated = update_packaging_quantity(composition.id, 5.5)

        assert updated.component_quantity == 5.5

    def test_update_packaging_quantity_supports_decimals(
        self, test_db, finished_good, packaging_product
    ):
        """Update supports decimal quantities."""
        composition = add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        updated = update_packaging_quantity(composition.id, 0.25)

        assert updated.component_quantity == 0.25

    def test_update_packaging_quantity_rejects_zero(
        self, test_db, finished_good, packaging_product
    ):
        """Reject zero quantity in update."""
        composition = add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        with pytest.raises(ValidationError) as excinfo:
            update_packaging_quantity(composition.id, 0)
        assert "greater than 0" in str(excinfo.value)

    def test_update_packaging_quantity_rejects_nonexistent(self, test_db):
        """Reject update for non-existent composition."""
        with pytest.raises(ValidationError):
            update_packaging_quantity(999999, 1.0)

# =============================================================================
# Test: remove_packaging
# =============================================================================

class TestRemovePackaging:
    """Tests for remove_packaging() functionality."""

    def test_remove_packaging_success(self, test_db, finished_good, packaging_product):
        """Successfully remove packaging composition."""
        composition = add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        result = remove_packaging(composition.id)

        assert result is True

        # Verify it's gone
        results = get_assembly_packaging(finished_good.id)
        assert len(results) == 0

    def test_remove_packaging_returns_false_for_nonexistent(self, test_db):
        """Return False for non-existent composition."""
        result = remove_packaging(999999)
        assert result is False

# =============================================================================
# Test: get_packaging_product_usage_count
# =============================================================================

class TestGetPackagingProductUsageCount:
    """Tests for get_packaging_product_usage_count() functionality."""

    def test_get_usage_count_with_usages(
        self, test_db, finished_good, package, packaging_product
    ):
        """Count includes usages in both assemblies and packages."""
        add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        count = get_packaging_product_usage_count(packaging_product.id)

        assert count == 2

    def test_get_usage_count_zero_when_unused(self, test_db, packaging_product):
        """Return 0 for unused product."""
        count = get_packaging_product_usage_count(packaging_product.id)
        assert count == 0
