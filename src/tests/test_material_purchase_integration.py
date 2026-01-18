"""Tests for Material Purchase Integration with FIFO Inventory.

Tests for Feature 058: Materials FIFO Foundation - WP07 Purchase Integration.

These tests verify:
- MaterialInventoryItem creation on purchase (atomic)
- Unit conversion from package units to metric base units
- FIFO inventory tracking through purchase records
- Cost per unit calculation in base units
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services.material_purchase_service import (
    record_purchase,
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
def sample_hierarchy_linear_cm(db_session):
    """Create a sample material hierarchy with linear_cm base units."""
    cat = create_category("Ribbons", session=db_session)
    subcat = create_subcategory(cat.id, "Satin", session=db_session)
    mat = create_material(subcat.id, "Red Satin", "linear_cm", session=db_session)
    return {"category": cat, "subcategory": subcat, "material": mat}


@pytest.fixture
def sample_product_feet(db_session, sample_hierarchy_linear_cm, sample_supplier):
    """Create a sample product sold in feet (100ft roll -> linear_cm base)."""
    prod = create_product(
        material_id=sample_hierarchy_linear_cm["material"].id,
        name="100ft Roll",
        package_quantity=100,
        package_unit="feet",
        brand="Michaels",
        supplier_id=sample_supplier.id,
        session=db_session,
    )
    return prod


@pytest.fixture
def sample_hierarchy_each(db_session):
    """Create a sample material hierarchy with each base units."""
    cat = create_category("Boxes", session=db_session)
    subcat = create_subcategory(cat.id, "Small", session=db_session)
    mat = create_material(subcat.id, "Gift Box", "each", session=db_session)
    return {"category": cat, "subcategory": subcat, "material": mat}


@pytest.fixture
def sample_product_each(db_session, sample_hierarchy_each, sample_supplier):
    """Create a sample 'each' type product (6-pack)."""
    prod = create_product(
        material_id=sample_hierarchy_each["material"].id,
        name="6-pack Gift Boxes",
        package_quantity=6,
        package_unit="each",
        supplier_id=sample_supplier.id,
        session=db_session,
    )
    return prod


@pytest.fixture
def sample_hierarchy_square_cm(db_session):
    """Create a sample material hierarchy with square_cm base units."""
    cat = create_category("Paper", session=db_session)
    subcat = create_subcategory(cat.id, "Wrapping", session=db_session)
    mat = create_material(subcat.id, "Gift Wrap", "square_cm", session=db_session)
    return {"category": cat, "subcategory": subcat, "material": mat}


@pytest.fixture
def sample_product_sq_feet(db_session, sample_hierarchy_square_cm, sample_supplier):
    """Create a sample product sold in square feet."""
    prod = create_product(
        material_id=sample_hierarchy_square_cm["material"].id,
        name="25 sq ft Roll",
        package_quantity=25,
        package_unit="square_feet",
        supplier_id=sample_supplier.id,
        session=db_session,
    )
    return prod


# ============================================================================
# Unit Conversion Tests (Feature 058: Metric Base Units)
# ============================================================================


class TestUnitConversionMetric:
    """Tests for unit conversion to metric base units."""

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

    def test_convert_cm_to_cm(self):
        """cm to cm is identity."""
        result = convert_to_base_units(100, "cm", "linear_cm")
        assert result == 100.0

    def test_convert_each_type(self):
        """Each type needs no conversion."""
        result = convert_to_base_units(10, "each", "each")
        assert result == 10.0

    def test_convert_square_feet_to_square_cm(self):
        """1 square foot = 929.0304 square cm."""
        result = convert_to_base_units(2, "square_feet", "square_cm")
        assert abs(result - 1858.0608) < 0.001

    def test_invalid_linear_unit(self):
        """Invalid linear unit raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            convert_to_base_units(10, "invalid_unit", "linear_cm")
        assert "not compatible" in str(exc.value)

    def test_incompatible_unit_types(self):
        """Linear unit to area base type raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            convert_to_base_units(10, "feet", "square_cm")
        assert "not compatible" in str(exc.value)


# ============================================================================
# Purchase Creates MaterialInventoryItem Tests (T029)
# ============================================================================


class TestPurchaseCreatesInventoryItem:
    """Test that purchase creates MaterialInventoryItem atomically."""

    def test_first_purchase_creates_inventory_item(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """First purchase creates a MaterialInventoryItem record."""
        purchase = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("15.00"),
            notes="First order",
            session=db_session,
        )

        # Verify purchase was created
        assert purchase is not None
        assert purchase.packages_purchased == 2
        assert purchase.package_price == Decimal("15.00")

        # Verify inventory item was created
        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )
        assert inventory_item is not None
        assert inventory_item.material_product_id == sample_product_feet.id
        assert inventory_item.purchase_date == date.today()

    def test_purchase_inventory_item_has_correct_quantity(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """MaterialInventoryItem has correct quantity in base units (cm)."""
        # 2 packages * 100 feet/package = 200 feet = 6096 cm
        purchase = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("15.00"),
            session=db_session,
        )

        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )

        # 200 feet * 30.48 cm/foot = 6096 cm
        expected_qty = 200 * 30.48
        assert inventory_item.quantity_purchased == expected_qty
        assert inventory_item.quantity_remaining == expected_qty

    def test_purchase_inventory_item_has_correct_cost(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """MaterialInventoryItem has correct cost per base unit."""
        # 2 packages @ $15 each = $30 total
        # 200 feet = 6096 cm
        # Cost per cm = $30 / 6096 = ~$0.00492/cm
        purchase = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("15.00"),
            session=db_session,
        )

        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )

        # $30 / 6096 cm = ~0.00492126 $/cm
        expected_qty = 200 * 30.48  # 6096 cm
        expected_cost = Decimal("30.00") / Decimal(str(expected_qty))

        # Compare with small tolerance for decimal precision
        assert abs(float(inventory_item.cost_per_unit) - float(expected_cost)) < 0.0001

    def test_purchase_record_has_converted_units(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """MaterialPurchase record stores units in base units (cm)."""
        purchase = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("15.00"),
            session=db_session,
        )

        # 1 package * 100 feet = 100 feet = 3048 cm
        expected_units = 100 * 30.48
        assert purchase.units_added == expected_units

    def test_multiple_purchases_create_multiple_inventory_items(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """Each purchase creates its own inventory item (FIFO lots)."""
        # First purchase
        purchase1 = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today() - timedelta(days=7),
            packages_purchased=1,
            package_price=Decimal("12.00"),
            session=db_session,
        )

        # Second purchase at different price
        purchase2 = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("15.00"),
            session=db_session,
        )

        # Check inventory items
        items = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_product_id=sample_product_feet.id)
            .order_by(MaterialInventoryItem.purchase_date)
            .all()
        )

        assert len(items) == 2
        assert items[0].material_purchase_id == purchase1.id
        assert items[1].material_purchase_id == purchase2.id

        # Each has its own cost per unit
        assert items[0].cost_per_unit != items[1].cost_per_unit


# ============================================================================
# Each Type Product Tests (T029)
# ============================================================================


class TestEachTypeProductPurchase:
    """Test purchases of 'each' type products."""

    def test_each_type_purchase_creates_inventory_item(
        self, db_session, sample_product_each, sample_supplier
    ):
        """Each type purchase creates inventory item with correct quantity."""
        # 3 packages of 6 = 18 units
        purchase = record_purchase(
            product_id=sample_product_each.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=3,
            package_price=Decimal("9.00"),  # $9 per pack
            session=db_session,
        )

        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )

        assert inventory_item is not None
        assert inventory_item.quantity_purchased == 18.0  # 3 * 6
        assert inventory_item.quantity_remaining == 18.0

        # Cost: $27 total / 18 units = $1.50/unit
        expected_cost = Decimal("27.00") / Decimal("18")
        assert inventory_item.cost_per_unit == expected_cost


# ============================================================================
# Area Type Product Tests (T029)
# ============================================================================


class TestAreaTypeProductPurchase:
    """Test purchases of area type products (square_cm base)."""

    def test_sq_feet_to_sq_cm_conversion(
        self, db_session, sample_product_sq_feet, sample_supplier
    ):
        """Square feet purchase converts to square cm correctly."""
        # 2 packages of 25 sq ft = 50 sq ft
        # 50 sq ft * 929.0304 sq cm/sq ft = 46451.52 sq cm
        purchase = record_purchase(
            product_id=sample_product_sq_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("8.00"),  # $8 per roll
            session=db_session,
        )

        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )

        expected_qty = 50 * 929.0304  # 46451.52 sq cm
        assert abs(inventory_item.quantity_purchased - expected_qty) < 0.01
        assert abs(inventory_item.quantity_remaining - expected_qty) < 0.01


# ============================================================================
# Get Product Inventory Tests (Feature 058: FIFO Aggregation)
# ============================================================================


class TestGetProductInventoryFIFO:
    """Test get_product_inventory with FIFO inventory items."""

    def test_get_inventory_aggregates_from_items(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """get_product_inventory aggregates from MaterialInventoryItem records."""
        # First purchase: 100 feet @ $12 = 3048 cm @ $0.00394/cm
        record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today() - timedelta(days=7),
            packages_purchased=1,
            package_price=Decimal("12.00"),
            session=db_session,
        )

        # Second purchase: 200 feet @ $15 = 6096 cm @ $0.00492/cm
        record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("15.00"),
            session=db_session,
        )

        info = get_product_inventory(sample_product_feet.id, session=db_session)

        # Total: 3048 + 6096 = 9144 cm
        assert info["current_inventory"] == 9144.0
        assert info["inventory_lots"] == 2  # Two FIFO lots
        assert info["base_unit_type"] == "linear_cm"

    def test_get_inventory_weighted_avg_cost(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """Weighted average cost calculated correctly from FIFO items."""
        # Purchase 1: 3048 cm @ $12 (total $12)
        # Purchase 2: 6096 cm @ $30 (total $30)
        # Total value: $42, Total qty: 9144 cm
        # Weighted avg: $42 / 9144 = ~$0.004593/cm
        record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today() - timedelta(days=7),
            packages_purchased=1,
            package_price=Decimal("12.00"),
            session=db_session,
        )
        record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=2,
            package_price=Decimal("15.00"),
            session=db_session,
        )

        info = get_product_inventory(sample_product_feet.id, session=db_session)

        # Verify weighted average is reasonable (between the two unit costs)
        # Unit cost 1: $12/3048 = ~0.00394
        # Unit cost 2: $30/6096 = ~0.00492
        # Weighted should be between these
        avg_cost = float(info["weighted_avg_cost"])
        assert 0.0039 < avg_cost < 0.0050

    def test_get_inventory_empty_product(
        self, db_session, sample_product_feet
    ):
        """get_product_inventory returns zero for product with no purchases."""
        info = get_product_inventory(sample_product_feet.id, session=db_session)

        assert info["current_inventory"] == 0
        assert info["weighted_avg_cost"] == Decimal("0")
        assert info["inventory_lots"] == 0

    def test_get_inventory_excludes_depleted_items(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """Depleted inventory items are not counted."""
        purchase = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("12.00"),
            session=db_session,
        )

        # Manually deplete the inventory item
        item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )
        item.quantity_remaining = 0.0005  # Below depletion threshold
        db_session.flush()

        info = get_product_inventory(sample_product_feet.id, session=db_session)

        assert info["current_inventory"] == 0
        assert info["inventory_lots"] == 0


# ============================================================================
# Validation Tests
# ============================================================================


class TestPurchaseValidation:
    """Test purchase validation with FIFO integration."""

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

    def test_purchase_invalid_supplier(self, db_session, sample_product_feet):
        """Purchase with invalid supplier raises error."""
        with pytest.raises(SupplierNotFoundError) as exc:
            record_purchase(
                product_id=sample_product_feet.id,
                supplier_id=99999,
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("10.00"),
                session=db_session,
            )
        assert "99999" in str(exc.value)

    def test_purchase_zero_packages(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """Purchase with zero packages raises error."""
        with pytest.raises(ValidationError) as exc:
            record_purchase(
                product_id=sample_product_feet.id,
                supplier_id=sample_supplier.id,
                purchase_date=date.today(),
                packages_purchased=0,
                package_price=Decimal("10.00"),
                session=db_session,
            )
        assert "positive" in str(exc.value)

    def test_purchase_negative_price(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """Purchase with negative price raises error."""
        with pytest.raises(ValidationError) as exc:
            record_purchase(
                product_id=sample_product_feet.id,
                supplier_id=sample_supplier.id,
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("-10.00"),
                session=db_session,
            )
        assert "negative" in str(exc.value)

    def test_purchase_zero_price_allowed(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """Purchase with zero price (free/donation) is allowed."""
        purchase = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("0.00"),
            notes="Donation",
            session=db_session,
        )
        assert purchase.package_price == Decimal("0.00")

        # Verify inventory item was still created
        item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )
        assert item is not None
        assert item.cost_per_unit == Decimal("0")


# ============================================================================
# Atomicity Tests
# ============================================================================


class TestPurchaseAtomicity:
    """Test that purchase and inventory item creation are atomic."""

    def test_purchase_and_inventory_same_transaction(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """Purchase and inventory item are created in same transaction."""
        # This test verifies atomicity by checking both records exist
        # after a successful purchase
        purchase = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("15.00"),
            session=db_session,
        )

        # Verify both exist before commit
        assert purchase.id is not None

        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )
        assert inventory_item is not None
        assert inventory_item.id is not None

        # Both have the same purchase date
        assert inventory_item.purchase_date == purchase.purchase_date

    def test_inventory_item_references_purchase(
        self, db_session, sample_product_feet, sample_supplier
    ):
        """Inventory item correctly references its purchase record."""
        purchase = record_purchase(
            product_id=sample_product_feet.id,
            supplier_id=sample_supplier.id,
            purchase_date=date.today(),
            packages_purchased=1,
            package_price=Decimal("15.00"),
            notes="Test notes",
            session=db_session,
        )

        # Access via relationship
        assert purchase.inventory_item is not None
        assert purchase.inventory_item.material_purchase_id == purchase.id
        assert purchase.inventory_item.notes == "Test notes"

        # Access via query
        inventory_item = (
            db_session.query(MaterialInventoryItem)
            .filter_by(material_purchase_id=purchase.id)
            .first()
        )
        assert inventory_item.purchase.id == purchase.id
