# Research: Materials FIFO Foundation

**Feature**: 058-materials-fifo-foundation
**Date**: 2026-01-18
**Purpose**: Document existing patterns to follow for implementation

## Research Summary

All key patterns have been identified from the existing ingredient/food inventory system. The materials implementation should follow these patterns exactly for constitutional compliance.

---

## Pattern 1: InventoryItem Model Structure

**Source**: `src/models/inventory_item.py`

**Decision**: MaterialInventoryItem will mirror InventoryItem structure exactly.

### Key Fields to Replicate

| InventoryItem Field | MaterialInventoryItem Equivalent | Notes |
|---------------------|----------------------------------|-------|
| `product_id` | `material_product_id` | FK to definition |
| `purchase_id` | `material_purchase_id` | FK to purchase record |
| `quantity` | `quantity_remaining` | Mutable, decremented on consume |
| `unit_cost` | `cost_per_unit` | Immutable snapshot from purchase |
| `purchase_date` | `purchase_date` | For FIFO ordering (indexed) |
| `location` | `location` | Optional storage location |
| `notes` | `notes` | Optional user notes |

### Additional Field for Materials

| Field | Purpose |
|-------|---------|
| `quantity_purchased` | Immutable snapshot (ingredients derive from Purchase) |

**Rationale**: Materials need explicit quantity_purchased since MaterialPurchase stores `packages_purchased` and `units_added`, making the relationship less direct than ingredients.

### Indexes Required

```python
Index("idx_material_inventory_product", "material_product_id"),
Index("idx_material_inventory_purchase_date", "purchase_date"),
Index("idx_material_inventory_purchase", "material_purchase_id"),
```

---

## Pattern 2: FIFO Consumption Algorithm

**Source**: `src/services/inventory_item_service.py:consume_fifo()`

**Decision**: Copy algorithm exactly, adapting for material-specific relationships.

### Algorithm Steps

1. **Query Phase**: `ORDER BY purchase_date ASC` (oldest first)
2. **Filter**: `quantity_remaining > 0.001` (avoid floating-point dust)
3. **Iteration**: Loop through lots consuming from each
4. **Unit Conversion**: Convert between lot unit and target unit
5. **Atomic Updates**: Single transaction for all changes
6. **Cost Calculation**: `sum(quantity_consumed * cost_per_unit)`
7. **Return Structure**: `{consumed, breakdown, shortfall, satisfied, total_cost}`

### Session Pattern (Critical)

```python
def consume_material_fifo(..., session=None):
    """
    Session management pattern from CLAUDE.md:
    - If session provided: caller owns transaction, don't commit
    - If session is None: create own transaction via session_scope()
    """
    if session is not None:
        return _do_consume(session)
    else:
        with session_scope() as sess:
            return _do_consume(sess)
```

### Return Value Structure

```python
{
    "consumed": Decimal,          # Amount consumed in target_unit
    "breakdown": [                # Per-lot details for audit
        {
            "inventory_item_id": int,
            "quantity_consumed": Decimal,
            "unit": str,
            "remaining_in_lot": Decimal,
            "unit_cost": Decimal,
        }
    ],
    "shortfall": Decimal,         # Amount not available
    "satisfied": bool,            # True if fully consumed
    "total_cost": Decimal,        # FIFO cost of consumed
}
```

---

## Pattern 3: MaterialProduct Current State

**Source**: `src/models/material_product.py`

**Decision**: Remove `current_inventory` and `weighted_avg_cost` fields.

### Fields to Remove

| Field | Current Type | Reason for Removal |
|-------|-------------|-------------------|
| `current_inventory` | Float | Violates definition/instantiation separation |
| `weighted_avg_cost` | Numeric(10,4) | FIFO replaces weighted average |

### Constraints to Remove

```python
CheckConstraint("current_inventory >= 0", name="ck_material_product_inventory_non_negative"),
CheckConstraint("weighted_avg_cost >= 0", name="ck_material_product_cost_non_negative"),
```

### Property to Remove

