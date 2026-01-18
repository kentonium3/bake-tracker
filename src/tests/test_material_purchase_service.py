"""Tests for Material Purchase Service.

Tests purchase recording, FIFO inventory creation, and unit conversion
for the Materials Management System (Feature 047, updated for Feature 058 FIFO).

Feature 058 Changes:
- MaterialProduct no longer has current_inventory or weighted_avg_cost fields
- Inventory is tracked via MaterialInventoryItem (FIFO pattern)
- Base unit types changed from imperial (linear_inches) to metric (linear_cm)
- adjust_inventory() is deprecated (raises NotImplementedError)
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services.material_purchase_service import (
    record_purchase,
    adjust_inventory,
    calculate_weighted_average,
    convert_to_base_units,
    get_purchase,
    list_purchases,
    get_product_inventory,
    MaterialProductNotFoundError,
    SupplierNotFoundError,
)
from src.services.material_catalog_service import (
    create_category,
    create_subcategory,
    create_material,
    create_product,
)
from src.services.exceptions import ValidationError
from src.models import Supplier, MaterialInventoryItem


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
def sample_hierarchy(db_session):
    """Create a sample material hierarchy for testing (Feature 058: metric units)."""
    cat = create_category("Ribbons", session=db_session)
    subcat = create_subcategory(cat.id, "Satin", session=db_session)
    # Feature 058: Changed from linear_inches to linear_cm
    mat = create_material(subcat.id, "Red Satin", "linear_cm", session=db_session)
    return {"category": cat, "subcategory": subcat, "material": mat}


@pytest.fixture
def sample_product(db_session, sample_hierarchy, sample_supplier):
    """Create a sample product (100ft roll -> 3048 cm)."""
    prod = create_product(
        material_id=sample_hierarchy["material"].id,
        name="100ft Roll",
        package_quantity=100,
        package_unit="feet",
        brand="Michaels",
        supplier_id=sample_supplier.id,
        session=db_session,
    )
    return prod


@pytest.fixture
def sample_product_each(db_session, sample_supplier):
    """Create a sample 'each' type product."""
    cat = create_category("Boxes", session=db_session)
    subcat = create_subcategory(cat.id, "Small", session=db_session)
    mat = create_material(subcat.id, "Gift Box", "each", session=db_session)
    prod = create_product(
        material_id=mat.id,
        name="6-pack Gift Boxes",
        package_quantity=6,
        package_unit="each",
        supplier_id=sample_supplier.id,
        session=db_session,
    )
    return prod


class TestConvertToBaseUnits:
    """Tests for unit conversion function (Feature 058: metric base units)."""

    def test_convert_feet_to_cm(self):
        """100 feet = 3048 cm (100 * 30.48)."""
        result = convert_to_base_units(100, "feet", "linear_cm")
        assert result == 3048.0

    def test_convert_yards_to_cm(self):
        """50 yards = 4572 cm (50 * 91.44)."""
        result = convert_to_base_units(50, "yards", "linear_cm")
        assert result == 4572.0

    def test_convert_inches_to_cm(self):
        """100 inches = 254 cm (100 * 2.54)."""
        result = convert_to_base_units(100, "inches", "linear_cm")
        assert result == 254.0

    def test_convert_each_type(self):
        """Each type needs no conversion."""
        result = convert_to_base_units(10, "each", "each")
        assert result == 10.0

    def test_convert_square_feet_to_square_cm(self):
        """2 square feet = 1858.0608 square cm."""
        result = convert_to_base_units(2, "square_feet", "square_cm")
        assert abs(result - 1858.0608) < 0.001

    def test_invalid_linear_unit(self):
        """Invalid/incompatible linear unit raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            convert_to_base_units(10, "unknown_unit", "linear_cm")
        assert "not compatible" in str(exc.value)

    def test_invalid_base_unit_type(self):
        """Invalid base_unit_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            convert_to_base_units(10, "feet", "invalid_type")
        assert "Unknown base unit type" in str(exc.value)


class TestWeightedAverageCalculation:
    """Tests for weighted average cost calculation."""

    def test_first_purchase_sets_cost(self):
        """First purchase (no existing inventory) sets initial cost."""
        result = calculate_weighted_average(
            current_quantity=0,
            current_avg_cost=Decimal("0"),
            added_quantity=100,
            added_unit_cost=Decimal("0.15"),
        )
        assert result == Decimal("0.15")

    def test_weighted_average_calculation(self):
        """200 units at $0.12 + 100 units at $0.15 = $0.13."""
        result = calculate_weighted_average(
            current_quantity=200,
            current_avg_cost=Decimal("0.12"),
            added_quantity=100,
            added_unit_cost=Decimal("0.15"),
        )
        assert result == Decimal("0.1300")

    def test_zero_added_unchanged(self):
        """Adding zero quantity doesn't change average."""
        result = calculate_weighted_average(
            current_quantity=200,
            current_avg_cost=Decimal("0.12"),
            added_quantity=0,
            added_unit_cost=Decimal("0.20"),
        )
        assert result == Decimal("0.12")

    def test_equal_quantities_equal_weights(self):
        """Equal quantities give arithmetic mean."""
        result = calculate_weighted_average(
            current_quantity=100,
            current_avg_cost=Decimal("0.10"),
            added_quantity=100,
            added_unit_cost=Decimal("0.20"),
        )
        assert result == Decimal("0.1500")

    def test_large_existing_inventory_dominates(self):
        """Large existing inventory dominates the average."""
        result = calculate_weighted_average(
            current_quantity=1000,
            current_avg_cost=Decimal("0.10"),
            added_quantity=100,
            added_unit_cost=Decimal("0.20"),
        )
        # (1000 * 0.10 + 100 * 0.20) / 1100 = 120 / 1100 = 0.1091
        assert result == Decimal("0.1091")


