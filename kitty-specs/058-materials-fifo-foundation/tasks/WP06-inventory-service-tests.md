---
work_package_id: "WP06"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "MaterialInventoryService Tests"
phase: "Phase 2 - Services"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP05"]
history:
  - timestamp: "2026-01-18T18:06:18Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – MaterialInventoryService Tests

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

## Objectives & Success Criteria

Achieve >70% test coverage for MaterialInventoryService (constitutional requirement).

**Success Criteria**:
- All service functions have unit tests
- FIFO algorithm tested with multi-lot scenarios
- Edge cases covered (zero inventory, shortfall, donated materials)
- pytest passes with coverage report >70%

## Context & Constraints

**Reference Documents**:
- `kitty-specs/058-materials-fifo-foundation/spec.md` - Acceptance scenarios
- `src/tests/` - Existing test patterns to follow
- Constitution: Service layer must have >70% coverage

**Key Test Scenarios from Spec**:
1. Two lots: Lot A (100cm @ $0.10), Lot B (100cm @ $0.15) - consume 50cm → $5.00 from A only
2. Lot A (30cm remaining), Lot B (100cm) - consume 50cm → 30cm from A + 20cm from B = $6.00

## Subtasks & Detailed Guidance

### Subtask T022 – Create test file structure

**Purpose**: Set up test file with fixtures and imports.

**Steps**:
1. Create `src/tests/test_material_inventory_service.py`:

```python
"""Tests for material inventory service FIFO operations."""

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
)


@pytest.fixture
def setup_material_data():
    """Create test material hierarchy and return cleanup function."""
    with session_scope() as session:
        # Create supplier
        supplier = Supplier(name="Test Supplier", slug="test-supplier")
        session.add(supplier)

        # Create category hierarchy
        category = MaterialCategory(name="Test Category", slug="test-category")
        session.add(category)
        session.flush()

        subcategory = MaterialSubcategory(
            category_id=category.id,
            name="Test Subcategory",
            slug="test-subcategory",
        )
        session.add(subcategory)
        session.flush()

        # Create material with linear_cm base type
        material = Material(
            subcategory_id=subcategory.id,
            name="Test Ribbon",
            slug="test-ribbon",
            base_unit_type="linear_cm",
        )
        session.add(material)
        session.flush()

        # Create product
        product = MaterialProduct(
            material_id=material.id,
            supplier_id=supplier.id,
            name="100ft Red Ribbon",
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
def setup_two_lots(setup_material_data):
    """Create two inventory lots for FIFO testing."""
    data = setup_material_data
    with session_scope() as session:
        # Older lot - purchased 10 days ago
        lot_a = MaterialInventoryItem(
            material_product_id=data["product_id"],
            material_purchase_id=None,  # Will be set if needed
            quantity_purchased=100.0,  # 100 cm
            quantity_remaining=100.0,
            cost_per_unit=Decimal("0.10"),  # $0.10/cm
            purchase_date=date.today() - timedelta(days=10),
        )
        session.add(lot_a)

        # Newer lot - purchased 5 days ago
        lot_b = MaterialInventoryItem(
            material_product_id=data["product_id"],
            material_purchase_id=None,
            quantity_purchased=100.0,  # 100 cm
            quantity_remaining=100.0,
            cost_per_unit=Decimal("0.15"),  # $0.15/cm
            purchase_date=date.today() - timedelta(days=5),
        )
        session.add(lot_b)
        session.flush()

        return {
            **data,
            "lot_a_id": lot_a.id,
            "lot_b_id": lot_b.id,
        }
```

**Files**:
- Create: `src/tests/test_material_inventory_service.py`

**Parallel?**: No (foundation for other tests)

### Subtask T023 – Test get_fifo_inventory() ordering

**Purpose**: Verify lots are returned in correct FIFO order.

**Steps**:
1. Add test class:

```python
class TestGetFifoInventory:
    """Tests for get_fifo_inventory function."""

    def test_returns_lots_ordered_by_purchase_date(self, setup_two_lots):
        """Verify oldest lots returned first."""
        lots = get_fifo_inventory(setup_two_lots["product_id"])

        assert len(lots) == 2
        # First lot should be older (purchased 10 days ago)
        assert lots[0].purchase_date < lots[1].purchase_date

    def test_excludes_empty_lots(self, setup_two_lots):
        """Verify depleted lots are excluded."""
        # Deplete lot A
        with session_scope() as session:
            lot_a = session.query(MaterialInventoryItem).filter_by(
                id=setup_two_lots["lot_a_id"]
            ).first()
            lot_a.quantity_remaining = 0.0

        lots = get_fifo_inventory(setup_two_lots["product_id"])
        assert len(lots) == 1
        assert lots[0].id == setup_two_lots["lot_b_id"]

    def test_returns_empty_for_no_inventory(self, setup_material_data):
        """Verify empty list when no inventory exists."""
        lots = get_fifo_inventory(setup_material_data["product_id"])
        assert lots == []
```

