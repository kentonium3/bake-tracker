"""
Tests for Event Service Packaging Extensions (Feature 011).

Tests cover:
- get_event_packaging_needs() functionality
- _aggregate_packaging() helper
- _get_packaging_on_hand() helper
- get_shopping_list() packaging integration
- get_event_packaging_breakdown() functionality
- Empty packaging scenarios
"""

import pytest
from datetime import date
from decimal import Decimal

from src.services.event_service import (
    EventNotFoundError,
    PackagingNeed,
    PackagingSource,
    create_event,
    get_event_packaging_needs,
    get_event_packaging_breakdown,
    get_shopping_list,
    assign_package_to_recipient,
)
from src.services.composition_service import (
    add_packaging_to_assembly,
    add_packaging_to_package,
)
from src.services.ingredient_service import create_ingredient
from src.services.product_service import create_product
from src.models import (
    FinishedGood,
    Package,
    Recipient,
    InventoryItem,
)
from src.models.assembly_type import AssemblyType

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def packaging_ingredient(test_db):
    """Create a packaging ingredient for tests."""
    return create_ingredient(
        {
            "display_name": "Test Cellophane Bags",
            "category": "Bags",
        }
    )


@pytest.fixture
def packaging_ingredient_2(test_db):
    """Create a second packaging ingredient for tests."""
    return create_ingredient(
        {
            "display_name": "Test Gift Boxes",
            "category": "Boxes",
        }
    )


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
        },
    )


@pytest.fixture
def packaging_product_2(test_db, packaging_ingredient_2):
    """Create a second packaging product for tests."""
    return create_product(
        packaging_ingredient_2.slug,
        {
            "brand": "Kraft",
            "package_size": "6 pack",
            "package_unit": "each",
            "package_unit_quantity": 6,
        },
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


@pytest.fixture
def recipient(test_db):
    """Create a recipient for tests."""
    rec = Recipient(
        name="Test Recipient",
    )
    test_db.add(rec)
    test_db.flush()
    return rec


@pytest.fixture
def event(test_db):
    """Create an event for tests."""
    return create_event(
        name="Test Holiday Event",
        event_date=date(2024, 12, 25),
        year=2024,
    )


# =============================================================================
# Test: get_event_packaging_needs
# =============================================================================


class TestGetEventPackagingNeeds:
    """Tests for get_event_packaging_needs() functionality."""

    def test_get_packaging_needs_empty_event(self, test_db, event):
        """Event with no packages returns empty needs."""
        needs = get_event_packaging_needs(event.id)
        assert needs == {}

    def test_get_packaging_needs_nonexistent_event(self, test_db):
        """Nonexistent event raises EventNotFoundError."""
        with pytest.raises(EventNotFoundError):
            get_event_packaging_needs(999999)

    def test_get_packaging_needs_from_package_level(
        self, test_db, event, package, recipient, packaging_product
    ):
        """Package-level packaging is aggregated correctly."""
        from src.models import PackageFinishedGood

        # Add packaging to package
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=2.0,
        )

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=3,  # 3 packages
        )

        needs = get_event_packaging_needs(event.id)

        # Feature 026: Keys are now "specific_{product_id}" for specific products
        key = f"specific_{packaging_product.id}"
        assert key in needs
        need = needs[key]
        assert isinstance(need, PackagingNeed)
        assert need.total_needed == 6.0  # 2.0 per package * 3 packages
        assert need.product_id == packaging_product.id
        assert need.is_generic is False

    def test_get_packaging_needs_from_finished_good_level(
        self, test_db, event, package, finished_good, recipient, packaging_product
    ):
        """FinishedGood-level packaging is aggregated correctly."""
        from src.models import PackageFinishedGood

        # Add packaging to finished good
        add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.5,
        )

        # Add finished good to package
        pfg = PackageFinishedGood(
            package_id=package.id,
            finished_good_id=finished_good.id,
            quantity=2,  # 2 finished goods per package
        )
        test_db.add(pfg)
        test_db.flush()

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=4,  # 4 packages
        )

        needs = get_event_packaging_needs(event.id)

        # Feature 026: Keys are now "specific_{product_id}" for specific products
        key = f"specific_{packaging_product.id}"
        assert key in needs
        need = needs[key]
        # 1.5 per FG * 2 FGs per package * 4 packages = 12.0
        assert need.total_needed == 12.0
        assert need.is_generic is False

    def test_get_packaging_needs_aggregates_both_levels(
        self, test_db, event, package, finished_good, recipient, packaging_product
    ):
        """Packaging from both Package and FinishedGood levels is aggregated."""
        from src.models import PackageFinishedGood

        # Add packaging to package (2.0 per package)
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=2.0,
        )

        # Add packaging to finished good (1.0 per FG)
        add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        # Add finished good to package (2 FGs per package)
        pfg = PackageFinishedGood(
            package_id=package.id,
            finished_good_id=finished_good.id,
            quantity=2,
        )
        test_db.add(pfg)
        test_db.flush()

        # Assign package to event (3 packages)
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=3,
        )

        needs = get_event_packaging_needs(event.id)

        # Feature 026: Keys are now "specific_{product_id}" for specific products
        key = f"specific_{packaging_product.id}"
        assert key in needs
        need = needs[key]
        # Package-level: 2.0 * 3 = 6.0
        # FG-level: 1.0 * 2 FGs * 3 packages = 6.0
        # Total: 12.0
        assert need.total_needed == 12.0
        assert need.is_generic is False

    def test_get_packaging_needs_multiple_products(
        self,
        test_db,
        event,
        package,
        recipient,
        packaging_product,
        packaging_product_2,
    ):
        """Multiple packaging products are tracked separately."""
        # Add first packaging to package
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=1.0,
        )

        # Add second packaging to package
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product_2.id,
            quantity=2.0,
        )

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=5,
        )

        needs = get_event_packaging_needs(event.id)

        # Feature 026: Keys are now "specific_{product_id}" for specific products
        assert len(needs) == 2
        key1 = f"specific_{packaging_product.id}"
        key2 = f"specific_{packaging_product_2.id}"
        assert needs[key1].total_needed == 5.0
        assert needs[key2].total_needed == 10.0

    def test_get_packaging_needs_with_inventory(
        self, test_db, event, package, recipient, packaging_product
    ):
        """On-hand inventory is subtracted from total needed."""
        # Add packaging to package
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=10.0,
        )

        # Add inventory for the product
        inv = InventoryItem(
            product_id=packaging_product.id,
            quantity=6.0,
        )
        test_db.add(inv)
        test_db.flush()

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=1,
        )

        needs = get_event_packaging_needs(event.id)

        # Feature 026: Keys are now "specific_{product_id}" for specific products
        key = f"specific_{packaging_product.id}"
        assert key in needs
        need = needs[key]
        assert need.total_needed == 10.0
        assert need.on_hand == 6.0
        assert need.to_buy == 4.0

    def test_get_packaging_needs_to_buy_never_negative(
        self, test_db, event, package, recipient, packaging_product
    ):
        """to_buy is never negative even if on_hand exceeds needed."""
        # Add packaging to package
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=5.0,
        )

        # Add more inventory than needed
        inv = InventoryItem(
            product_id=packaging_product.id,
            quantity=20.0,
        )
        test_db.add(inv)
        test_db.flush()

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=1,
        )

        needs = get_event_packaging_needs(event.id)

        # Feature 026: Keys are now "specific_{product_id}" for specific products
        key = f"specific_{packaging_product.id}"
        need = needs[key]
        assert need.total_needed == 5.0
        assert need.on_hand == 20.0
        assert need.to_buy == 0.0  # Never negative