class TestRecordPurchase:
    """Tests for record_purchase function (Feature 058: FIFO inventory)."""

    def test_first_purchase_creates_record(self, db_session, sample_product, sample_supplier):
        """First purchase creates record and MaterialInventoryItem."""
        purchase = record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("12.00"),
            notes="First order",
            session=db_session,
        )

        assert purchase is not None
        assert purchase.packages_purchased == 2
        assert purchase.package_price == Decimal("12.00")
        # 2 packages * 100 feet * 30.48 cm/foot = 6096 cm
        assert purchase.units_added == 6096.0
        # $24 total / 6096 cm = ~$0.00394/cm
        expected_cost = Decimal("24.00") / Decimal("6096")
        assert abs(float(purchase.unit_cost) - float(expected_cost)) < 0.0001

        # Feature 058: Verify MaterialInventoryItem was created
        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )
        assert inventory_item is not None
        assert inventory_item.quantity_purchased == 6096.0
        assert inventory_item.quantity_remaining == 6096.0

    def test_second_purchase_creates_separate_inventory_item(
        self, db_session, sample_product, sample_supplier
    ):
        """Second purchase creates separate FIFO lot (Feature 058)."""
        # First purchase: 6096 cm
        purchase1 = record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today() - timedelta(days=7),
            packages_purchased=2,
            package_price=Decimal("12.00"),
            session=db_session,
        )

        # Second purchase: 3048 cm at different price
        purchase2 = record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("18.00"),
            session=db_session,
        )

        # Feature 058: Verify separate inventory items
        items = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_product_id=sample_product.id)
            .order_by(MaterialInventoryItem.purchase_date)
            .all()
        )
        assert len(items) == 2
        assert items[0].material_purchase_id == purchase1.id
        assert items[1].material_purchase_id == purchase2.id

        # Each has its own cost
        assert items[0].cost_per_unit != items[1].cost_per_unit

    def test_purchase_each_type_product(self, db_session, sample_product_each, sample_supplier):
        """Purchase of 'each' type product works correctly."""
        purchase = record_purchase(
            product_id=sample_product_each.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=3,  # 3 packs of 6 = 18 units
            package_price=Decimal("9.00"),  # $9 per pack
            session=db_session,
        )

        assert purchase.units_added == 18.0
        # $27 total / 18 units = $1.50/unit
        assert purchase.unit_cost == Decimal("1.5000")

        # Feature 058: Verify MaterialInventoryItem
        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )
        assert inventory_item is not None
        assert inventory_item.quantity_remaining == 18.0
        assert inventory_item.cost_per_unit == Decimal("1.5000")

    def test_purchase_invalid_product(self, db_session, sample_supplier):
        """Purchase with invalid product raises error."""
        with pytest.raises(MaterialProductNotFoundError) as exc:
            record_purchase(
                product_id=99999,
                supplier_id=sample_supplier.id,
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("10.00"),
                session=db_session,
            )
        assert "99999" in str(exc.value)

    def test_purchase_invalid_supplier(self, db_session, sample_product):
        """Purchase with invalid supplier raises error."""
        with pytest.raises(SupplierNotFoundError) as exc:
            record_purchase(
                product_id=sample_product.id,
                supplier_id=99999,
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("10.00"),
                session=db_session,
            )
        assert "99999" in str(exc.value)

    def test_purchase_zero_packages(self, db_session, sample_product, sample_supplier):
        """Purchase with zero packages raises error."""
        with pytest.raises(ValidationError) as exc:
            record_purchase(
                product_id=sample_product.id,
                supplier_id=sample_supplier.id,
                purchase_date=date.today(),
                packages_purchased=0,
                package_price=Decimal("10.00"),
                session=db_session,
            )
        assert "positive" in str(exc.value)

    def test_purchase_negative_packages(self, db_session, sample_product, sample_supplier):
        """Purchase with negative packages raises error."""
        with pytest.raises(ValidationError) as exc:
            record_purchase(
                product_id=sample_product.id,
                supplier_id=sample_supplier.id,
                purchase_date=date.today(),
                packages_purchased=-1,
                package_price=Decimal("10.00"),
                session=db_session,
            )
        assert "positive" in str(exc.value)

    def test_purchase_negative_price(self, db_session, sample_product, sample_supplier):
        """Purchase with negative price raises error."""
        with pytest.raises(ValidationError) as exc:
            record_purchase(
                product_id=sample_product.id,
                supplier_id=sample_supplier.id,
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("-10.00"),
                session=db_session,
            )
        assert "negative" in str(exc.value)

    def test_purchase_zero_price_allowed(self, db_session, sample_product, sample_supplier):
        """Purchase with zero price (free/donation) is allowed."""
        purchase = record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("0.00"),
            notes="Donation",
            session=db_session,
        )
        assert purchase.package_price == Decimal("0.00")


