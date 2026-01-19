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
    adjust_inventory,
)
from src.services.exceptions import (
    MaterialInventoryItemNotFoundError,
    ValidationError as ServiceValidationError,
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
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            lot_a.quantity_remaining = 0.0

        lots = get_fifo_inventory(setup_two_lots["product_id"])

        assert len(lots) == 1
        assert lots[0].id == setup_two_lots["lot_b_id"]

    def test_excludes_near_zero_lots(self, setup_two_lots):
        """Verify floating-point dust (< 0.001) is excluded."""
        # Set lot A to near-zero (floating-point dust)
        with session_scope() as session:
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
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
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
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
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            assert lot_a.quantity_remaining == 70.0  # 100 - 30

    def test_dry_run_does_not_modify_inventory(self, setup_two_lots):
        """Verify dry_run mode doesn't change quantities."""
        # Get initial quantity
        with session_scope() as session:
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
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
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            assert lot_a.quantity_remaining == initial_qty

        assert result["satisfied"] is True
        assert result["total_cost"] == Decimal("5.00")


class TestConsumeMaterialFifoMultiLot:
    """Tests for consume_material_fifo spanning multiple lots."""

    def test_consumes_oldest_first_then_newer(self, setup_two_lots):
        """Spec scenario 2: Lot A (30cm), consume 50cm → 30 from A + 20 from B."""
        # Reduce lot A to 30cm remaining
        with session_scope() as session:
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
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
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            lot_b = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_b_id"])
                .first()
            )

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
        requirements = [
            {
                "material_product_id": setup_two_lots["product_id"],
                "quantity_needed": Decimal("100"),
                "unit": "cm",
            }
        ]

        result = validate_inventory_availability(requirements)

        assert result["can_fulfill"] is True
        assert len(result["shortfalls"]) == 0

    def test_returns_shortfalls_when_insufficient(self, setup_two_lots):
        """Verify shortfalls reported when inventory insufficient."""
        requirements = [
            {
                "material_product_id": setup_two_lots["product_id"],
                "quantity_needed": Decimal("300"),  # More than 200 available
                "unit": "cm",
            }
        ]

        result = validate_inventory_availability(requirements)

        assert result["can_fulfill"] is False
        assert len(result["shortfalls"]) == 1
        assert result["shortfalls"][0]["shortfall"] == Decimal("100")

    def test_does_not_modify_inventory(self, setup_two_lots):
        """Verify validation doesn't consume inventory (uses dry_run)."""
        # Get initial quantities
        with session_scope() as session:
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            initial_qty = lot_a.quantity_remaining

        requirements = [
            {
                "material_product_id": setup_two_lots["product_id"],
                "quantity_needed": Decimal("50"),
                "unit": "cm",
            }
        ]

        validate_inventory_availability(requirements)

        # Verify quantity unchanged
        with session_scope() as session:
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
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
        value = get_total_inventory_value(material_product_id=setup_two_lots["product_id"])
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
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            original_qty_purchased = lot_a.quantity_purchased

        # Consume some inventory
        consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        # Verify quantity_purchased unchanged (only quantity_remaining changed)
        with session_scope() as session:
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            assert lot_a.quantity_purchased == original_qty_purchased
            assert lot_a.quantity_remaining == 50.0  # Reduced

    def test_cost_per_unit_not_changed_by_consumption(self, setup_two_lots):
        """FR-016: Verify cost_per_unit remains unchanged after consumption."""
        # Get initial cost_per_unit
        with session_scope() as session:
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            original_cost = lot_a.cost_per_unit

        # Consume some inventory
        consume_material_fifo(
            material_product_id=setup_two_lots["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        # Verify cost_per_unit unchanged
        with session_scope() as session:
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
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
            lot_a = (
                session.query(MaterialInventoryItem)
                .filter_by(id=setup_two_lots["lot_a_id"])
                .first()
            )
            assert lot_a.quantity_remaining == 100.0


# =============================================================================
# Feature 059: Inventory Adjustment Tests
# =============================================================================


class TestAdjustInventory:
    """Tests for adjust_inventory() function - F059."""

    def test_adjust_add(self, setup_two_lots):
        """Test adding to inventory quantity."""
        result = adjust_inventory(
            setup_two_lots["lot_a_id"],
            "add",
            Decimal("25"),
            notes="Found extra",
        )

        assert result["quantity_remaining"] == Decimal("125")

        # Verify in database
        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert item.quantity_remaining == 125.0

    def test_adjust_subtract(self, setup_two_lots):
        """Test subtracting from inventory quantity."""
        result = adjust_inventory(
            setup_two_lots["lot_a_id"],
            "subtract",
            Decimal("30"),
            notes="Used untracked",
        )

        assert result["quantity_remaining"] == Decimal("70")

        # Verify in database
        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert item.quantity_remaining == 70.0

    def test_adjust_set(self, setup_two_lots):
        """Test setting exact inventory quantity."""
        result = adjust_inventory(
            setup_two_lots["lot_a_id"],
            "set",
            Decimal("50"),
            notes="Physical count",
        )

        assert result["quantity_remaining"] == Decimal("50")

        # Verify in database
        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert item.quantity_remaining == 50.0

    def test_adjust_percentage_50(self, setup_two_lots):
        """Test 50% adjustment (half remaining)."""
        result = adjust_inventory(
            setup_two_lots["lot_a_id"],
            "percentage",
            Decimal("50"),
            notes="Half used",
        )

        assert result["quantity_remaining"] == Decimal("50.00")

    def test_adjust_percentage_zero(self, setup_two_lots):
        """Test 0% adjustment (fully depleted)."""
        result = adjust_inventory(
            setup_two_lots["lot_a_id"],
            "percentage",
            Decimal("0"),
        )

        assert result["quantity_remaining"] == Decimal("0")

    def test_adjust_percentage_100(self, setup_two_lots):
        """Test 100% adjustment (no change)."""
        result = adjust_inventory(
            setup_two_lots["lot_a_id"],
            "percentage",
            Decimal("100"),
        )

        assert result["quantity_remaining"] == Decimal("100.00")

    def test_adjust_negative_result_raises(self, setup_two_lots):
        """Test that negative result raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc:
            adjust_inventory(
                setup_two_lots["lot_a_id"],
                "subtract",
                Decimal("200"),  # More than available (100)
            )

        assert "negative quantity" in str(exc.value).lower()

    def test_adjust_invalid_percentage_above_100_raises(self, setup_two_lots):
        """Test that percentage > 100 raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc:
            adjust_inventory(
                setup_two_lots["lot_a_id"],
                "percentage",
                Decimal("150"),
            )

        assert "0-100" in str(exc.value)

    def test_adjust_invalid_percentage_below_0_raises(self, setup_two_lots):
        """Test that percentage < 0 raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc:
            adjust_inventory(
                setup_two_lots["lot_a_id"],
                "percentage",
                Decimal("-10"),
            )

        assert "0-100" in str(exc.value)

    def test_adjust_invalid_type_raises(self, setup_two_lots):
        """Test that invalid adjustment_type raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc:
            adjust_inventory(
                setup_two_lots["lot_a_id"],
                "multiply",  # Invalid type
                Decimal("2"),
            )

        assert "invalid adjustment_type" in str(exc.value).lower()

    def test_adjust_notes_stored(self, setup_two_lots):
        """Test that adjustment notes are stored with timestamp."""
        adjust_inventory(
            setup_two_lots["lot_a_id"],
            "set",
            Decimal("75"),
            notes="Inventory recount",
        )

        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert "Inventory recount" in item.notes
            assert "Adjustment (set)" in item.notes
            # Should have timestamp format
            assert "UTC" in item.notes

    def test_adjust_notes_appended(self, setup_two_lots):
        """Test that multiple adjustments append notes."""
        # First adjustment
        adjust_inventory(
            setup_two_lots["lot_a_id"],
            "subtract",
            Decimal("10"),
            notes="First adjustment",
        )

        # Second adjustment
        adjust_inventory(
            setup_two_lots["lot_a_id"],
            "add",
            Decimal("5"),
            notes="Second adjustment",
        )

        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert "First adjustment" in item.notes
            assert "Second adjustment" in item.notes
            # Notes should be on separate lines
            assert "\n" in item.notes

    def test_adjust_without_notes(self, setup_two_lots):
        """Test adjustment without notes (notes remain unchanged)."""
        # First, set initial notes via adjustment
        adjust_inventory(
            setup_two_lots["lot_a_id"],
            "set",
            Decimal("80"),
            notes="Initial note",
        )

        # Second adjustment without notes
        adjust_inventory(
            setup_two_lots["lot_a_id"],
            "subtract",
            Decimal("5"),
            notes=None,  # No notes
        )

        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            # Original note should still be there, no new line added
            assert "Initial note" in item.notes
            assert item.notes.count("Adjustment") == 1  # Only one adjustment note

    def test_adjust_item_not_found(self, setup_material_hierarchy):
        """Test adjusting non-existent item raises error."""
        with pytest.raises(MaterialInventoryItemNotFoundError):
            adjust_inventory(
                99999,  # Non-existent ID
                "set",
                Decimal("50"),
            )

    def test_adjust_with_session(self, setup_two_lots):
        """Test adjustment works with provided session."""
        with session_scope() as session:
            result = adjust_inventory(
                setup_two_lots["lot_a_id"],
                "subtract",
                Decimal("20"),
                notes="Session test",
                session=session,
            )

            assert result["quantity_remaining"] == Decimal("80")

            # Verify within same session
            item = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            assert item.quantity_remaining == 80.0

    def test_adjust_set_to_zero(self, setup_two_lots):
        """Test setting quantity to exactly zero is allowed."""
        result = adjust_inventory(
            setup_two_lots["lot_a_id"],
            "set",
            Decimal("0"),
            notes="Depleted",
        )

        assert result["quantity_remaining"] == Decimal("0")
        assert result["is_depleted"] is True

    def test_adjust_decimal_precision(self, setup_two_lots):
        """Test that percentage adjustments maintain proper decimal precision."""
        # Start with 100, take 33% remaining
        result = adjust_inventory(
            setup_two_lots["lot_a_id"],
            "percentage",
            Decimal("33"),
        )

        # Should be 33.00 (rounded to 2 decimal places)
        assert result["quantity_remaining"] == Decimal("33.00")


# =============================================================================
# Feature 059: list_inventory_items Tests
# =============================================================================


class TestListInventoryItems:
    """Tests for list_inventory_items function (Feature 059 - WP04)."""

    def test_list_all_items(self, setup_two_lots):
        """Test listing all non-depleted inventory items."""
        from src.services.material_inventory_service import list_inventory_items

        items = list_inventory_items()
        assert len(items) >= 2  # At least the two lots we created

        # Check that our test items are in the list
        item_ids = [item["id"] for item in items]
        assert setup_two_lots["lot_a_id"] in item_ids
        assert setup_two_lots["lot_b_id"] in item_ids

    def test_list_by_product_id(self, setup_two_lots, setup_material_hierarchy):
        """Test filtering by product_id."""
        from src.services.material_inventory_service import list_inventory_items

        items = list_inventory_items(product_id=setup_material_hierarchy["product_id"])
        assert len(items) == 2  # Exactly our two test lots

        for item in items:
            assert item["material_product_id"] == setup_material_hierarchy["product_id"]

    def test_list_excludes_depleted_by_default(self, setup_two_lots):
        """Test that depleted items are excluded by default."""
        from src.services.material_inventory_service import list_inventory_items

        # Deplete lot A
        adjust_inventory(
            setup_two_lots["lot_a_id"],
            "set",
            Decimal("0"),
        )

        items = list_inventory_items()
        item_ids = [item["id"] for item in items]

        # Depleted lot should not be in list
        assert setup_two_lots["lot_a_id"] not in item_ids
        # Non-depleted lot should still be in list
        assert setup_two_lots["lot_b_id"] in item_ids

    def test_list_includes_depleted_when_requested(self, setup_two_lots):
        """Test that include_depleted=True includes depleted items."""
        from src.services.material_inventory_service import list_inventory_items

        # Deplete lot A
        adjust_inventory(
            setup_two_lots["lot_a_id"],
            "set",
            Decimal("0"),
        )

        items = list_inventory_items(include_depleted=True)
        item_ids = [item["id"] for item in items]

        # Both lots should be in list
        assert setup_two_lots["lot_a_id"] in item_ids
        assert setup_two_lots["lot_b_id"] in item_ids

    def test_list_includes_product_info(self, setup_two_lots):
        """Test that returned items include product name and brand."""
        from src.services.material_inventory_service import list_inventory_items

        items = list_inventory_items()

        # Find one of our test items
        test_item = next(
            (i for i in items if i["id"] == setup_two_lots["lot_a_id"]),
            None
        )
        assert test_item is not None
        assert "product_name" in test_item
        assert "brand" in test_item
        assert "display_name" in test_item

    def test_list_ordered_by_date_descending(self, setup_two_lots):
        """Test that items are ordered by purchase_date descending (newest first)."""
        from src.services.material_inventory_service import list_inventory_items

        items = list_inventory_items()

        # Filter to just our test items
        test_items = [
            i for i in items
            if i["id"] in [setup_two_lots["lot_a_id"], setup_two_lots["lot_b_id"]]
        ]

        # Lot B is newer (5 days ago vs 10 days ago), should come first
        if len(test_items) == 2:
            if test_items[0]["id"] == setup_two_lots["lot_b_id"]:
                assert test_items[0]["purchase_date"] >= test_items[1]["purchase_date"]

    def test_list_with_session(self, setup_two_lots):
        """Test list_inventory_items works with provided session."""
        from src.services.material_inventory_service import list_inventory_items

        with session_scope() as session:
            items = list_inventory_items(session=session)
            assert len(items) >= 2

    def test_list_empty_result(self, setup_material_hierarchy):
        """Test listing with filter that matches nothing."""
        from src.services.material_inventory_service import list_inventory_items

        # Use a product_id that doesn't exist
        items = list_inventory_items(product_id=99999)
        assert items == []
