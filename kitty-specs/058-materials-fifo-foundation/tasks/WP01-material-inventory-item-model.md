---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Schema Changes - MaterialInventoryItem Model"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: "claude-opus"
agent: "claude-opus"
shell_pid: "25073"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
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
    action: "Review passed: MaterialInventoryItem model complete"
---

# Work Package Prompt: WP01 – Schema Changes - MaterialInventoryItem Model

## Objectives & Success Criteria

Create the MaterialInventoryItem model that parallels InventoryItem for FIFO inventory tracking of materials.

**Success Criteria**:
- MaterialInventoryItem model exists with all required fields
- Model can be imported from `src.models`
- Relationships properly configured with MaterialProduct and MaterialPurchase
- Basic model instantiation works without errors

## Context & Constraints

**Reference Documents**:
- `.kittify/memory/constitution.md` - Definition/instantiation separation principle
- `kitty-specs/058-materials-fifo-foundation/plan.md` - Technical architecture
- `kitty-specs/058-materials-fifo-foundation/data-model.md` - Schema definition
- `kitty-specs/058-materials-fifo-foundation/research.md` - Pattern to follow

**Pattern Reference**: `src/models/inventory_item.py` - Copy this structure exactly for constitutional compliance.

**Key Constraints**:
- All quantities stored in metric base units (cm for linear/area)
- quantity_purchased and cost_per_unit are IMMUTABLE after creation
- quantity_remaining is MUTABLE (decremented on consumption)
- 1:1 relationship with MaterialPurchase

## Subtasks & Detailed Guidance

### Subtask T001 – Create MaterialInventoryItem model

**Purpose**: Define the core model for FIFO material inventory tracking.

**Steps**:
1. Create new file `src/models/material_inventory_item.py`
2. Import required SQLAlchemy components and BaseModel
3. Define MaterialInventoryItem class with:

```python
class MaterialInventoryItem(BaseModel):
    """
    Tracks a specific lot of material inventory from a purchase.
    Parallels InventoryItem (for food) exactly.
    """
    __tablename__ = "material_inventory_items"

    # Foreign Keys
    material_product_id = Column(
        Integer,
        ForeignKey("material_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_purchase_id = Column(
        Integer,
        ForeignKey("material_purchases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quantity Tracking (in base units - cm for linear/area, count for each)
    quantity_purchased = Column(Float, nullable=False)   # Immutable snapshot
    quantity_remaining = Column(Float, nullable=False)   # Mutable

    # Cost Tracking
    cost_per_unit = Column(Numeric(10, 4), nullable=False)  # Immutable snapshot

    # Date Tracking
    purchase_date = Column(Date, nullable=False, index=True)  # For FIFO ordering

    # Optional Fields
    location = Column(String(100), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    # Relationships (define after model)
    # product, purchase, consumptions

    # Table constraints
    __table_args__ = (
        CheckConstraint("quantity_purchased > 0", name="ck_mat_inv_qty_purchased_positive"),
        CheckConstraint("quantity_remaining >= 0", name="ck_mat_inv_qty_remaining_non_negative"),
        CheckConstraint("cost_per_unit >= 0", name="ck_mat_inv_cost_non_negative"),
        Index("idx_material_inventory_product", "material_product_id"),
        Index("idx_material_inventory_purchase_date", "purchase_date"),
        Index("idx_material_inventory_purchase", "material_purchase_id"),
        Index("idx_material_inventory_location", "location"),
    )
```

4. Add relationships:
```python
product = relationship("MaterialProduct", back_populates="inventory_items")
purchase = relationship("MaterialPurchase", back_populates="inventory_item")
consumptions = relationship("MaterialConsumption", back_populates="inventory_item")
```

5. Add `__repr__` and `to_dict` methods following InventoryItem pattern

**Files**:
- Create: `src/models/material_inventory_item.py`

**Parallel?**: Yes (independent new file)

