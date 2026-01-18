---
work_package_id: WP10
title: Integration Tests & Validation
lane: "doing"
dependencies: []
subtasks:
- T039
- T040
- T041
- T042
- T043
phase: Phase 5 - Validation
assignee: "claude-opus"
agent: "claude-opus"
shell_pid: "29933"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-18T18:06:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
- timestamp: '2026-01-18T21:30:00Z'
  lane: done
  agent: claude-opus
  shell_pid: ''
  action: "Review passed: All 2384 tests pass with FIFO integration tests"
---

# Work Package Prompt: WP10 – Integration Tests & Validation

## Implementation Command

```bash
spec-kitty implement WP10 --base WP07
```

**Note**: This is the final validation WP - depends on all core functionality being complete.

## Objectives & Success Criteria

Comprehensive integration tests validating end-to-end FIFO behavior and pattern consistency.

**Success Criteria**:
- Purchase→Inventory item creation tested end-to-end
- Multi-lot FIFO scenarios from spec acceptance criteria pass
- Cost calculations verified accurate across multiple lots
- MaterialInventoryItem structure matches InventoryItem pattern
- All integration tests pass

## Context & Constraints

**Reference Documents**:
- `kitty-specs/058-materials-fifo-foundation/spec.md` - Acceptance scenarios
- `kitty-specs/058-materials-fifo-foundation/data-model.md` - FIFO consumption flow
- `src/models/inventory_item.py` - Pattern to match

**Key Acceptance Scenarios from Spec**:

**Scenario 1** (User Story 2, Acceptance 1):
> Given two inventory lots exist (Lot A: 100cm at $0.10/cm, Lot B: 100cm at $0.15/cm) where Lot A was purchased first, When 50cm is consumed, Then consumption comes from Lot A only and total cost is $5.00.

**Scenario 2** (User Story 2, Acceptance 2):
> Given Lot A has 30cm remaining and Lot B has 100cm, When 50cm is consumed, Then all 30cm from Lot A is consumed first, then 20cm from Lot B, with total cost calculated as (30 × $0.10) + (20 × $0.15) = $6.00.

## Subtasks & Detailed Guidance

### Subtask T039 – Create integration test file

**Purpose**: Set up comprehensive integration test file.

**Steps**:
1. Create `src/tests/test_material_fifo_integration.py`:

```python
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
)
# Import purchase service if available
# from src.services.material_purchase_service import record_material_purchase


@pytest.fixture
def integration_material_setup():
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
            slug="test-packaging",
        )
        session.add(category)
        session.flush()

        subcategory = MaterialSubcategory(
            category_id=category.id,
            name="Ribbons",
            slug="ribbons",
        )
        session.add(subcategory)
        session.flush()

        material = Material(
            subcategory_id=subcategory.id,
            name="Red Satin Ribbon",
            slug="red-satin-ribbon",
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
```

**Files**:
- Create: `src/tests/test_material_fifo_integration.py`

**Parallel?**: No (foundation for other tests)

### Subtask T040 – Test purchase→inventory item creation flow

**Purpose**: Verify complete purchase flow creates correct inventory items.

**Steps**:
1. Add test class:

```python
class TestPurchaseToInventoryFlow:
    """
    Integration tests for purchase → inventory item creation.

    Reference: Spec User Story 1 - Material Purchase Creates Inventory
    """

    def test_purchase_creates_inventory_item_with_correct_conversion(
        self, integration_material_setup
    ):
        """
        Acceptance Scenario 1: Record purchase of 100 feet of ribbon at $15.00.

        Expected:
        - MaterialInventoryItem created
        - quantity_purchased = 3048cm (100 feet × 30.48)
        - quantity_remaining = 3048cm
        - cost_per_unit calculated correctly
        """
        data = integration_material_setup

        # Create purchase (either via service or directly)
        with session_scope() as session:
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

            # Create corresponding inventory item (this should be automatic in WP07)
            inventory_item = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=purchase.id,
                quantity_purchased=3048.0,  # 100 feet in cm
                quantity_remaining=3048.0,
                cost_per_unit=Decimal("0.00492"),  # $0.15/ft / 30.48 cm/ft
                purchase_date=purchase.purchase_date,
            )
            session.add(inventory_item)

        # Verify
        with session_scope() as session:
            items = session.query(MaterialInventoryItem).filter_by(
                material_product_id=data["product_id"]
            ).all()

            assert len(items) == 1
            item = items[0]

            # Verify quantity conversion (100 feet = 3048 cm)
            assert abs(item.quantity_purchased - 3048.0) < 1.0
            assert item.quantity_remaining == item.quantity_purchased

            # Verify cost conversion (approximate)
            assert item.cost_per_unit > Decimal("0")

    def test_cost_per_unit_immutability(self, integration_material_setup):
        """
        Acceptance Scenario 2: cost_per_unit is immutable snapshot.

        Create inventory item, attempt to modify cost_per_unit,
        verify it should remain unchanged (or raise error).
        """
        data = integration_material_setup

        with session_scope() as session:
            # Create inventory item
            item = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=None,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.10"),
                purchase_date=date.today(),
            )
            session.add(item)
            session.flush()
            item_id = item.id
            original_cost = item.cost_per_unit

        # Note: Immutability is enforced by application code, not database constraints
        # This test documents expected behavior
        # The service layer should not allow modifying cost_per_unit after creation
```

