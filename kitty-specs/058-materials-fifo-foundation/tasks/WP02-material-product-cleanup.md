---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
title: "Schema Changes - MaterialProduct Cleanup"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: "claude-opus"
agent: "claude-opus"
shell_pid: "26146"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP01"]
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
    action: "Review passed: Deprecated fields removed from MaterialProduct"
---

# Work Package Prompt: WP02 – Schema Changes - MaterialProduct Cleanup

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Objectives & Success Criteria

Remove deprecated cost/inventory fields from MaterialProduct to enforce definition/instantiation separation per constitutional Principle III.

**Success Criteria**:
- `current_inventory` field removed from MaterialProduct
- `weighted_avg_cost` field removed from MaterialProduct
- `inventory_value` property removed
- Related CheckConstraints removed
- Model still functions correctly for catalog operations

## Context & Constraints

**Reference Documents**:
- `.kittify/memory/constitution.md` - Principle III: Definition/Instantiation separation
- `kitty-specs/058-materials-fifo-foundation/plan.md` - Breaking change documentation
- `kitty-specs/058-materials-fifo-foundation/data-model.md` - Fields to remove
- `kitty-specs/058-materials-fifo-foundation/research.md` - Code locations

**BREAKING CHANGE**: This removes fields from the model. Users MUST export their catalog data before applying this schema change.

**Key Constraints**:
- MaterialProduct becomes a pure definition (catalog) entity
- Cost and inventory data now live in MaterialInventoryItem
- to_dict() must be updated to remove inventory_value

## Subtasks & Detailed Guidance

### Subtask T005 – Remove current_inventory field from MaterialProduct

**Purpose**: Eliminate inventory state from the definition layer.

**Steps**:
1. Open `src/models/material_product.py`
2. Find and remove the line:
```python
current_inventory = Column(Float, nullable=False, default=0)
```
3. Remove from any `to_dict()` output if explicitly included

**Files**:
- Edit: `src/models/material_product.py`

**Parallel?**: No (affects same file as T006-T008)

**Notes**: The default=0 shows this was tracking mutable state - exactly what we're removing.

### Subtask T006 – Remove weighted_avg_cost field from MaterialProduct

**Purpose**: Eliminate weighted average costing; FIFO costing replaces it.

**Steps**:
1. In `src/models/material_product.py`, find and remove:
```python
weighted_avg_cost = Column(Numeric(10, 4), nullable=False, default=0)
```
2. Remove from any `to_dict()` output if explicitly included

**Files**:
- Edit: `src/models/material_product.py`

**Parallel?**: No (same file as T005)

**Notes**: FIFO costing from MaterialInventoryItem.cost_per_unit replaces this.

### Subtask T007 – Remove inventory_value property from MaterialProduct

**Purpose**: Remove computed property that depends on removed fields.

**Steps**:
1. In `src/models/material_product.py`, find and remove the property:
```python
@property
def inventory_value(self) -> Decimal:
    """
    Calculate total value of current inventory.

    Returns:
        current_inventory * weighted_avg_cost
    """
    return Decimal(str(self.current_inventory)) * self.weighted_avg_cost
```
2. In `to_dict()` method, find and remove:
```python
result["inventory_value"] = str(self.inventory_value)
```

**Files**:
- Edit: `src/models/material_product.py`

**Parallel?**: No (same file as T005-T006)

**Notes**: Inventory value will be calculated from MaterialInventoryItem in future features.

### Subtask T008 – Remove cost/inventory CheckConstraints

**Purpose**: Remove constraints that validate removed fields.

**Steps**:
1. In `src/models/material_product.py`, find the `__table_args__` tuple
2. Remove these two CheckConstraints:
```python
CheckConstraint(
    "current_inventory >= 0", name="ck_material_product_inventory_non_negative"
),
CheckConstraint("weighted_avg_cost >= 0", name="ck_material_product_cost_non_negative"),
```

**Files**:
- Edit: `src/models/material_product.py`

**Parallel?**: No (same file as T005-T007)

**Notes**: These constraints would fail since the columns no longer exist.

## Test Strategy

Verify MaterialProduct still works for catalog operations:

```python
def test_material_product_no_inventory_fields():
    """Verify deprecated fields are removed."""
    from src.models import MaterialProduct

    # Verify fields don't exist
    assert not hasattr(MaterialProduct, 'current_inventory')
    assert not hasattr(MaterialProduct, 'weighted_avg_cost')
    assert not hasattr(MaterialProduct, 'inventory_value')

def test_material_product_to_dict_no_inventory():
    """Verify to_dict doesn't include inventory fields."""
    product = MaterialProduct(
        material_id=1,
        name="Test Product",
        package_quantity=100,
        package_unit="feet",
        quantity_in_base_units=3048,
    )
    result = product.to_dict()
    assert "current_inventory" not in result
    assert "weighted_avg_cost" not in result
    assert "inventory_value" not in result
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss | Document that users must export before migration |
| Breaking existing code | Search codebase for usages of removed fields |
| Test failures | Update any tests that reference removed fields |

**Code locations that may reference removed fields** (from research.md):
- `src/services/material_purchase_service.py` - _update_inventory_on_purchase()
- `src/services/material_catalog_service.py` - list_products() output
- `src/ui/materials_tab.py` - inventory columns
- `src/services/denormalized_export_service.py` - inventory_value

## Definition of Done Checklist

- [ ] `current_inventory` field removed from MaterialProduct
- [ ] `weighted_avg_cost` field removed from MaterialProduct
- [ ] `inventory_value` property removed
- [ ] CheckConstraints removed from __table_args__
- [ ] `to_dict()` updated to exclude removed fields
- [ ] No import errors
- [ ] Basic model operations still work

## Review Guidance

**Key acceptance checkpoints**:
1. Grep codebase for "current_inventory" - should only appear in migration notes
2. Grep codebase for "weighted_avg_cost" - should only appear in migration notes
3. Verify MaterialProduct can still be instantiated
4. Verify to_dict() returns clean output without removed fields

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
- 2026-01-18T19:05:16Z – claude-opus – lane=doing – Starting MaterialProduct cleanup
- 2026-01-18T19:09:02Z – claude-opus – lane=for_review – T005-T008 complete: Removed deprecated fields
- 2026-01-18T20:06:36Z – claude-opus – shell_pid=9761 – lane=doing – Started review via workflow command
- 2026-01-18T20:06:57Z – claude-opus – shell_pid=9761 – lane=done – Review passed: Deprecated fields removed from MaterialProduct
- 2026-01-18T21:24:53Z – claude-opus – shell_pid=26146 – lane=doing – Started review via workflow command
