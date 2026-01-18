"""Tests for material inventory service FIFO operations.

Part of Feature 058: Materials FIFO Foundation.
These tests validate the core FIFO algorithm and service layer functions.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services.database import session_scope
from src.models import (
    Material,
    MaterialProduct,
    MaterialPurchase,
    MaterialInventoryItem,
    MaterialCategory,
    MaterialSubcategory,
    Supplier,
)
from src.services.material_inventory_service import (
    get_fifo_inventory,
    calculate_available_inventory,
    consume_material_fifo,
    validate_inventory_availability,
    get_inventory_by_material,
    get_total_inventory_value,
)


@pytest.fixture
def setup_material_hierarchy(test_db):
    """Create test material hierarchy (category/subcategory/material)."""
    with session_scope() as session:
        # Create supplier
        supplier = Supplier(name="Test Material Supplier", slug="test-material-supplier")
        session.add(supplier)

        # Create category hierarchy
        category = MaterialCategory(name="Test Category", slug="test-cat-fifo")
        session.add(category)
        session.flush()

        subcategory = MaterialSubcategory(
            category_id=category.id,
            name="Test Subcategory",
            slug="test-subcat-fifo",
        )
        session.add(subcategory)
        session.flush()

        # Create material with linear_cm base type
        material = Material(
            subcategory_id=subcategory.id,
            name="Test Ribbon FIFO",
            slug="test-ribbon-fifo",
            base_unit_type="linear_cm",
        )
        session.add(material)
        session.flush()

        # Create product
        product = MaterialProduct(
            material_id=material.id,
            supplier_id=supplier.id,
            name="100ft Red Ribbon FIFO Test",
            package_quantity=100,
            package_unit="feet",
            quantity_in_base_units=3048,  # 100 feet = 3048 cm
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


@pytest.fixture
def setup_two_lots(setup_material_hierarchy):
    """Create two inventory lots for FIFO testing.

    Lot A: Older (10 days ago), 100 cm @ $0.10/cm
    Lot B: Newer (5 days ago), 100 cm @ $0.15/cm
    """
    data = setup_material_hierarchy

    with session_scope() as session:
        # Create a purchase record for lot A (to satisfy FK)
        purchase_a = MaterialPurchase(
            product_id=data["product_id"],
            supplier_id=data["supplier_id"],
            purchase_date=date.today() - timedelta(days=10),
            packages_purchased=1,
            package_price=Decimal("10.00"),
            units_added=100.0,
            unit_cost=Decimal("0.10"),
        )
        session.add(purchase_a)
        session.flush()

        # Older lot - purchased 10 days ago
        lot_a = MaterialInventoryItem(
            material_product_id=data["product_id"],
            material_purchase_id=purchase_a.id,
            quantity_purchased=100.0,  # 100 cm
            quantity_remaining=100.0,
            cost_per_unit=Decimal("0.10"),  # $0.10/cm
            purchase_date=date.today() - timedelta(days=10),
        )
        session.add(lot_a)
        session.flush()
        lot_a_id = lot_a.id

        # Create a purchase record for lot B
        purchase_b = MaterialPurchase(
            product_id=data["product_id"],
            supplier_id=data["supplier_id"],
            purchase_date=date.today() - timedelta(days=5),
            packages_purchased=1,
            package_price=Decimal("15.00"),
            units_added=100.0,
            unit_cost=Decimal("0.15"),
        )
        session.add(purchase_b)
        session.flush()

        # Newer lot - purchased 5 days ago
        lot_b = MaterialInventoryItem(
            material_product_id=data["product_id"],
            material_purchase_id=purchase_b.id,
            quantity_purchased=100.0,  # 100 cm
            quantity_remaining=100.0,
            cost_per_unit=Decimal("0.15"),  # $0.15/cm
            purchase_date=date.today() - timedelta(days=5),
        )
        session.add(lot_b)
        session.flush()
        lot_b_id = lot_b.id

        return {
            **data,
            "lot_a_id": lot_a_id,
            "lot_b_id": lot_b_id,
        }


class TestGetFifoInventory:
    """Tests for get_fifo_inventory function."""

    def test_returns_lots_ordered_by_purchase_date(self, setup_two_lots):
        """Verify oldest lots returned first (FIFO order)."""
        lots = get_fifo_inventory(setup_two_lots["product_id"])

        assert len(lots) == 2
        # First lot should be older (purchased 10 days ago)
        assert lots[0].purchase_date < lots[1].purchase_date
        assert lots[0].id == setup_two_lots["lot_a_id"]
        assert lots[1].id == setup_two_lots["lot_b_id"]

    def test_excludes_depleted_lots(self, setup_two_lots):
        """Verify depleted lots (quantity_remaining < 0.001) are excluded."""
        # Deplete lot A
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            lot_a.quantity_remaining = 0.0

        lots = get_fifo_inventory(setup_two_lots["product_id"])

        assert len(lots) == 1
        assert lots[0].id == setup_two_lots["lot_b_id"]

    def test_excludes_near_zero_lots(self, setup_two_lots):
        """Verify floating-point dust (< 0.001) is excluded."""
        # Set lot A to near-zero (floating-point dust)
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            lot_a.quantity_remaining = 0.0005  # Below threshold

        lots = get_fifo_inventory(setup_two_lots["product_id"])

        assert len(lots) == 1
        assert lots[0].id == setup_two_lots["lot_b_id"]

    def test_returns_empty_for_no_inventory(self, setup_material_hierarchy):
        """Verify empty list when no inventory exists."""
        lots = get_fifo_inventory(setup_material_hierarchy["product_id"])
        assert lots == []


class TestCalculateAvailableInventory:
    """Tests for calculate_available_inventory function."""

    def test_sums_all_lot_quantities(self, setup_two_lots):
        """Verify total is sum of quantity_remaining across lots."""
        available = calculate_available_inventory(setup_two_lots["product_id"])
        assert available == Decimal("200.0")  # 100 + 100

    def test_excludes_depleted_lots(self, setup_two_lots):
        """Verify depleted lots don't contribute to total."""
        # Deplete lot A
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            lot_a.quantity_remaining = 0.0

        available = calculate_available_inventory(setup_two_lots["product_id"])
        assert available == Decimal("100.0")  # Only lot B

    def test_returns_zero_for_no_inventory(self, setup_material_hierarchy):
        """Verify zero when no inventory exists."""
        available = calculate_available_inventory(setup_material_hierarchy["product_id"])
        assert available == Decimal("0")


