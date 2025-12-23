---
work_package_id: "WP05"
subtasks:
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "FIFO Verification and Final Testing"
phase: "Phase 4 - Testing"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - FIFO Verification and Final Testing

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Verify FIFO calculations work correctly with purchase-linked inventory, ensure purchase history queries function properly, and run full test suite to confirm no regressions.

**Success Criteria**:
- FIFO cost calculations use InventoryItem.unit_cost (populated from Purchase.unit_price)
- Integration test confirms FIFO accuracy with purchase-linked inventory
- Purchase history queries work correctly (sorted by date, filterable by supplier)
- All existing tests pass
- Service layer achieves >70% test coverage

**User Stories**: US3 (Accurate FIFO Cost Calculation), US4 (Purchase History Query)
**Success Criteria**: SC-004, SC-006

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/028-purchase-tracking-enhanced/spec.md` - US3, US4, SC-004, SC-006
- `kitty-specs/028-purchase-tracking-enhanced/plan.md` - Phase 4
- `CLAUDE.md` - FIFO accuracy as core principle

**Dependencies**:
- WP02: `add_to_inventory()` sets `unit_cost` from `unit_price`
- WP04: Migration ensures all items have purchase linkage

**Existing FIFO Implementation**:
- `src/services/inventory_item_service.py` - `consume_fifo()` function
- Uses `InventoryItem.unit_cost` for cost calculations

---

## Subtasks & Detailed Guidance

### Subtask T020 - Verify FIFO Uses unit_cost

**Purpose**: Confirm existing FIFO logic works with purchase-populated unit_cost.

**Steps**:
1. Read `src/services/inventory_item_service.py` - `consume_fifo()` function
2. Verify it uses `item.unit_cost` for cost calculations
3. Confirm no code path bypasses this (e.g., direct price_paid access)
4. Document any issues found

**Expected Behavior**:
```python
# In consume_fifo(), should see something like:
item_unit_cost = Decimal(str(item.unit_cost)) if item.unit_cost else Decimal("0.0")
# Cost calculation uses item_unit_cost
```

**Verification**:
- If using `item.unit_cost` - PASS (no changes needed)
- If using deprecated `price_paid` or other - needs update

**Files**: `src/services/inventory_item_service.py`
**Parallel?**: No - verification task

---

### Subtask T021 - Add Integration Test for FIFO

**Purpose**: Verify FIFO accuracy with purchase-linked inventory end-to-end.

**Test Case** (`src/tests/integration/test_fifo_with_purchases.py`):

```python
"""Integration test for FIFO with purchase-linked inventory."""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services import inventory_item_service
from src.models import InventoryItem, Purchase


class TestFIFOWithPurchases:
    """Verify FIFO calculations use purchase prices correctly."""

    def test_fifo_uses_purchase_prices(self, session, test_product, test_supplier):
        """
        Given: inventory added at different prices over time
        When: recipe consumes spanning multiple lots
        Then: cost calculation uses correct FIFO prices
        """
        # Add 10 units at $5.00 (January)
        inventory_item_service.add_to_inventory(
            product_id=test_product.id,
            quantity=10.0,
            supplier_id=test_supplier.id,
            unit_price=Decimal("5.00"),
            added_date=date.today() - timedelta(days=60),
            session=session,
        )

        # Add 10 units at $6.00 (February)
        inventory_item_service.add_to_inventory(
            product_id=test_product.id,
            quantity=10.0,
            supplier_id=test_supplier.id,
            unit_price=Decimal("6.00"),
            added_date=date.today() - timedelta(days=30),
            session=session,
        )

        # Consume 15 units (FIFO: 10 @ $5 + 5 @ $6 = $80)
        result = inventory_item_service.consume_fifo(
            product_id=test_product.id,
            quantity_needed=15.0,
            session=session,
        )

        # Verify cost calculation
        expected_cost = (10 * Decimal("5.00")) + (5 * Decimal("6.00"))  # $80.00
        assert result["total_cost"] == expected_cost

    def test_fifo_order_by_added_date(self, session, test_product, test_supplier):
        """FIFO consumes oldest inventory first."""
        # Add expensive first, cheap second
        inventory_item_service.add_to_inventory(
            product_id=test_product.id,
            quantity=5.0,
            supplier_id=test_supplier.id,
            unit_price=Decimal("10.00"),
            added_date=date.today() - timedelta(days=30),
            session=session,
        )

        inventory_item_service.add_to_inventory(
            product_id=test_product.id,
            quantity=5.0,
            supplier_id=test_supplier.id,
            unit_price=Decimal("5.00"),
            added_date=date.today(),
            session=session,
        )

        # Consume 3 units - should come from older $10.00 lot
        result = inventory_item_service.consume_fifo(
            product_id=test_product.id,
            quantity_needed=3.0,
            session=session,
        )

        assert result["total_cost"] == 3 * Decimal("10.00")  # $30.00

    def test_fifo_with_migrated_inventory(self, session, test_product, migrated_inventory_item):
        """FIFO works with migration-created purchases."""
        # migrated_inventory_item has purchase_id set by migration

        result = inventory_item_service.consume_fifo(
            product_id=test_product.id,
            quantity_needed=1.0,
            session=session,
        )

        # Should use unit_cost from migrated item
        assert result["total_cost"] == Decimal(str(migrated_inventory_item.unit_cost))