# =============================================================================
# Test: get_shopping_list with packaging
# =============================================================================


class TestGetShoppingListPackaging:
    """Tests for get_shopping_list() packaging integration."""

    def test_shopping_list_includes_packaging_section(
        self, test_db, event, package, recipient, packaging_product
    ):
        """Shopping list includes packaging section when packaging exists."""
        # Add packaging to package
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=3.0,
        )

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=2,
        )

        result = get_shopping_list(event.id)

        assert "packaging" in result
        assert len(result["packaging"]) == 1
        pkg_item = result["packaging"][0]
        assert pkg_item["product_id"] == packaging_product.id
        assert pkg_item["total_needed"] == 6.0  # 3.0 * 2 packages

    def test_shopping_list_no_packaging_section_when_empty(self, test_db, event):
        """Shopping list omits packaging section when no packaging needed."""
        result = get_shopping_list(event.id)

        # packaging key should not be present
        assert "packaging" not in result

    def test_shopping_list_exclude_packaging_parameter(
        self, test_db, event, package, recipient, packaging_product
    ):
        """include_packaging=False omits packaging section."""
        # Add packaging to package
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=3.0,
        )

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=2,
        )

        result = get_shopping_list(event.id, include_packaging=False)

        assert "packaging" not in result


# =============================================================================
# Test: get_event_packaging_breakdown
# =============================================================================


class TestGetEventPackagingBreakdown:
    """Tests for get_event_packaging_breakdown() functionality."""

    def test_breakdown_empty_event(self, test_db, event):
        """Event with no packages returns empty breakdown."""
        breakdown = get_event_packaging_breakdown(event.id)
        assert breakdown == {}

    def test_breakdown_nonexistent_event(self, test_db):
        """Nonexistent event raises EventNotFoundError."""
        with pytest.raises(EventNotFoundError):
            get_event_packaging_breakdown(999999)

    def test_breakdown_shows_package_sources(
        self, test_db, event, package, recipient, packaging_product
    ):
        """Breakdown shows package-level sources correctly."""
        # Add packaging to package
        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=packaging_product.id,
            quantity=4.0,
        )

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=2,
        )

        breakdown = get_event_packaging_breakdown(event.id)

        assert packaging_product.id in breakdown
        sources = breakdown[packaging_product.id]
        assert len(sources) == 1
        source = sources[0]
        assert isinstance(source, PackagingSource)
        assert source.source_type == "package"
        assert source.source_id == package.id
        assert source.quantity_per == 4.0
        assert source.source_count == 2
        assert source.total_for_source == 8.0

    def test_breakdown_shows_finished_good_sources(
        self, test_db, event, package, finished_good, recipient, packaging_product
    ):
        """Breakdown shows FinishedGood-level sources correctly."""
        from src.models import PackageFinishedGood

        # Add packaging to finished good
        add_packaging_to_assembly(
            assembly_id=finished_good.id,
            packaging_product_id=packaging_product.id,
            quantity=2.0,
        )

        # Add finished good to package
        pfg = PackageFinishedGood(
            package_id=package.id,
            finished_good_id=finished_good.id,
            quantity=3,
        )
        test_db.add(pfg)
        test_db.flush()

        # Assign package to event
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=2,
        )

        breakdown = get_event_packaging_breakdown(event.id)

        assert packaging_product.id in breakdown
        sources = breakdown[packaging_product.id]
        assert len(sources) == 1
        source = sources[0]
        assert source.source_type == "finished_good"
        assert source.source_id == finished_good.id
        assert source.quantity_per == 2.0
        # source_count = 3 FGs per package * 2 packages = 6
        assert source.source_count == 6
        assert source.total_for_source == 12.0  # 2.0 * 6