class TestConsumeMaterialFifoSingleLot:
    """Tests for consume_material_fifo with single lot scenarios."""

    def test_consumes_from_single_lot(self, setup_two_lots):
        """Spec scenario 1: Consume 50cm from oldest lot → $5.00."""
        result = consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        assert result["satisfied"] is True
        assert result["consumed"] == Decimal("50")
        assert result["shortfall"] == Decimal("0")
        assert result["total_cost"] == Decimal("5.00")  # 50 * $0.10

        # Verify only lot A was touched (oldest first)
        assert len(result["breakdown"]) == 1
        assert result["breakdown"][0]["inventory_item_id"] == setup_two_lots["lot_a_id"]

    def test_updates_lot_quantity_remaining(self, setup_two_lots):
        """Verify lot quantity is updated after consumption."""
        consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("30"),
            target_unit="cm",
        )

        # Verify lot A quantity was reduced
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert lot_a.quantity_remaining == 70.0  # 100 - 30

    def test_dry_run_does_not_modify_inventory(self, setup_two_lots):
        """Verify dry_run mode doesn't change quantities."""
        # Get initial quantity
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            initial_qty = lot_a.quantity_remaining

        # Run dry_run consumption
        result = consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
            dry_run=True,
        )

        # Verify quantity unchanged
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert lot_a.quantity_remaining == initial_qty

        assert result["satisfied"] is True
        assert result["total_cost"] == Decimal("5.00")