class TestAdjustInventory:
    """Tests for adjust_inventory function.

    Feature 058: adjust_inventory is DEPRECATED. MaterialProduct no longer
    tracks current_inventory or weighted_avg_cost. Inventory adjustments
    should be done via MaterialInventoryItem operations.
    """

    def test_adjust_raises_not_implemented(self, db_session, sample_product):
        """Feature 058: adjust_inventory raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc:
            adjust_inventory(
                product_id=sample_product.id,
                new_quantity=100,
                session=db_session,
            )
        assert "DEPRECATED" in str(exc.value)
        assert "Feature 058" in str(exc.value)


class TestGetPurchase:
    """Tests for get_purchase function."""

    def test_get_existing_purchase(self, db_session, sample_product, sample_supplier):
        """Get an existing purchase by ID."""
        created = record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("12.00"),
            session=db_session,
        )

        retrieved = get_purchase(created.id, session=db_session)
        assert retrieved.id == created.id
        assert retrieved.packages_purchased == 1

    def test_get_nonexistent_purchase(self, db_session):
        """Get nonexistent purchase raises error."""
        with pytest.raises(ValidationError) as exc:
            get_purchase(99999, session=db_session)
        assert "not found" in str(exc.value)


class TestListPurchases:
    """Tests for list_purchases function."""

    def test_list_all_purchases(self, db_session, sample_product, sample_supplier):
        """List all purchases returns all records."""
        record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today() - timedelta(days=2),
            packages_purchased=1,
            package_price=Decimal("12.00"),
            session=db_session,
        )
        record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("24.00"),
            session=db_session,
        )

        purchases = list_purchases(session=db_session)
        assert len(purchases) == 2
        # Most recent first
        assert purchases[0].packages_purchased == 2

    def test_list_by_product(self, db_session, sample_product, sample_product_each, sample_supplier):
        """List purchases filtered by product."""
        record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("12.00"),
            session=db_session,
        )
        record_purchase(
            product_id=sample_product_each.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("18.00"),
            session=db_session,
        )

        ribbon_purchases = list_purchases(product_id=sample_product.id, session=db_session)
        assert len(ribbon_purchases) == 1

    def test_list_by_date_range(self, db_session, sample_product, sample_supplier):
        """List purchases filtered by date range."""
        record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today() - timedelta(days=10),
            packages_purchased=1,
            package_price=Decimal("12.00"),
            session=db_session,
        )
        record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("24.00"),
            session=db_session,
        )

        recent = list_purchases(
            start_date=date.today() - timedelta(days=5),
            session=db_session,
        )
        assert len(recent) == 1
        assert recent[0].packages_purchased == 2

    def test_list_with_limit(self, db_session, sample_product, sample_supplier):
        """List purchases with limit."""
        for i in range(5):
            record_purchase(
                product_id=sample_product.id,
                supplier_id=sample_supplier.id,
                purchase_date=date.today() - timedelta(days=i),
                packages_purchased=i + 1,
                package_price=Decimal("12.00"),
                session=db_session,
            )

        limited = list_purchases(limit=3, session=db_session)
        assert len(limited) == 3


class TestGetProductInventory:
    """Tests for get_product_inventory function (Feature 058: FIFO aggregation)."""

    def test_get_inventory_details(self, db_session, sample_product, sample_supplier):
        """Get detailed inventory aggregated from FIFO lots."""
        record_purchase(
            product_id=sample_product.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("12.00"),
            session=db_session,
        )

        info = get_product_inventory(sample_product.id, session=db_session)
        assert info["product_id"] == sample_product.id
        # 2 packages * 100 feet * 30.48 cm/foot = 6096 cm
        assert info["current_inventory"] == 6096.0
        # Feature 058: Changed from linear_inches to linear_cm
        assert info["base_unit_type"] == "linear_cm"
        # Feature 058: New field showing number of FIFO lots
        assert info["inventory_lots"] == 1

    def test_get_inventory_nonexistent_product(self, db_session):
        """Get inventory for nonexistent product raises error."""
        with pytest.raises(MaterialProductNotFoundError):
            get_product_inventory(99999, session=db_session)