**Files**:
- Edit: `src/tests/test_material_inventory_service.py`

**Parallel?**: Yes

### Subtask T024 – Test calculate_available_inventory()

**Purpose**: Verify correct aggregation of available quantities.

**Steps**:
1. Add test class:

```python
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

    def test_returns_zero_for_no_inventory(self, setup_material_data):
        """Verify zero when no inventory exists."""
        available = calculate_available_inventory(setup_material_data["product_id"])
        assert available == Decimal("0")
```

**Files**:
- Edit: `src/tests/test_material_inventory_service.py`

**Parallel?**: Yes

### Subtask T025 – Test consume_material_fifo() single-lot scenario

**Purpose**: Verify basic consumption from a single lot.

**Steps**:
1. Add test class:

```python
class TestConsumeMaterialFifoSingleLot:
    """Tests for consume_material_fifo with single lot scenarios."""

    def test_consumes_from_single_lot(self, setup_two_lots):
        """Spec scenario 1: Consume 50cm from 100cm lot A → $5.00."""
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
```

**Files**:
- Edit: `src/tests/test_material_inventory_service.py`

**Parallel?**: Yes

### Subtask T026 – Test consume_material_fifo() multi-lot scenario

**Purpose**: Verify FIFO consumption spans multiple lots correctly.

**Steps**:
1. Add test class:

```python
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
```

**Files**:
- Edit: `src/tests/test_material_inventory_service.py`

**Parallel?**: Yes

### Subtask T027 – Test consume_material_fifo() shortfall scenario

**Purpose**: Verify correct handling when insufficient inventory.

**Steps**:
1. Add test class:

```python
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

    def test_shortfall_with_empty_inventory(self, setup_material_data):
        """Verify full shortfall when no inventory exists."""
        result = consume_material_fifo(
            material_product_id=setup_material_data["product_id"],
            quantity_needed=Decimal("100"),
            target_unit="cm",
        )

        assert result["satisfied"] is False
        assert result["consumed"] == Decimal("0")
        assert result["shortfall"] == Decimal("100")
        assert result["total_cost"] == Decimal("0")

    def test_zero_cost_donated_materials(self, setup_material_data):
        """Verify $0 cost materials (donations) work correctly."""
        # Create a lot with $0 cost
        with session_scope() as session:
            lot = MaterialInventoryItem(
                material_product_id=setup_material_data["product_id"],
                material_purchase_id=None,
                quantity_purchased=100.0,
                quantity_remaining=100.0,
                cost_per_unit=Decimal("0.00"),  # Donated
                purchase_date=date.today(),
            )
            session.add(lot)

        result = consume_material_fifo(
            material_product_id=setup_material_data["product_id"],
            quantity_needed=Decimal("50"),
            target_unit="cm",
        )

        assert result["satisfied"] is True
        assert result["total_cost"] == Decimal("0.00")  # Free!
```

**Files**:
- Edit: `src/tests/test_material_inventory_service.py`

**Parallel?**: Yes

### Subtask T028 – Test validate_inventory_availability()

**Purpose**: Verify availability validation function.

**Steps**:
1. Add test class:

```python
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
        """Verify validation doesn't consume inventory."""
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
```

**Files**:
- Edit: `src/tests/test_material_inventory_service.py`

**Parallel?**: Yes

## Test Strategy

Run tests with coverage:
```bash
pytest src/tests/test_material_inventory_service.py -v --cov=src/services/material_inventory_service --cov-report=term-missing
```

Expected: >70% coverage

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Test isolation | Use session rollback, fixtures for setup/teardown |
| Floating-point comparison | Use Decimal for precise comparisons |
| Fixture cleanup | Ensure fixtures clean up test data |

## Definition of Done Checklist

- [ ] Test file created with all test classes
- [ ] get_fifo_inventory() ordering tests pass
- [ ] calculate_available_inventory() aggregation tests pass
- [ ] consume_material_fifo() single-lot tests pass
- [ ] consume_material_fifo() multi-lot FIFO tests pass
- [ ] consume_material_fifo() shortfall tests pass
- [ ] validate_inventory_availability() tests pass
- [ ] All tests pass: `pytest src/tests/test_material_inventory_service.py -v`
- [ ] Coverage >70%

## Review Guidance

**Key acceptance checkpoints**:
1. Verify spec acceptance scenarios are tested (50cm from A only, 30+20 split)
2. Verify FIFO order is tested (oldest consumed first)
3. Verify dry_run doesn't modify database
4. Verify edge cases: zero inventory, donated materials ($0 cost)
5. Run coverage and verify >70%

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