**Notes**:
- Use `from .base import BaseModel` for the import
- Follow existing model patterns exactly (see material_product.py, inventory_item.py)

### Subtask T002 – Add model to __init__.py exports

**Purpose**: Make MaterialInventoryItem importable from src.models package.

**Steps**:
1. Open `src/models/__init__.py`
2. Add import: `from .material_inventory_item import MaterialInventoryItem`
3. Add `MaterialInventoryItem` to the `__all__` list

**Files**:
- Edit: `src/models/__init__.py`

**Parallel?**: No (depends on T001)

### Subtask T003 – Add inventory_items relationship to MaterialProduct

**Purpose**: Enable MaterialProduct to access its inventory items for FIFO queries.

**Steps**:
1. Open `src/models/material_product.py`
2. Add relationship:
```python
inventory_items = relationship(
    "MaterialInventoryItem",
    back_populates="product",
    cascade="all, delete-orphan",
    lazy="select",
)
```

**Files**:
- Edit: `src/models/material_product.py`

**Parallel?**: No (depends on T001)

### Subtask T004 – Add inventory_item relationship to MaterialPurchase

**Purpose**: Enable 1:1 navigation from purchase to its inventory item.

**Steps**:
1. Open `src/models/material_purchase.py`
2. Add relationship (1:1 with uselist=False):
```python
# One purchase creates exactly one inventory item
inventory_item = relationship(
    "MaterialInventoryItem",
    back_populates="purchase",
    uselist=False,  # 1:1 relationship
)
```

**Files**:
- Edit: `src/models/material_purchase.py`

**Parallel?**: No (depends on T001)

## Test Strategy

Basic validation tests to ensure model is properly defined:

```python
def test_material_inventory_item_can_be_created():
    """Test that MaterialInventoryItem can be instantiated."""
    from src.models import MaterialInventoryItem
    # Basic instantiation test
    item = MaterialInventoryItem(
        material_product_id=1,
        material_purchase_id=1,
        quantity_purchased=100.0,
        quantity_remaining=100.0,
        cost_per_unit=Decimal("0.15"),
        purchase_date=date.today(),
    )
    assert item.quantity_purchased == 100.0
    assert item.quantity_remaining == 100.0
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Use string-based relationship references ("MaterialProduct") |
| Relationship naming conflicts | Follow exact naming pattern from research.md |
| Missing imports | Verify all SQLAlchemy types imported |

## Definition of Done Checklist

- [ ] MaterialInventoryItem model exists in `src/models/material_inventory_item.py`
- [ ] Model has all fields per data-model.md
- [ ] Model exported from `src/models/__init__.py`
- [ ] MaterialProduct has `inventory_items` relationship
- [ ] MaterialPurchase has `inventory_item` relationship (1:1)
- [ ] Basic instantiation test passes
- [ ] No import errors when running `from src.models import MaterialInventoryItem`

## Review Guidance

**Key acceptance checkpoints**:
1. Verify field types match data-model.md exactly
2. Verify CheckConstraints are properly named
3. Verify indexes exist for FIFO query performance
4. Verify relationship back_populates match on both sides
5. Verify uselist=False on MaterialPurchase relationship (1:1)

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
- 2026-01-18T18:32:26Z – claude-opus – shell_pid=87459 – lane=doing – Started implementation via workflow command
- 2026-01-18T18:36:31Z – claude-opus – shell_pid=87459 – lane=for_review – Ready for review: MaterialInventoryItem model with all relationships. All 4 subtasks (T001-T004) complete.
- 2026-01-18T20:06:28Z – claude-opus – shell_pid=9695 – lane=doing – Started review via workflow command
- 2026-01-18T20:06:52Z – claude-opus – shell_pid=9695 – lane=done – Review passed: MaterialInventoryItem model complete with all required fields, relationships, and helper methods
- 2026-01-18T21:19:43Z – claude-opus – shell_pid=25073 – lane=doing – Started review via workflow command