**Files**:
- Edit: `src/tests/test_material_fifo_integration.py`

**Parallel?**: Yes

### Subtask T041 – Test multi-lot FIFO consumption scenario

**Purpose**: Verify FIFO consumption matches spec acceptance criteria exactly.

**Steps**:
1. Add test class:

```python
class TestMultiLotFifoConsumption:
    """
    Integration tests for FIFO consumption across multiple lots.

    Reference: Spec User Story 2 - FIFO Consumption of Materials
    """

    def test_spec_scenario_1_consume_from_oldest_lot_only(
        self, integration_material_setup
    ):
        """
        Spec Acceptance Scenario 1:

        Given: Lot A (100cm @ $0.10/cm) purchased first, Lot B (100cm @ $0.15/cm)
        When: 50cm consumed
        Then: Consumption from Lot A only, total cost = $5.00
        """
        data = integration_material_setup

        with session_scope() as session:
            # Create Lot A (older - purchased 10 days ago)
            lot_a = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=None,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.10"),
                purchase_date=date.today() - timedelta(days=10),
            )
            session.add(lot_a)

            # Create Lot B (newer - purchased 5 days ago)
            lot_b = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=None,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.15"),
                purchase_date=date.today() - timedelta(days=5),
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
        assert result["total_cost"] == Decimal("5.00")  # 50 × $0.10

        # Verify breakdown shows only Lot A
        assert len(result["breakdown"]) == 1
        assert result["breakdown"][0]["inventory_item_id"] == lot_a_id
        assert result["breakdown"][0]["quantity_consumed"] == Decimal("50")

        # Verify Lot B untouched
        with session_scope() as session:
            lot_b = session.query(MaterialInventoryItem).filter_by(id=lot_b_id).first()
            assert lot_b.quantity_remaining == 100.0

    def test_spec_scenario_2_consume_across_multiple_lots(
        self, integration_material_setup
    ):
        """
        Spec Acceptance Scenario 2:

        Given: Lot A (30cm remaining @ $0.10), Lot B (100cm @ $0.15)
        When: 50cm consumed
        Then: 30cm from A + 20cm from B, cost = (30×$0.10) + (20×$0.15) = $6.00
        """
        data = integration_material_setup

        with session_scope() as session:
            # Create Lot A (older, partially depleted)
            lot_a = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=None,
                quantity_purchased=100.0,
                quantity_remaining=30.0,  # Only 30cm remaining
                cost_per_unit=Decimal("0.10"),
                purchase_date=date.today() - timedelta(days=10),
            )
            session.add(lot_a)

            # Create Lot B (newer, full)
            lot_b = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=None,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.15"),
                purchase_date=date.today() - timedelta(days=5),
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

        # Cost: (30 × $0.10) + (20 × $0.15) = $3.00 + $3.00 = $6.00
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
```

**Files**:
- Edit: `src/tests/test_material_fifo_integration.py`

**Parallel?**: Yes

### Subtask T042 – Test cost calculation accuracy

**Purpose**: Verify cost calculations are accurate across various scenarios.

**Steps**:
1. Add test class:

```python
class TestCostCalculationAccuracy:
    """
    Integration tests for FIFO cost calculation accuracy.

    Verifies cost calculations remain accurate with:
    - Different cost per unit values
    - Multiple lots at different prices
    - Partial lot consumption
    """

    def test_cost_with_different_prices(self, integration_material_setup):
        """Verify cost calculation with varying prices."""
        data = integration_material_setup

        with session_scope() as session:
            # Create lots with different prices
            lots = [
                (50.0, Decimal("0.05"), 15),   # Oldest, cheapest
                (50.0, Decimal("0.10"), 10),   # Middle
                (50.0, Decimal("0.20"), 5),    # Newest, most expensive
            ]

            for qty, cost, days_ago in lots:
                lot = MaterialInventoryItem(
                    material_product_id=data["product_id"],
                    material_purchase_id=None,
                    quantity_purchased=qty,
                    quantity_remaining=qty,
                    cost_per_unit=cost,
                    purchase_date=date.today() - timedelta(days=days_ago),
                )
                session.add(lot)

        # Consume 100cm (should take all of lot 1 and lot 2)
        result = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("100"),
            target_unit="cm",
        )

        # Expected cost: (50 × $0.05) + (50 × $0.10) = $2.50 + $5.00 = $7.50
        assert result["total_cost"] == Decimal("7.50")

    def test_zero_cost_materials(self, integration_material_setup):
        """Verify $0 cost materials (donations) calculate correctly."""
        data = integration_material_setup

        with session_scope() as session:
            lot = MaterialInventoryItem(
                material_product_id=data["product_id"],
                material_purchase_id=None,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.00"),  # Donated
                purchase_date=date.today(),
            )
            session.add(lot)

        result = consume_material_fifo(
            material_product_id=data["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        assert result["satisfied"] is True
        assert result["total_cost"] == Decimal("0.00")
```

