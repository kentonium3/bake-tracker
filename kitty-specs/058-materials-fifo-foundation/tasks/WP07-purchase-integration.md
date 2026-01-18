---
work_package_id: "WP07"
subtasks:
  - "T029"
  - "T030"
  - "T031"
  - "T032"
title: "Purchase Integration"
phase: "Phase 3 - Integration"
lane: "doing"
assignee: "claude-opus"
agent: "claude-opus"
shell_pid: "29058"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP01", "WP04"]
history:
  - timestamp: "2026-01-18T18:06:18Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-18T21:30:00Z"
    lane: "done"
    agent: "claude-opus"
    shell_pid: ""
    action: "Review passed: MaterialPurchaseService integration with FIFO inventory"
---

# Work Package Prompt: WP07 – Purchase Integration

## Implementation Command

```bash
spec-kitty implement WP07 --base WP01
```

**Note**: Also requires WP04 (unit converter) to be complete.

## Objectives & Success Criteria

Update material purchase service to create MaterialInventoryItem atomically on purchase.

**Success Criteria**:
- Recording a purchase creates a MaterialInventoryItem in the same transaction
- Unit conversion converts imperial input to metric base units
- cost_per_unit calculated and stored correctly
- Old weighted average logic removed
- quantity_purchased and cost_per_unit are immutable snapshots

## Context & Constraints

**Reference Documents**:
- `kitty-specs/058-materials-fifo-foundation/data-model.md` - Purchase→Inventory flow
- `kitty-specs/058-materials-fifo-foundation/spec.md` - User Story 1 acceptance criteria
- `src/services/material_purchase_service.py` - Current implementation to modify

**Key Constraints**:
- Atomic transaction: purchase and inventory item created together
- Unit conversion: 100 feet → 3048 cm; $15/100ft → $0.00492/cm
- Purchase is immutable after creation

**Example from Data Model**:
```
User records MaterialPurchase:
    - packages_purchased: 2
    - package_price: $15.00
    - units_added: 200 (feet)

Convert to base units:
    - 200 feet × 30.48 = 6096 cm
    - $0.15/foot ÷ 30.48 = $0.00492/cm

Create MaterialInventoryItem:
    - quantity_purchased: 6096 (cm)
    - quantity_remaining: 6096 (cm)
    - cost_per_unit: 0.00492 ($/cm)
```

## Subtasks & Detailed Guidance

### Subtask T029 – Update material_purchase_service to create MaterialInventoryItem

**Purpose**: Create inventory item atomically with purchase.

**Steps**:
1. Open `src/services/material_purchase_service.py`
2. Find the function that creates MaterialPurchase (likely `record_purchase` or similar)
3. Add import for MaterialInventoryItem and unit converter:
```python
from ..models import MaterialInventoryItem
from .material_unit_converter import convert_to_base_units
```

4. After creating MaterialPurchase and flushing to get ID, create MaterialInventoryItem:
```python
# Convert units_added to base units (cm)
product = session.query(MaterialProduct).options(
    joinedload(MaterialProduct.material)
).filter_by(id=product_id).first()

base_unit_type = product.material.base_unit_type
package_unit = product.package_unit

# Convert quantity to base units
success, qty_base, error = convert_to_base_units(
    Decimal(str(units_added)),
    package_unit,
    base_unit_type,
)
if not success:
    raise ValidationError([error])

# Calculate cost per base unit
# unit_cost from purchase is per package_unit, convert to per base_unit
# cost_per_base = unit_cost / conversion_factor
success, one_unit_in_base, _ = convert_to_base_units(
    Decimal("1"),
    package_unit,
    base_unit_type,
)
cost_per_base_unit = Decimal(str(unit_cost)) / one_unit_in_base

# Create inventory item in same transaction
inventory_item = MaterialInventoryItem(
    material_product_id=product_id,
    material_purchase_id=purchase.id,
    quantity_purchased=float(qty_base),
    quantity_remaining=float(qty_base),
    cost_per_unit=cost_per_base_unit,
    purchase_date=purchase.purchase_date,
)
session.add(inventory_item)
session.flush()
```

**Files**:
- Edit: `src/services/material_purchase_service.py`

**Parallel?**: No (core change, T030-T31 follow)

**Notes**:
- Ensure same session is used for atomicity
- purchase.id must be obtained via flush before creating inventory_item

### Subtask T030 – Remove _update_inventory_on_purchase() weighted average logic

**Purpose**: Remove deprecated weighted average cost calculation.

**Steps**:
1. In `material_purchase_service.py`, find the function `_update_inventory_on_purchase()` or similar that updates MaterialProduct.current_inventory and weighted_avg_cost
2. Remove or comment out the entire function
3. Remove any calls to this function from the purchase recording flow
4. The old logic looked something like:
```python
# REMOVE THIS LOGIC
def _update_inventory_on_purchase(product_id, units_added, unit_cost, session):
    product = session.query(MaterialProduct).filter_by(id=product_id).first()
    old_total = product.current_inventory * product.weighted_avg_cost
    new_total = units_added * unit_cost
    product.current_inventory += units_added
    product.weighted_avg_cost = (old_total + new_total) / product.current_inventory
```

**Files**:
- Edit: `src/services/material_purchase_service.py`

**Parallel?**: No (same file as T029)

**Notes**:
- This is safe because WP02 removes the fields from MaterialProduct
- The new FIFO approach calculates cost from inventory items

### Subtask T031 – Add unit conversion on purchase

