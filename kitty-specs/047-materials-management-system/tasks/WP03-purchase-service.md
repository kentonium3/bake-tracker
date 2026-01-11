---
work_package_id: "WP03"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "Purchase Service - User Story 2"
phase: "Phase 1 - Core Services"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Purchase Service - User Story 2

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Implement purchase recording and inventory management with weighted average costing.

**User Story**: As a baker, I need to record material purchases so I know what I have on hand and what it cost.

**Success Criteria:**
- Can record purchases with package-level tracking
- Inventory updates atomically with purchase
- Weighted average cost recalculates correctly
- Manual inventory adjustments work (by count or percentage)
- All acceptance scenarios from spec.md User Story 2 pass

## Context & Constraints

**Reference Documents:**
- `kitty-specs/047-materials-management-system/spec.md` - User Story 2 acceptance scenarios
- `kitty-specs/047-materials-management-system/contracts/material_purchase_service.md` - Service interface
- `src/services/purchase_service.py` - Existing pattern (for food ingredients)
- `src/models/purchase.py` - Immutable purchase pattern

**Weighted Average Formula:**
```
new_avg = (current_qty * current_avg + added_qty * added_cost) / (current_qty + added_qty)
```

**Special Cases:**
- First purchase: new_avg = added_cost (no existing inventory)
- Zero added: new_avg = current_avg (unchanged)

**Dependencies:**
- WP01 (models)
- WP02 (catalog service for product retrieval)

## Subtasks & Detailed Guidance

### Subtask T017 - Implement record_purchase()
- **Purpose**: Record a material purchase transaction
- **File**: `src/services/material_purchase_service.py`
- **Parallel?**: No
- **Steps**:
  1. Create file with standard imports
  2. Implement `record_purchase(product_id, supplier_id, purchase_date, packages_purchased, package_price, notes=None, session=None)`
  3. Validate product_id exists
  4. Validate supplier_id exists
  5. Validate packages_purchased > 0
  6. Calculate units_added = packages_purchased * product.quantity_in_base_units
  7. Calculate unit_cost = package_price / product.quantity_in_base_units
  8. Create MaterialPurchase record
  9. Call inventory update (T019)
  10. Return created purchase

### Subtask T018 - Implement Weighted Average Calculation
- **Purpose**: Calculate new weighted average cost after purchase
- **File**: `src/services/material_purchase_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `calculate_weighted_average(current_quantity, current_avg_cost, added_quantity, added_unit_cost)`
  2. Handle special case: current_quantity == 0 returns added_unit_cost
  3. Handle special case: added_quantity == 0 returns current_avg_cost
  4. Use Decimal for precision: `(curr_qty * curr_avg + add_qty * add_cost) / (curr_qty + add_qty)`
  5. Return Decimal result
- **Example**:
  ```python
  # 200 units at $0.12 + 100 units at $0.15 = 300 units at $0.13
  result = calculate_weighted_average(200, Decimal("0.12"), 100, Decimal("0.15"))
  assert result == Decimal("0.13")
  ```

### Subtask T019 - Implement Inventory Update Logic
- **Purpose**: Update product inventory and cost atomically with purchase
- **File**: `src/services/material_purchase_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `_update_inventory_on_purchase(product, units_added, unit_cost, session)`
  2. Calculate new weighted average using T018
  3. Update `product.current_inventory += units_added`
  4. Update `product.weighted_avg_cost = new_avg`
  5. Ensure both updates happen in same transaction
- **Notes**: This is called by record_purchase(), not exposed directly

### Subtask T020 - Implement Inventory Adjustment
- **Purpose**: Allow manual inventory corrections
- **File**: `src/services/material_purchase_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `adjust_inventory(product_id, new_quantity=None, percentage=None, notes=None, session=None)`
  2. Validate exactly one of new_quantity or percentage provided
  3. If new_quantity: set `product.current_inventory = new_quantity`
  4. If percentage: set `product.current_inventory *= percentage` (0.0 to 1.0)
  5. Do NOT change weighted_avg_cost (cost remains unchanged)
  6. Return updated product
- **Example**:
  ```python
  # "50% remaining" halves inventory
  adjust_inventory(prod_id, percentage=0.5, session=session)
  ```

### Subtask T021 - Unit Conversion for Package Units
- **Purpose**: Convert package_unit to base units when creating products
- **File**: `src/services/material_purchase_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `convert_to_base_units(quantity, from_unit, base_unit_type)`
  2. For 'each': no conversion needed
  3. For 'linear_inches': convert feet (x12), yards (x36) to inches
  4. For 'square_inches': convert square_feet (x144) to square_inches
  5. Return converted quantity as float
