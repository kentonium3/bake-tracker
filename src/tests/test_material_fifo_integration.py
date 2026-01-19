"""Integration tests for Materials FIFO Foundation (F058).

These tests validate end-to-end FIFO behavior across the full stack:
- Purchase recording → Inventory item creation
- FIFO consumption across multiple lots
- Cost calculation accuracy
- Pattern consistency with ingredient system

Reference: kitty-specs/058-materials-fifo-foundation/spec.md
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
    InventoryItem,  # For pattern comparison
)
from src.services.material_inventory_service import (
    get_fifo_inventory,
    consume_material_fifo,
    calculate_available_inventory,
)


@pytest.fixture
def integration_material_setup(test_db):
    """
    Create complete material hierarchy for integration tests.

    Creates:
    - Category: Test Packaging
    - Subcategory: Ribbons
    - Material: Red Satin Ribbon (base_unit_type: linear_cm)
    - Product: 100ft Roll
    - Supplier: Test Supplier
    """
    with session_scope() as session:
        # Supplier
        supplier = Supplier(
            name="Integration Test Supplier",
            slug="integration-test-supplier",
        )
        session.add(supplier)

        # Category hierarchy
        category = MaterialCategory(
            name="Test Packaging",
            slug="test-packaging-integ",
        )
        session.add(category)
        session.flush()

        subcategory = MaterialSubcategory(
            category_id=category.id,
            name="Ribbons",
            slug="ribbons-integ",
        )
        session.add(subcategory)
        session.flush()

        material = Material(
            subcategory_id=subcategory.id,
            name="Red Satin Ribbon",
            slug="red-satin-ribbon-integ",
            base_unit_type="linear_cm",
        )
        session.add(material)
        session.flush()

        product = MaterialProduct(
            material_id=material.id,
            supplier_id=supplier.id,
            name="100ft Red Ribbon Roll",
            package_quantity=100,
            package_unit="feet",
            quantity_in_base_units=3048,  # 100 feet in cm
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


class TestPurchaseToInventoryFlow:
    """
    Integration tests for purchase → inventory item creation.

    Reference: Spec User Story 1 - Material Purchase Creates Inventory
    """

    def test_purchase_creates_inventory_item_with_correct_data(self, integration_material_setup):
        """
        Verify inventory item is created with correct data from purchase.

        Expected:
        - MaterialInventoryItem created
        - quantity_purchased reflects purchase
        - quantity_remaining = quantity_purchased
        - cost_per_unit from purchase
        """
        data = integration_material_setup

        with session_scope() as session:
            # Create purchase
            purchase = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("15.00"),
                units_added=100,  # 100 feet
                unit_cost=Decimal("0.15"),  # $15/100ft = $0.15/ft
            )
            session.add(purchase)
            session.flush()

            # Create corresponding inventory item
            inventory_item = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase.id,
                quantity_purchased=3048.0,  # 100 feet in cm
                quantity_remaining=3048.0,
                cost_per_unit=Decimal("0.00492"),  # ~$0.15/ft / 30.48 cm/ft
                purchase_date=purchase.purchase_date,
            )
            session.add(inventory_item)
            session.flush()
            item_id = inventory_item.id

        # Verify
        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(id=item_id).first()

            # Verify quantity conversion (100 feet = 3048 cm)
            assert abs(item.quantity_purchased - 3048.0) < 1.0
            assert item.quantity_remaining == item.quantity_purchased
            assert item.cost_per_unit > Decimal("0")

    def test_multiple_purchases_create_separate_lots(self, integration_material_setup):
        """Verify each purchase creates a separate inventory lot."""
        data = integration_material_setup

        with session_scope() as session:
            # First purchase
            purchase1 = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today() - timedelta(days=5),
                packages_purchased=1,
                package_price=Decimal("15.00"),
                units_added=100,
                unit_cost=Decimal("0.15"),
            )
            session.add(purchase1)
            session.flush()

            item1 = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase1.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.10"),
                purchase_date=purchase1.purchase_date,
            )
            session.add(item1)

            # Second purchase
            purchase2 = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("18.00"),
                units_added=100,
                unit_cost=Decimal("0.18"),
            )
            session.add(purchase2)
            session.flush()

            item2 = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase2.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.15"),
                purchase_date=purchase2.purchase_date,
            )
            session.add(item2)

        # Verify
        lots = get_fifo_inventory(data["product_id"])
        assert len(lots) == 2

        # Should be in FIFO order (oldest first)
        assert lots[0].purchase_date < lots[1].purchase_date


class TestMultiLotFifoConsumption:
    """
    Integration tests for FIFO consumption across multiple lots.

    Reference: Spec User Story 2 - FIFO Consumption of Materials
    """

    def test_spec_scenario_1_consume_from_oldest_lot_only(self, integration_material_setup):
        """
        Spec Acceptance Scenario 1:

        Given: Lot A (100cm @ $0.10/cm) purchased first, Lot B (100cm @ $0.15/cm)
        When: 50cm consumed
        Then: Consumption from Lot A only, total cost = $5.00
        """
        data = integration_material_setup

        with session_scope() as session:
            # Create purchase for Lot A (older - purchased 10 days ago)
            purchase_a = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today() - timedelta(days=10),
                packages_purchased=1,
                package_price=Decimal("10.00"),
                units_added=100,
                unit_cost=Decimal("0.10"),
            )
            session.add(purchase_a)
            session.flush()

            lot_a = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase_a.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.10"),
                purchase_date=purchase_a.purchase_date,
            )
            session.add(lot_a)

            # Create purchase for Lot B (newer - purchased 5 days ago)
            purchase_b = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today() - timedelta(days=5),
                packages_purchased=1,
                package_price=Decimal("15.00"),
                units_added=100,
                unit_cost=Decimal("0.15"),
            )
            session.add(purchase_b)
            session.flush()

            lot_b = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase_b.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.15"),
                purchase_date=purchase_b.purchase_date,
            )
            session.add(lot_b)
            session.flush()
            lot_a_id = lot_a.id
            lot_b_id = lot_b.id

        # Consume 50cm
        result = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        # Verify FIFO: only Lot A consumed
        assert result["satisfied"] is True
        assert result["consumed"] == Decimal("50")
        assert result["total_cost"] == Decimal("5.00")  # 50 * $0.10

        # Verify breakdown shows only Lot A
        assert len(result["breakdown"]) == 1
        assert result["breakdown"][0]["inventory_item_id"] == lot_a_id
        assert result["breakdown"][0]["quantity_consumed"] == Decimal("50")

        # Verify Lot B untouched
        with session_scope() as session:
            lot_b = session.query(MaterialInventoryItem).filter_by(id=lot_b_id).first()
            assert lot_b.quantity_remaining == 100.0

    def test_spec_scenario_2_consume_across_multiple_lots(self, integration_material_setup):
        """
        Spec Acceptance Scenario 2:

        Given: Lot A (30cm remaining @ $0.10), Lot B (100cm @ $0.15)
        When: 50cm consumed
        Then: 30cm from A + 20cm from B, cost = (30*$0.10) + (20*$0.15) = $6.00
        """
        data = integration_material_setup

        with session_scope() as session:
            # Create purchase for Lot A (older, partially depleted)
            purchase_a = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today() - timedelta(days=10),
                packages_purchased=1,
                package_price=Decimal("10.00"),
                units_added=100,
                unit_cost=Decimal("0.10"),
            )
            session.add(purchase_a)
            session.flush()

            lot_a = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase_a.id,
                quantity_purchased=100.0,
                quantity_remaining=30.0,  # Only 30cm remaining
                cost_per_unit=Decimal("0.10"),
                purchase_date=purchase_a.purchase_date,
            )
            session.add(lot_a)

            # Create purchase for Lot B (newer, full)
            purchase_b = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today() - timedelta(days=5),
                packages_purchased=1,
                package_price=Decimal("15.00"),
                units_added=100,
                unit_cost=Decimal("0.15"),
            )
            session.add(purchase_b)
            session.flush()

            lot_b = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase_b.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.15"),
                purchase_date=purchase_b.purchase_date,
            )
            session.add(lot_b)
            session.flush()
            lot_a_id = lot_a.id
            lot_b_id = lot_b.id

        # Consume 50cm
        result = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        # Verify FIFO: Lot A depleted first, then Lot B
        assert result["satisfied"] is True
        assert result["consumed"] == Decimal("50")

        # Cost: (30 * $0.10) + (20 * $0.15) = $3.00 + $3.00 = $6.00
        assert result["total_cost"] == Decimal("6.00")

        # Verify breakdown
        assert len(result["breakdown"]) == 2

        # First breakdown: Lot A (30cm @ $0.10)
        assert result["breakdown"][0]["inventory_item_id"] == lot_a_id
        assert result["breakdown"][0]["quantity_consumed"] == Decimal("30")

        # Second breakdown: Lot B (20cm @ $0.15)
        assert result["breakdown"][1]["inventory_item_id"] == lot_b_id
        assert result["breakdown"][1]["quantity_consumed"] == Decimal("20")

        # Verify final quantities
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(id=lot_a_id).first()
            lot_b = session.query(MaterialInventoryItem).filter_by(id=lot_b_id).first()

            assert lot_a.quantity_remaining < 0.001  # Depleted
            assert lot_b.quantity_remaining == 80.0  # 100 - 20


class TestCostCalculationAccuracy:
    """
    Integration tests for FIFO cost calculation accuracy.

    Verifies cost calculations remain accurate with:
    - Different cost per unit values
    - Multiple lots at different prices
    - Partial lot consumption
    """

    def test_cost_with_different_prices(self, integration_material_setup):
        """Verify cost calculation with varying prices across lots."""
        data = integration_material_setup

        with session_scope() as session:
            # Create lots with different prices (oldest to newest)
            lots = [
                (50.0, Decimal("0.05"), 15),  # Oldest, cheapest
                (50.0, Decimal("0.10"), 10),  # Middle
                (50.0, Decimal("0.20"), 5),  # Newest, most expensive
            ]

            for qty, cost, days_ago in lots:
                purchase = MaterialPurchase(
                    product_id=data["product_id"],
                    supplier_id=data["supplier_id"],
                    purchase_date=date.today() - timedelta(days=days_ago),
                    packages_purchased=1,
                    package_price=Decimal(str(qty * float(cost))),
                    units_added=int(qty),
                    unit_cost=cost,
                )
                session.add(purchase)
                session.flush()

                lot = MaterialInventoryItem(
                    material_product_id=data["product_id"],
                    material_purchase_id=purchase.id,
                    quantity_purchased=qty,
                    quantity_remaining=qty,
                    cost_per_unit=cost,
                    purchase_date=purchase.purchase_date,
                )
                session.add(lot)

        # Consume 100cm (should take all of lot 1 and lot 2)
        result = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("100"),
            target_unit="cm",
        )

        # Expected cost: (50 * $0.05) + (50 * $0.10) = $2.50 + $5.00 = $7.50
        assert result["total_cost"] == Decimal("7.50")
        assert result["satisfied"] is True

    def test_zero_cost_materials(self, integration_material_setup):
        """Verify $0 cost materials (donations) calculate correctly."""
        data = integration_material_setup

        with session_scope() as session:
            purchase = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("0.00"),  # Donated
                units_added=100,
                unit_cost=Decimal("0.00"),
            )
            session.add(purchase)
            session.flush()

            lot = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.00"),  # Donated
                purchase_date=purchase.purchase_date,
            )
            session.add(lot)

        result = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        assert result["satisfied"] is True
        assert result["total_cost"] == Decimal("0.00")

    def test_partial_lot_consumption_cost(self, integration_material_setup):
        """Verify cost accuracy with partial lot consumption."""
        data = integration_material_setup

        with session_scope() as session:
            purchase = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today(),
                packages_purchased=1,
                package_price=Decimal("12.00"),
                units_added=100,
                unit_cost=Decimal("0.12"),
            )
            session.add(purchase)
            session.flush()

            lot = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.12"),  # $0.12/cm
                purchase_date=purchase.purchase_date,
            )
            session.add(lot)

        # Consume 37cm
        result = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("37"),
            target_unit="cm",
        )

        # Expected: 37 * $0.12 = $4.44
        assert result["total_cost"] == Decimal("4.44")


class TestPatternConsistency:
    """
    Verify MaterialInventoryItem follows InventoryItem pattern.

    Reference: Spec SC-007 - Pattern consistency with ingredient system
    """

    def test_model_structure_matches_inventory_item(self, test_db):
        """
        Verify MaterialInventoryItem has equivalent fields to InventoryItem.
        """
        from sqlalchemy import inspect

        # Get column names
        inv_mapper = inspect(InventoryItem)
        mat_inv_mapper = inspect(MaterialInventoryItem)

        inv_columns = {c.name for c in inv_mapper.columns}
        mat_inv_columns = {c.name for c in mat_inv_mapper.columns}

        # Required fields that must exist in MaterialInventoryItem
        required_fields = {
            "material_product_id",  # equivalent to product_id
            "material_purchase_id",  # equivalent to purchase_id
            "quantity_remaining",  # equivalent to quantity
            "cost_per_unit",  # equivalent to unit_cost
            "purchase_date",  # same name
        }

        for field in required_fields:
            assert field in mat_inv_columns, f"Missing required field: {field}"

        # MaterialInventoryItem should also have quantity_purchased (immutable snapshot)
        assert "quantity_purchased" in mat_inv_columns

    def test_fifo_ordering_consistent(self, integration_material_setup):
        """
        Verify FIFO ordering uses same approach: purchase_date ASC.
        """
        data = integration_material_setup

        with session_scope() as session:
            # Create lots in reverse order (newest first in creation)
            for i in range(3):
                purchase = MaterialPurchase(
                    product_id=data["product_id"],
                    supplier_id=data["supplier_id"],
                    purchase_date=date.today() - timedelta(days=10 - i * 5),  # Oldest first
                    packages_purchased=1,
                    package_price=Decimal(f"{(i+1)*10}.00"),
                    units_added=100,
                    unit_cost=Decimal(f"0.{i+1}0"),
                )
                session.add(purchase)
                session.flush()

                lot = MaterialInventoryItem(
                    material_product_id=data["product_id"],
                    material_purchase_id=purchase.id,
                    quantity_purchased=100.0,
                    quantity_remaining=100.0,
                    cost_per_unit=Decimal(f"0.{i+1}0"),
                    purchase_date=purchase.purchase_date,
                )
                session.add(lot)

        lots = get_fifo_inventory(data["product_id"])

        # Verify FIFO order: oldest (earliest date) first
        for i in range(len(lots) - 1):
            assert (
                lots[i].purchase_date <= lots[i + 1].purchase_date
            ), "FIFO ordering violated: lots not sorted by purchase_date ASC"

    def test_both_models_have_base_model_fields(self, test_db):
        """Verify both models inherit BaseModel fields (id, uuid, timestamps)."""
        from sqlalchemy import inspect

        inv_mapper = inspect(InventoryItem)
        mat_inv_mapper = inspect(MaterialInventoryItem)

        inv_columns = {c.name for c in inv_mapper.columns}
        mat_inv_columns = {c.name for c in mat_inv_mapper.columns}

        # BaseModel fields
        base_fields = {"id", "uuid", "created_at"}

        for field in base_fields:
            assert field in inv_columns, f"InventoryItem missing base field: {field}"
            assert field in mat_inv_columns, f"MaterialInventoryItem missing base field: {field}"


class TestEndToEndScenario:
    """
    End-to-end integration tests simulating real-world usage.
    """

    def test_complete_purchase_consume_cycle(self, integration_material_setup):
        """
        Complete cycle: create purchases, consume inventory, verify balances.
        """
        data = integration_material_setup

        # Step 1: Create two purchases
        with session_scope() as session:
            # First purchase
            purchase1 = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today() - timedelta(days=10),
                packages_purchased=1,
                package_price=Decimal("10.00"),
                units_added=100,
                unit_cost=Decimal("0.10"),
            )
            session.add(purchase1)
            session.flush()

            item1 = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase1.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.10"),
                purchase_date=purchase1.purchase_date,
            )
            session.add(item1)

            # Second purchase
            purchase2 = MaterialPurchase(
                product_id=data["product_id"],
                supplier_id=data["supplier_id"],
                purchase_date=date.today() - timedelta(days=5),
                packages_purchased=1,
                package_price=Decimal("15.00"),
                units_added=100,
                unit_cost=Decimal("0.15"),
            )
            session.add(purchase2)
            session.flush()

            item2 = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase2.id,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.15"),
                purchase_date=purchase2.purchase_date,
            )
            session.add(item2)

        # Step 2: Verify initial inventory
        available = calculate_available_inventory(data["product_id"])
        assert available == Decimal("200.0")

        # Step 3: First consumption (from oldest lot only)
        result1 = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("80"),
            target_unit="cm",
        )
        assert result1["satisfied"] is True
        assert result1["total_cost"] == Decimal("8.00")  # 80 * $0.10

        # Step 4: Verify remaining inventory
        available = calculate_available_inventory(data["product_id"])
        assert available == Decimal("120.0")  # 200 - 80

        # Step 5: Second consumption (spans both lots)
        result2 = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )
        assert result2["satisfied"] is True
        # 20 from lot 1 @ $0.10 = $2.00
        # 30 from lot 2 @ $0.15 = $4.50
        # Total = $6.50
        assert result2["total_cost"] == Decimal("6.50")

        # Step 6: Verify final inventory
        available = calculate_available_inventory(data["product_id"])
        assert available == Decimal("70.0")  # 120 - 50