**Purpose**: Ensure all purchases convert imperial inputs to metric base units.

**Steps**:
1. Verify that T029 implementation handles unit conversion correctly
2. Add validation that package_unit is compatible with material's base_unit_type:
```python
from .material_unit_converter import validate_unit_compatibility

# At start of purchase recording
is_valid, error = validate_unit_compatibility(
    product.package_unit,
    product.material.base_unit_type,
)
if not is_valid:
    raise ValidationError([error])
```

3. Document the conversion in function docstring:
```python
"""
Records a material purchase and creates inventory item.

Conversion logic:
- quantity is converted from package_unit to base_unit (cm)
- unit_cost is converted from per-package_unit to per-base_unit
- Example: 100 feet @ $15 → 3048 cm @ $0.00492/cm
"""
```

**Files**:
- Edit: `src/services/material_purchase_service.py`

**Parallel?**: No (same file as T029-T030)

### Subtask T032 – Add purchase→inventory integration tests

**Purpose**: Verify the complete purchase flow creates correct inventory items.

**Steps**:
1. Create or update test file for purchase service:

```python
"""Tests for material purchase to inventory integration."""

import pytest
from decimal import Decimal
from datetime import date

from src.services.database import session_scope
from src.models import (
    MaterialProduct,
    MaterialPurchase,
    MaterialInventoryItem,
)
# Import purchase service function
from src.services.material_purchase_service import record_material_purchase


class TestPurchaseCreatesInventoryItem:
    """Tests for purchase → inventory item creation."""

    def test_purchase_creates_inventory_item(self, setup_material_data):
        """Verify purchase creates MaterialInventoryItem."""
        result = record_material_purchase(
            product_id=setup_material_data["product_id"],
            supplier_id=setup_material_data["supplier_id"],
            packages_purchased=2,
            package_price=Decimal("15.00"),
            purchase_date=date.today(),
        )

        # Verify inventory item created
        with session_scope() as session:
            items = session.query(MaterialInventoryItem).filter_by(
                material_product_id=setup_material_data["product_id"]
            ).all()
            assert len(items) == 1

            item = items[0]
            assert item.material_purchase_id is not None
            assert item.quantity_purchased > 0
            assert item.quantity_remaining == item.quantity_purchased
            assert item.cost_per_unit > 0

    def test_purchase_converts_feet_to_cm(self, setup_material_data):
        """Verify imperial units converted to metric base units."""
        # Product has package_unit='feet'
        result = record_material_purchase(
            product_id=setup_material_data["product_id"],
            supplier_id=setup_material_data["supplier_id"],
            packages_purchased=1,
            package_price=Decimal("15.00"),
            purchase_date=date.today(),
        )

        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(
                material_product_id=setup_material_data["product_id"]
            ).first()

            # 100 feet = 3048 cm
            assert abs(item.quantity_purchased - 3048.0) < 1.0

    def test_purchase_calculates_cost_per_base_unit(self, setup_material_data):
        """Verify cost converted to per-base-unit."""
        result = record_material_purchase(
            product_id=setup_material_data["product_id"],
            supplier_id=setup_material_data["supplier_id"],
            packages_purchased=1,
            package_price=Decimal("15.00"),  # $15 for 100 feet
            purchase_date=date.today(),
        )

        with session_scope() as session:
            item = session.query(MaterialInventoryItem).filter_by(
                material_product_id=setup_material_data["product_id"]
            ).first()

            # $15/100ft = $0.15/ft = $0.15/30.48 = ~$0.00492/cm
            expected_cost = Decimal("0.15") / Decimal("30.48")
            actual_cost = Decimal(str(item.cost_per_unit))
            assert abs(actual_cost - expected_cost) < Decimal("0.0001")

    def test_purchase_atomicity_rollback(self, setup_material_data):
        """Verify failed purchase doesn't create orphan inventory item."""
        # This test would force an error after purchase but before inventory
        # Both should be rolled back together
        pass  # Implementation depends on how errors are handled
```

**Files**:
- Create or edit: `src/tests/test_material_purchase_integration.py`

**Parallel?**: No (must follow T029-T031)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Atomicity failure | Use single session, flush not commit until end |
| Unit conversion errors | Validate compatibility before conversion |
| Cost precision loss | Use Decimal throughout calculation |

## Definition of Done Checklist

- [ ] Purchase service imports MaterialInventoryItem and unit converter
- [ ] Purchase creates MaterialInventoryItem atomically
- [ ] Units converted from package_unit to base units (cm)
- [ ] Cost per unit calculated and stored correctly
- [ ] Weighted average logic removed
- [ ] Unit compatibility validated before purchase
- [ ] Integration tests pass
- [ ] Manual test: create purchase, verify inventory item exists

## Review Guidance

**Key acceptance checkpoints**:
1. Verify atomic transaction: purchase and inventory item created together
2. Verify unit conversion math: 100 feet = 3048 cm
3. Verify cost math: $15/100ft → $0.00492/cm
4. Verify no reference to current_inventory or weighted_avg_cost
5. Verify inventory item has correct purchase_date

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
- 2026-01-18T19:20:31Z – gemini – lane=for_review – T029-T032 complete: Purchase creates inventory item
- 2026-01-18T20:07:17Z – claude-opus – lane=done – Review passed: MaterialPurchaseService integration with FIFO inventory
- 2026-01-18T21:34:53Z – claude-opus – shell_pid=29058 – lane=doing – Started review via workflow command