class TestConsumeMaterialFifoMultiLot:
    """Tests for consume_material_fifo spanning multiple lots."""

    def test_consumes_oldest_first_then_newer(self, setup_two_lots):
        """Spec scenario 2: Lot A (30cm), consume 50cm → 30 from A + 20 from B."""
        # Reduce lot A to 30cm remaining
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            lot_a.quantity_remaining = 30.0

        result = consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        assert result["satisfied"] is True
        assert result["consumed"] == Decimal("50")
        # Cost: (30 * $0.10) + (20 * $0.15) = $3.00 + $3.00 = $6.00
        assert result["total_cost"] == Decimal("6.00")

        # Verify both lots consumed
        assert len(result["breakdown"]) == 2
        # First breakdown should be lot A (30cm)
        assert result["breakdown"][0]["inventory_item_id"] == setup_two_lots["lot_a_id"]
        assert result["breakdown"][0]["quantity_consumed"] == Decimal("30")
        # Second breakdown should be lot B (20cm)
        assert result["breakdown"][1]["inventory_item_id"] == setup_two_lots["lot_b_id"]
        assert result["breakdown"][1]["quantity_consumed"] == Decimal("20")

    def test_depletes_lot_completely_before_next(self, setup_two_lots):
        """Verify lot is fully depleted before moving to next."""
        result = consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("150"),
            target_unit="cm",
        )

        # Should consume all 100 from A, then 50 from B
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            lot_b = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_b_id"]
            ).first()

            assert lot_a.quantity_remaining < 0.001  # Depleted
            assert lot_b.quantity_remaining == 50.0  # 100 - 50

        assert result["satisfied"] is True
        # Cost: (100 * $0.10) + (50 * $0.15) = $10.00 + $7.50 = $17.50
        assert result["total_cost"] == Decimal("17.50")