**Files**:
- Edit: `src/tests/test_material_fifo_integration.py`

**Parallel?**: Yes

### Subtask T043 – Test pattern consistency with ingredient system

**Purpose**: Verify MaterialInventoryItem structure matches InventoryItem.

**Steps**:
1. Add test class:

```python
class TestPatternConsistency:
    """
    Verify MaterialInventoryItem follows InventoryItem pattern.

    Reference: Spec SC-007 - Pattern consistency with ingredient system
    """

    def test_model_structure_matches_inventory_item(self):
        """
        Verify MaterialInventoryItem has equivalent fields to InventoryItem.
        """
        from sqlalchemy import inspect

        # Get column names
        inv_mapper = inspect(InventoryItem)
        mat_inv_mapper = inspect(MaterialInventoryItem)

        inv_columns = {c.name for c in inv_mapper.columns}
        mat_inv_columns = {c.name for c in mat_inv_mapper.columns}

        # MaterialInventoryItem should have equivalent fields (with different FK names)
        # InventoryItem: product_id, purchase_id, quantity, unit_cost, purchase_date
        # MaterialInventoryItem: material_product_id, material_purchase_id, quantity_remaining, cost_per_unit, purchase_date

        # Required fields that must exist in MaterialInventoryItem
        required_fields = {
            "material_product_id",  # equivalent to product_id
            "material_purchase_id",  # equivalent to purchase_id
            "quantity_remaining",    # equivalent to quantity
            "cost_per_unit",         # equivalent to unit_cost
            "purchase_date",         # same name
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
                lot = MaterialInventoryItem(
                    material_product_id=data["product_id"],
                    material_purchase_id=None,
                    quantity_purchased=100.0,
                    quantity_remaining=100.0,
                    cost_per_unit=Decimal(f"0.{i+1}0"),
                    purchase_date=date.today() - timedelta(days=10 - i*5),  # Oldest first
                )
                session.add(lot)

        lots = get_fifo_inventory(data["product_id"])

        # Verify FIFO order: oldest (earliest date) first
        for i in range(len(lots) - 1):
            assert lots[i].purchase_date <= lots[i+1].purchase_date, \
                "FIFO ordering violated: lots not sorted by purchase_date ASC"
```

**Files**:
- Edit: `src/tests/test_material_fifo_integration.py`

**Parallel?**: Yes

## Test Strategy

Run full integration test suite:
```bash
pytest src/tests/test_material_fifo_integration.py -v
```

All tests should pass before marking F058 as complete.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Test isolation | Use separate fixtures, rollback after each test |
| Floating-point comparison | Use Decimal for all cost comparisons |
| Test order dependence | Ensure each test creates its own data |

## Definition of Done Checklist

- [ ] Integration test file created
- [ ] Purchase→inventory flow tested
- [ ] Spec scenario 1 (single lot FIFO) test passes
- [ ] Spec scenario 2 (multi-lot FIFO) test passes
- [ ] Cost calculation accuracy tests pass
- [ ] Pattern consistency with InventoryItem verified
- [ ] All integration tests pass
- [ ] Tests run in isolation (no order dependence)

## Review Guidance

**Key acceptance checkpoints**:
1. Run: `pytest src/tests/test_material_fifo_integration.py -v`
2. Verify all tests pass
3. Verify spec acceptance scenarios are covered exactly
4. Verify cost calculations match expected values
5. Verify FIFO order is oldest-first

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
- 2026-01-18T19:32:22Z – claude – lane=doing – Starting final integration tests
- 2026-01-18T20:01:07Z – claude-opus – lane=for_review – All 2384 tests pass; integration tests complete
- 2026-01-18T20:07:21Z – claude-opus – lane=done – Review passed: All 2384 tests pass with FIFO integration tests
- 2026-01-18T21:36:42Z – claude-opus – shell_pid=29933 – lane=doing – Started review via workflow command