- **Reference**: Check `src/services/unit_converter.py` for existing patterns

### Subtask T022 - Service Tests
- **Purpose**: Achieve >70% coverage
- **File**: `src/tests/test_material_purchase_service.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create test fixtures for product, supplier
  2. Test record_purchase creates purchase and updates inventory
  3. Test weighted average calculation (multiple scenarios)
  4. Test first purchase sets initial cost
  5. Test inventory adjustment by count
  6. Test inventory adjustment by percentage
  7. Test validation errors (negative packages, invalid product)

### Subtask T023 - Export Service
- **Purpose**: Make service available
- **File**: `src/services/__init__.py`
- **Parallel?**: No
- **Steps**:
  1. Add import for material_purchase_service
  2. Add to `__all__`

## Test Strategy

```python
import pytest
from decimal import Decimal
from src.services.material_purchase_service import (
    record_purchase, adjust_inventory, calculate_weighted_average
)

def test_first_purchase_sets_cost(db_session, sample_product, sample_supplier):
    """First purchase sets initial weighted average cost."""
    purchase = record_purchase(
        product_id=sample_product.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=2,  # 2 packs of 100 units = 200 units
        package_price=Decimal("12.00"),  # $12 per pack = $0.12/unit
        session=db_session
    )

    db_session.refresh(sample_product)
    assert sample_product.current_inventory == 200
    assert sample_product.weighted_avg_cost == Decimal("0.12")

def test_weighted_average_updates(db_session, sample_product_with_inventory):
    """Second purchase recalculates weighted average."""
    # Existing: 200 units at $0.12/unit
    # Adding: 100 units at $0.15/unit (package_price = $15 for 100 units)
    purchase = record_purchase(
        product_id=sample_product_with_inventory.id,
        supplier_id=sample_supplier.id,
        purchase_date=date.today(),
        packages_purchased=1,
        package_price=Decimal("15.00"),
        session=db_session
    )

    db_session.refresh(sample_product_with_inventory)
    assert sample_product_with_inventory.current_inventory == 300
    assert sample_product_with_inventory.weighted_avg_cost == Decimal("0.13")

def test_inventory_adjustment_percentage(db_session, sample_product_with_inventory):
    """50% adjustment halves inventory, keeps cost."""
    original_cost = sample_product_with_inventory.weighted_avg_cost
    adjust_inventory(sample_product_with_inventory.id, percentage=0.5, session=db_session)

    db_session.refresh(sample_product_with_inventory)
    assert sample_product_with_inventory.current_inventory == 100  # Was 200
    assert sample_product_with_inventory.weighted_avg_cost == original_cost
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Floating point precision | Use Decimal for all cost calculations |
| Division by zero | Handle first purchase (no existing inventory) specially |
| Concurrent purchases | Database transaction ensures atomicity |
| Negative inventory | Validation prevents negative quantities |

## Definition of Done Checklist

- [ ] record_purchase() creates MaterialPurchase and updates product
- [ ] Weighted average calculates correctly per acceptance scenarios
- [ ] First purchase sets initial cost correctly
- [ ] Inventory adjustment works by count and percentage
- [ ] Unit conversion handles linear and area measurements
- [ ] Tests achieve >70% coverage
- [ ] Service exported in `__init__.py`

## Review Guidance

**Reviewer should verify:**
1. Weighted average formula matches spec exactly
2. First purchase edge case handled correctly
3. Decimal used for all currency calculations
4. Adjustment does NOT change weighted_avg_cost
5. Unit conversion covers all base_unit_types

## Activity Log

- 2026-01-10T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-10T20:45:14Z – claude – lane=doing – Starting purchase service implementation with weighted average costing
- 2026-01-10T20:49:50Z – claude – lane=for_review – All 36 tests passing. Purchase recording, weighted avg costing, inventory adjustments, unit conversion complete
- 2026-01-11T01:06:27Z – claude – lane=done – Review passed: Purchase recording, weighted average costing, inventory adjustments complete. 36 tests passing.