class TestConsumeMaterialFifoShortfall:
    """Tests for consume_material_fifo with insufficient inventory."""

    def test_reports_shortfall_when_insufficient(self, setup_two_lots):
        """Verify shortfall reported when demand exceeds supply."""
        # Try to consume more than available (200cm total)
        result = consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("250"),
            target_unit="cm",
        )

        assert result["satisfied"] is False
        assert result["consumed"] == Decimal("200")  # All available
        assert result["shortfall"] == Decimal("50")  # 250 - 200

    def test_shortfall_with_empty_inventory(self, setup_material_hierarchy):
        """Verify full shortfall when no inventory exists."""
        result = consume_material_fifo(
            material_product_id=setup_material_hierarchy["product_id"],
            quantity_needed=Decimal("100"),
            target_unit="cm",
        )

        assert result["satisfied"] is False
        assert result["consumed"] == Decimal("0")
        assert result["shortfall"] == Decimal("100")
        assert result["total_cost"] == Decimal("0")

    def test_zero_cost_donated_materials(self, setup_material_hierarchy):
        """Verify $0 cost materials (donations) work correctly."""
        # Create a purchase for the lot
        with session_scope() as session:
            purchase = MaterialPurchase(
                product_id=setup_material_hierarchy["product_id"],
                supplier_id=setup_material_hierarchy["supplier_id"],
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("0.00"),
                units_added=100.0,
                unit_cost=Decimal("0.00"),
            )
            session.add(purchase)
            session.flush()

            # Create a lot with $0 cost
            lot = MaterialInventoryItem(
                material_product_id=setup_material_hierarchy["product_id"],
                material_purchase_id=purchase.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.00"),  # Donated
                purchase_date=date.today(),
            )
            session.add(lot)

        result = consume_material_fifo(
            material_product_id=setup_material_hierarchy["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        assert result["satisfied"] is True
        assert result["total_cost"] == Decimal("0.00")  # Free!


class TestValidateInventoryAvailability:
    """Tests for validate_inventory_availability function."""

    def test_returns_can_fulfill_true_when_sufficient(self, setup_two_lots):
        """Verify can_fulfill=True when inventory meets requirements."""
        requirements = [{
            "material_product_id": setup_two_lots["product_id"],
            "quantity_needed": Decimal("100"),
            "unit": "cm",
        }]

        result = validate_inventory_availability(requirements)

        assert result["can_fulfill"] is True
        assert len(result["shortfalls"]) == 0

    def test_returns_shortfalls_when_insufficient(self, setup_two_lots):
        """Verify shortfalls reported when inventory insufficient."""
        requirements = [{
            "material_product_id": setup_two_lots["product_id"],
            "quantity_needed": Decimal("300"),  # More than 200 available
            "unit": "cm",
        }]

        result = validate_inventory_availability(requirements)

        assert result["can_fulfill"] is False
        assert len(result["shortfalls"]) == 1
        assert result["shortfalls"][0]["shortfall"] == Decimal("100")

    def test_does_not_modify_inventory(self, setup_two_lots):
        """Verify validation doesn't consume inventory (uses dry_run)."""
        # Get initial quantities
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            initial_qty = lot_a.quantity_remaining

        requirements = [{
            "material_product_id": setup_two_lots["product_id"],
            "quantity_needed": Decimal("50"),
            "unit": "cm",
        }]

        validate_inventory_availability(requirements)

        # Verify quantity unchanged
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert lot_a.quantity_remaining == initial_qty


class TestGetInventoryByMaterial:
    """Tests for get_inventory_by_material function."""

    def test_returns_all_lots_for_material(self, setup_two_lots):
        """Verify all inventory items for a material are returned."""
        lots = get_inventory_by_material(setup_two_lots["material_id"])

        assert len(lots) == 2
        # Should be ordered by purchase_date ASC
        assert lots[0].purchase_date < lots[1].purchase_date

    def test_returns_empty_for_no_inventory(self, setup_material_hierarchy):
        """Verify empty list when no inventory exists for material."""
        lots = get_inventory_by_material(setup_material_hierarchy["material_id"])
        assert lots == []


class TestGetTotalInventoryValue:
    """Tests for get_total_inventory_value function."""

    def test_calculates_total_value_for_product(self, setup_two_lots):
        """Verify total value calculation for specific product."""
        value = get_total_inventory_value(
            material_product_id=setup_two_lots["product_id"]
        )
        # Lot A: 100 * $0.10 = $10.00
        # Lot B: 100 * $0.15 = $15.00
        # Total: $25.00
        assert value == Decimal("25.00")

    def test_returns_zero_for_no_inventory(self, setup_material_hierarchy):
        """Verify zero value when no inventory exists."""
        value = get_total_inventory_value(
            material_product_id=setup_material_hierarchy["product_id"]
        )
        assert value == Decimal("0.0")


class TestImmutabilityBehavior:
    """Tests verifying immutable field behavior (FR-015, FR-016).

    Note: These tests verify the EXPECTED behavior that quantity_purchased
    and cost_per_unit should be immutable. The actual enforcement may be
    at the application layer (service functions that refuse to update these
    fields) rather than at the database/model layer.
    """

    def test_quantity_purchased_not_changed_by_consumption(self, setup_two_lots):
        """FR-015: Verify quantity_purchased remains unchanged after consumption."""
        # Get initial quantity_purchased
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            original_qty_purchased = lot_a.quantity_purchased

        # Consume some inventory
        consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        # Verify quantity_purchased unchanged (only quantity_remaining changed)
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert lot_a.quantity_purchased == original_qty_purchased
            assert lot_a.quantity_remaining == 50.0  # Reduced

    def test_cost_per_unit_not_changed_by_consumption(self, setup_two_lots):
        """FR-016: Verify cost_per_unit remains unchanged after consumption."""
        # Get initial cost_per_unit
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            original_cost = lot_a.cost_per_unit

        # Consume some inventory
        consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        # Verify cost_per_unit unchanged
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert lot_a.cost_per_unit == original_cost


class TestSessionManagement:
    """Tests for proper session management pattern."""

    def test_accepts_external_session(self, setup_two_lots):
        """Verify functions work correctly with provided session."""
        with session_scope() as session:
            # Call with external session
            lots = get_fifo_inventory(
                setup_two_lots["product_id"],
                session=session,
            )
            assert len(lots) == 2

            available = calculate_available_inventory(
                setup_two_lots["product_id"],
                session=session,
            )
            assert available == Decimal("200.0")

    def test_dry_run_with_external_session(self, setup_two_lots):
        """Verify dry_run works correctly with external session."""
        with session_scope() as session:
            result = consume_material_fifo(
                material_product_id=setup_two_lots["product_id"],
                quantity_needed=Decimal("50"),
                target_unit="cm",
                dry_run=True,
                session=session,
            )
            assert result["satisfied"] is True

            # Verify quantity unchanged within same session
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert lot_a.quantity_remaining == 100.0