```python
@property
def inventory_value(self) -> Decimal:
    """Calculate total value: current_inventory * weighted_avg_cost"""
    # DELETE THIS - will be calculated from MaterialInventoryItem
```

### Code Locations Requiring Updates

1. `src/services/material_purchase_service.py` - Remove `_update_inventory_on_purchase()`
2. `src/services/material_catalog_service.py` - Remove from `list_products()` output
3. `src/ui/materials_tab.py` - Remove inventory columns from display
4. `src/services/denormalized_export_service.py` - Remove `inventory_value`

---

## Pattern 4: Unit Conversion

**Decision**: Create new `material_unit_converter.py` with metric base units.

### Base Unit Types

| Type | Base Unit | Storage |
|------|-----------|---------|
| `linear_cm` | centimeter | Float |
| `square_cm` | square centimeter | Float |
| `each` | count | Integer |

### Conversion Factors (to base units)

**Linear (to cm)**:
| Unit | Factor | Source |
|------|--------|--------|
| feet | 30.48 | NIST |
| inches | 2.54 | NIST |
| yards | 91.44 | NIST |
| meters | 100.0 | SI |
| mm | 0.1 | SI |
| cm | 1.0 | Base |

**Area (to square_cm)**:
| Unit | Factor | Source |
|------|--------|--------|
| square_feet | 929.0304 | Derived (30.48²) |
| square_inches | 6.4516 | Derived (2.54²) |
| square_yards | 8361.2736 | Derived (91.44²) |
| square_meters | 10000.0 | SI |
| square_cm | 1.0 | Base |

### Validation Rule

```python
def validate_unit_compatibility(package_unit: str, base_unit_type: str) -> bool:
    """
    Ensure package_unit can be converted to base_unit_type.
    - "feet" → "linear_cm" ✓
    - "feet" → "square_cm" ✗ (incompatible)
    - "square_feet" → "square_cm" ✓
    """
```

---

## Pattern 5: MaterialConsumption Update

**Source**: `src/models/material_consumption.py`

**Decision**: Add `inventory_item_id` FK for FIFO traceability.

### Field to Add

```python
inventory_item_id = Column(
    Integer,
    ForeignKey("material_inventory_items.id", ondelete="RESTRICT"),
    nullable=True,  # Nullable for migration of existing records
    index=True,
)
```

### Relationship to Add

```python
inventory_item = relationship("MaterialInventoryItem", back_populates="consumptions")
```

---

## Pattern 6: Import/Export Schema Handling

**Source**: `src/services/import_export_service.py`

**Decision**: Filter removed fields on export; ignore on import.

### Export Changes

```python
# In MaterialProduct export
EXCLUDED_FIELDS = {"current_inventory", "weighted_avg_cost"}
product_data = {k: v for k, v in product.to_dict().items() if k not in EXCLUDED_FIELDS}
```

### Import Changes

```python
# In MaterialProduct import - gracefully ignore deprecated fields
IGNORED_IMPORT_FIELDS = {"current_inventory", "weighted_avg_cost"}
clean_data = {k: v for k, v in import_data.items() if k not in IGNORED_IMPORT_FIELDS}
```

---

## Alternatives Considered

### Alternative 1: Migrate Existing MaterialPurchase to Inventory Items

**Rejected because**:
- Requires complex data transformation
- Historical weighted_avg_cost cannot be accurately split into FIFO lots
- User has accepted fresh start for material inventory
- Simpler to document clean migration path

### Alternative 2: Keep weighted_avg_cost alongside FIFO

**Rejected because**:
- Violates constitutional Principle III (definition/instantiation separation)
- Creates confusion about which cost is "correct"
- Requires maintaining two cost calculation paths

### Alternative 3: Use ingredient unit_converter.py for materials

**Rejected because**:
- Ingredient units (cups, oz, grams) differ from material units (feet, inches, cm)
- Material base units are metric (cm) not ingredient base units
- Cleaner to have separate material_unit_converter.py with appropriate units

---

## Research Complete

All patterns documented. Ready to proceed with data-model.md generation.