```

**Files**: `src/tests/integration/test_fifo_with_purchases.py`
**Parallel?**: Yes - can be written alongside T020

---

### Subtask T022 - Verify Purchase History Queries

**Purpose**: Confirm purchase history queries work per US4.

**Steps**:
1. Test `get_purchase_history()` in purchase_service (if exists) or purchase.py helpers
2. Verify results sorted by date (most recent first)
3. Verify filtering by supplier works
4. Add tests if needed

**Test Cases**:
```python
class TestPurchaseHistoryQueries:
    """Verify purchase history query functionality."""

    def test_history_sorted_by_date_descending(self, session, product_with_purchases):
        """History returns most recent first."""
        history = purchase_service.get_purchase_history(
            product_id=product_with_purchases.id,
            session=session
        )

        dates = [p["purchase_date"] for p in history]
        assert dates == sorted(dates, reverse=True)

    def test_history_filter_by_supplier(self, session, product_with_multi_supplier_purchases):
        """History can be filtered by supplier."""
        costco_history = purchase_service.get_purchase_history(
            product_id=product_with_multi_supplier_purchases.id,
            supplier_id=costco_supplier.id,
            session=session
        )

        assert all(p["supplier_id"] == costco_supplier.id for p in costco_history)
```

**Files**: `src/tests/services/test_purchase_service.py`
**Parallel?**: Yes - independent of T020, T021

---

### Subtask T023 - Run Full Test Suite

**Purpose**: Verify no regressions from F028 changes.

**Steps**:
1. Run full test suite: `pytest src/tests -v --cov=src`
2. Verify all tests pass
3. Check coverage meets >70% threshold
4. Document any failures

**Commands**:
```bash
# Run all tests with coverage
pytest src/tests -v --cov=src --cov-report=html

# Run specific service tests
pytest src/tests/services -v --cov=src/services

# Check coverage
pytest src/tests -v --cov=src --cov-fail-under=70
```

**Expected Result**:
- All tests pass
- Coverage >= 70% on service layer
- No warnings about deprecated patterns

**Files**: N/A (test execution)
**Parallel?**: No - final validation step

---

### Subtask T024 - Fix Broken Tests

**Purpose**: Address any test failures from signature changes.

**Potential Issues**:
1. Tests calling `add_to_inventory()` without new params
2. Tests expecting different return structure
3. Import path changes

**Fix Pattern**:
```python
# Old test (may break)
def test_old_add_inventory(self, session, product):
    result = add_to_inventory(product_id=product.id, quantity=10.0)

# Updated test
def test_new_add_inventory(self, session, product, supplier):
    result = add_to_inventory(
        product_id=product.id,
        quantity=10.0,
        supplier_id=supplier.id,        # NEW
        unit_price=Decimal("5.00"),     # NEW
        session=session
    )
```

**Files**: Various test files
**Parallel?**: No - depends on T023 results

---

## Test Strategy

**Coverage Goals**:
- Service layer: >70%
- Focus on: inventory_item_service, purchase_service

**Test Commands**:
```bash
# Full suite
pytest src/tests -v --cov=src

# Service layer only
pytest src/tests/services -v --cov=src/services --cov-report=term-missing

# Specific integration test
pytest src/tests/integration/test_fifo_with_purchases.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FIFO logic needs changes | Verify T020 first; unit_cost usage should be sufficient |
| Broken existing tests | T024 addresses; scope changes documented |
| Coverage threshold not met | Focus on untested paths; add targeted tests |

---

## Definition of Done Checklist

- [ ] FIFO verified to use InventoryItem.unit_cost
- [ ] Integration test passes for FIFO with purchases
- [ ] Purchase history queries work correctly
- [ ] Full test suite passes
- [ ] Service layer coverage >70%
- [ ] All broken tests fixed
- [ ] No regressions from F028 changes

---

## Review Guidance

**Verification Checkpoints**:
1. FIFO calculation matches spec example (10@$5 + 5@$6 = $80)
2. History sorted correctly (most recent first)
3. Coverage report shows >70% on services
4. No test failures in CI

---

## Activity Log

- 2025-12-22T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks.
- 2025-12-23T14:45:21Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-23T17:15:29Z – system – shell_pid= – lane=for_review – Moved to for_review
