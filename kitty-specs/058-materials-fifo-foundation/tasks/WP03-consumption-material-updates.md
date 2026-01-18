---
work_package_id: "WP03"
subtasks:
  - "T009"
  - "T010"
  - "T011"
title: "Schema Changes - MaterialConsumption & Material Updates"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: "claude-opus"
agent: "claude-opus"
shell_pid: "27637"
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
    action: "Review passed: FIFO traceability added to MaterialConsumption"
---

# Work Package Prompt: WP03 – Schema Changes - MaterialConsumption & Material Updates

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

## Objectives & Success Criteria

Add FIFO traceability to MaterialConsumption and update Material base_unit_type to metric values.

**Success Criteria**:
- MaterialConsumption has inventory_item_id FK (nullable for backward compatibility)
- MaterialConsumption has inventory_item relationship
- Material.base_unit_type accepts metric values: 'linear_cm', 'square_cm', 'each'
- CHECK constraint updated

## Context & Constraints

**Reference Documents**:
- `kitty-specs/058-materials-fifo-foundation/data-model.md` - Field additions
- `kitty-specs/058-materials-fifo-foundation/research.md` - Pattern 5

**Key Constraints**:
- inventory_item_id is NULLABLE for backward compatibility with existing consumption records
- Existing data using 'linear_inches' or 'square_inches' will need migration during reset/re-import
- Schema change strategy is reset/re-import per constitution

## Subtasks & Detailed Guidance

### Subtask T009 – Add inventory_item_id FK to MaterialConsumption

**Purpose**: Enable FIFO traceability - link each consumption to its source inventory lot.

**Steps**:
1. Open `src/models/material_consumption.py`
2. Add the new foreign key column after product_id:
```python
inventory_item_id = Column(
    Integer,
    ForeignKey("material_inventory_items.id", ondelete="RESTRICT"),
    nullable=True,  # Nullable for backward compatibility with existing records
    index=True,
)
```
3. Add index to __table_args__:
```python
Index("idx_material_consumption_inventory_item", "inventory_item_id"),
```

**Files**:
- Edit: `src/models/material_consumption.py`

**Parallel?**: Yes (different file from T011)

**Notes**:
- ondelete="RESTRICT" prevents deleting inventory items that have consumption records
- nullable=True allows existing records to remain valid

### Subtask T010 – Add inventory_item relationship to MaterialConsumption

**Purpose**: Enable navigation from consumption to its source inventory lot.

**Steps**:
1. In `src/models/material_consumption.py`, add the relationship:
```python
inventory_item = relationship(
    "MaterialInventoryItem",
    back_populates="consumptions",
)
```
2. Update to_dict() to optionally include inventory_item information:
```python
if include_relationships:
    # ... existing code ...
    if self.inventory_item:
        result["inventory_item"] = {
            "id": self.inventory_item.id,
            "purchase_date": self.inventory_item.purchase_date.isoformat() if self.inventory_item.purchase_date else None,
        }
```

**Files**:
- Edit: `src/models/material_consumption.py`

**Parallel?**: No (depends on T009 being in same file)

### Subtask T011 – Update Material.base_unit_type to metric values

**Purpose**: Change from imperial (inches) to metric (cm) base units for consistency.

**Steps**:
1. Open `src/models/material.py`
2. Find the base_unit_type CheckConstraint in __table_args__:
```python
CheckConstraint(
    "base_unit_type IN ('each', 'linear_inches', 'square_inches')",
    name="ck_material_base_unit_type",
),
```
3. Change to metric values:
```python
CheckConstraint(
    "base_unit_type IN ('each', 'linear_cm', 'square_cm')",
    name="ck_material_base_unit_type",
),
```
4. Update the field docstring/comment to reflect metric:
```python
base_unit_type = Column(String(20), nullable=False)  # 'each', 'linear_cm', 'square_cm'
```

**Files**:
- Edit: `src/models/material.py`

**Parallel?**: Yes (different file from T009-T010)

**Notes**:
- Existing data migration: linear_inches→linear_cm, square_inches→square_cm
- This is handled during reset/re-import, not automatic migration
- Document migration mapping in spec:
  ```python
  UNIT_TYPE_MIGRATION = {
      "linear_inches": "linear_cm",
      "square_inches": "square_cm",
      "each": "each",  # No change
  }
  ```

## Test Strategy

```python
def test_material_consumption_has_inventory_item_id():
    """Verify MaterialConsumption has inventory_item_id FK."""
    from src.models import MaterialConsumption
    from sqlalchemy import inspect

    mapper = inspect(MaterialConsumption)
    columns = [c.name for c in mapper.columns]
    assert "inventory_item_id" in columns

def test_material_base_unit_type_metric():
    """Verify Material accepts metric base_unit_type values."""
    from src.models import Material

    # Should accept metric values
    material = Material(
        subcategory_id=1,
        name="Test Material",
        slug="test-material",
        base_unit_type="linear_cm",
    )
    assert material.base_unit_type == "linear_cm"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing consumption records | inventory_item_id nullable preserves backward compatibility |
| Existing material data | Migration handled via reset/re-import |
| CHECK constraint failure | Update constraint BEFORE importing new data |

## Definition of Done Checklist

- [ ] MaterialConsumption has inventory_item_id column (nullable, indexed)
- [ ] MaterialConsumption has inventory_item relationship
- [ ] to_dict() updated to include inventory_item when present
- [ ] Material.base_unit_type CHECK constraint uses metric values
- [ ] Model docstring updated to reflect metric units
- [ ] No import errors

## Review Guidance

**Key acceptance checkpoints**:
1. Verify inventory_item_id is nullable=True
2. Verify ondelete="RESTRICT" (don't cascade delete inventory items)
3. Verify CHECK constraint uses exact values: 'each', 'linear_cm', 'square_cm'
4. Verify back_populates matches on both sides of relationship

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
- 2026-01-18T19:09:03Z – unknown – lane=for_review – T009-T011 complete: Added FIFO traceability
- 2026-01-18T20:07:04Z – claude-opus – lane=done – Review passed: MaterialConsumption traceability added with inventory_item_id FK
- 2026-01-18T21:32:03Z – claude-opus – shell_pid=27637 – lane=doing – Started review via workflow command
